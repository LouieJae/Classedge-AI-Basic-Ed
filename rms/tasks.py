from celery import shared_task, chain
import requests
from requests.exceptions import ConnectionError, Timeout, RequestException
from django.conf import settings
from django.core.exceptions import ValidationError
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# Default RMS page size for paginated endpoints. Matches the migration app's
# fetch_page limit so memory stays bounded to ~500 records at a time instead
# of buffering the entire dataset before any DB work begins.
RMS_PAGE_SIZE = 500


def _iter_rms_pages(url, headers, *, task=None, label="records", page_size=RMS_PAGE_SIZE):
    """Yield each page of an RMS paginated endpoint as it arrives.

    Streams instead of accumulating: callers process every yielded page
    immediately, so the entire payload never sits in memory at once.

    Yields tuples of (page_items, total_so_far, page_number).
    """
    if 'page_size=' not in url:
        sep = '&' if '?' in url else '?'
        url = f"{url}{sep}page_size={page_size}"

    total = 0
    page_no = 0
    while url:
        response = requests.get(url, headers=headers, timeout=300)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch data. Status: {response.status_code}")

        data = response.json()
        if isinstance(data, dict) and 'results' in data:
            page_items = data['results']
            next_url = data.get('next')
        elif isinstance(data, list):
            page_items = data
            next_url = None
        else:
            raise Exception("Unexpected data structure")

        page_no += 1
        total += len(page_items)
        if task is not None:
            task.update_state(
                state='PROGRESS',
                meta={
                    'current': total,
                    'status': f'Fetched page {page_no} ({total} {label}). Processing…',
                },
            )

        yield page_items, total, page_no
        url = next_url


@shared_task(bind=True, max_retries=3)
def sync_academic_terms_task(self, user_id, dry_run=False):
    """
    Sync academic terms from RMS asynchronously.

    Args:
        user_id: ID of the user who initiated the sync
        dry_run: If True, fetch + count pages but skip DB writes.
    """
    try:
        from rms.utils import sync_semesters

        based_url = settings.RMS_URL
        token = settings.RMS_TOKEN
        url = based_url + "academic-terms/?current_semester=true&pagination=true"
        headers = {"Authorization": f"Bearer {token}"}

        total_synced = 0
        page_count = 0
        for page, _total, page_count in _iter_rms_pages(url, headers, task=self, label='academic terms'):
            current_only = [item for item in page if item.get("current_semester") is True]
            if current_only and not dry_run:
                sync_semesters(current_only)
            total_synced += len(current_only)

        return {
            "status": "success",
            "dry_run": dry_run,
            "pages": page_count,
            "total_synced": total_synced,
        }
    
    except (ConnectionError, Timeout, RequestException) as exc:
        logger.warning(f"Network error in sync_academic_terms_task: {str(exc)}. Retrying...")
        raise self.retry(exc=exc, countdown=300 * (2 ** self.request.retries))
    except ValidationError as e:
        logger.error(f"Validation error in sync_academic_terms_task: {str(e)}")
        return {"status": "failed", "error": f"Validation error: {str(e)}"}
    except Exception as exc:
        logger.error(f"Unexpected error in sync_academic_terms_task: {str(exc)}", exc_info=True)
        return {"status": "failed", "error": f"Unexpected error: {str(exc)}"}


@shared_task(bind=True, max_retries=3)
def sync_class_schedules_task(self, user_id, school_year=None, dry_run=False):
    """
    Sync class schedules from RMS asynchronously.

    Args:
        user_id: ID of the user who initiated the sync
        school_year: Optional school year filter
        dry_run: If True, fetch + count pages but skip DB writes.
    """
    try:
        from rms.utils import sync_subject_and_schedule

        based_url = settings.RMS_URL
        token = settings.RMS_TOKEN

        if school_year:
            url = based_url + f"class-schedules/?academic_term__school_year={school_year}&pagination=true"
        else:
            url = based_url + "class-schedules/?pagination=true"

        headers = {"Authorization": f"Bearer {token}"}

        total_fetched = 0
        updated_count = 0
        failed_items = []
        idx = 0
        page_count = 0

        for page, total_fetched, page_count in _iter_rms_pages(url, headers, task=self, label='class schedules'):
            for item in page:
                idx += 1
                if dry_run:
                    continue
                try:
                    sync_subject_and_schedule(item)
                    updated_count += 1
                except ValidationError as e:
                    subject_name = (item.get('subject') or {}).get('subject_name', 'Unknown')
                    logger.warning(f"Validation error for subject {subject_name}: {str(e)}")
                    failed_items.append({"subject": subject_name, "error": str(e)})
                except Exception as e:
                    subject_name = (item.get('subject') or {}).get('subject_name', 'Unknown')
                    logger.error(f"Error processing subject {subject_name}: {str(e)}", exc_info=True)
                    failed_items.append({"subject": subject_name, "error": f"Unexpected error: {str(e)}"})

                if idx % 50 == 0:
                    self.update_state(
                        state='PROGRESS',
                        meta={'current': idx, 'total': total_fetched, 'status': f'Processed {idx} schedules'},
                    )

        return {
            "status": "success",
            "dry_run": dry_run,
            "pages": page_count,
            "total_fetched": total_fetched,
            "updated": updated_count,
            "failed": len(failed_items),
            "failed_items": failed_items[:10],
        }
    
    except (ConnectionError, Timeout, RequestException) as exc:
        logger.warning(f"Network error in sync_class_schedules_task: {str(exc)}. Retrying...")
        raise self.retry(exc=exc, countdown=300 * (2 ** self.request.retries))
    except Exception as exc:
        logger.error(f"Unexpected error in sync_class_schedules_task: {str(exc)}", exc_info=True)
        return {"status": "failed", "error": f"Unexpected error: {str(exc)}"}


@shared_task(bind=True, max_retries=3)
def sync_student_enrollments_task(self, user_id, school_year=None, dry_run=False):
    """
    Sync student enrollments from RMS asynchronously.

    Args:
        user_id: ID of the user who initiated the sync
        school_year: Optional school year filter
        dry_run: If True, fetch + count pages but skip DB writes.
    """
    try:
        from rms.utils.sync_enrollments import (
            sync_enrollments_bulk,
            create_placeholder_enrollments_for_empty_subjects,
        )

        based_url = settings.RMS_URL
        token = settings.RMS_TOKEN

        if school_year:
            url = based_url + f"student-schedules/?student_subject__subject_template__academic_term__school_year={school_year}&pagination=true"
        else:
            url = based_url + "student-schedules/?pagination=true"

        headers = {"Authorization": f"Bearer {token}"}

        # ── Stream + bulk-process each page ───────────────────────────────────
        total_fetched = 0
        created = skipped = failed = 0
        failed_items = []
        page_count = 0

        for page, total_fetched, page_count in _iter_rms_pages(url, headers, task=self, label='enrollments'):
            if dry_run:
                continue
            self.update_state(
                state='PROGRESS',
                meta={'status': f'Bulk-processing page {page_count} ({len(page)} rows, {total_fetched} total)...'},
            )
            result = sync_enrollments_bulk(page)
            created += result['created']
            skipped += result['skipped']
            failed += result['failed']
            if result.get('failed_items'):
                failed_items.extend(result['failed_items'])

        # ── Placeholder enrollments for subjects with no students ─────────────
        placeholders_created = 0
        if not dry_run:
            try:
                placeholders_created = create_placeholder_enrollments_for_empty_subjects()
            except Exception as e:
                logger.error(f"Error creating placeholder enrollments: {str(e)}", exc_info=True)

        logger.info(
            f"sync_student_enrollments_task done (dry_run={dry_run}): "
            f"created={created}, skipped={skipped}, "
            f"failed={failed}, placeholders={placeholders_created}"
        )

        return {
            "status": "success",
            "dry_run": dry_run,
            "pages": page_count,
            "total_fetched": total_fetched,
            "created": created,
            "skipped": skipped,
            "failed": failed,
            "placeholders_created": placeholders_created,
            "failed_items": failed_items[:10],
        }
    
    except (ConnectionError, Timeout, RequestException) as exc:
        logger.warning(f"Network error in sync_student_enrollments_task: {str(exc)}. Retrying...")
        raise self.retry(exc=exc, countdown=300 * (2 ** self.request.retries))
    except Exception as exc:
        logger.error(f"Unexpected error in sync_student_enrollments_task: {str(exc)}", exc_info=True)
        return {"status": "failed", "error": f"Unexpected error: {str(exc)}"}


@shared_task(bind=True, max_retries=3)
def sync_terms_task(self, user_id, dry_run=False):
    """
    Sync terms from RMS asynchronously.

    Args:
        user_id: ID of the user who initiated the sync
        dry_run: If True, fetch + count pages but skip DB writes.
    """
    try:
        from rms.utils import sync_terms

        based_url = settings.RMS_URL
        token = settings.RMS_TOKEN
        url = based_url + "terms/?current_semester=true&pagination=true"
        headers = {"Authorization": f"Bearer {token}"}

        total_synced = 0
        page_count = 0
        for page, total_synced, page_count in _iter_rms_pages(url, headers, task=self, label='terms'):
            if page and not dry_run:
                sync_terms(page)

        return {
            "status": "success",
            "dry_run": dry_run,
            "pages": page_count,
            "total_synced": total_synced,
        }
    
    except (ConnectionError, Timeout, RequestException) as exc:
        logger.warning(f"Network error in sync_terms_task: {str(exc)}. Retrying...")
        raise self.retry(exc=exc, countdown=300 * (2 ** self.request.retries))
    except ValidationError as e:
        logger.error(f"Validation error in sync_terms_task: {str(e)}")
        return {"status": "failed", "error": f"Validation error: {str(e)}"}
    except Exception as exc:
        logger.error(f"Unexpected error in sync_terms_task: {str(exc)}", exc_info=True)
        return {"status": "failed", "error": f"Unexpected error: {str(exc)}"}


@shared_task(bind=True, max_retries=3)
def sync_student_data_task(self, user_id, school_year=None, dry_run=False):
    """
    Sync student data from RMS asynchronously.

    Args:
        user_id: ID of the user who initiated the sync
        school_year: Optional school year filter
        dry_run: If True, fetch + count pages but skip DB writes.
    """
    try:
        from rms.utils import sync_user_data

        based_url = settings.RMS_URL
        token = settings.RMS_TOKEN

        if school_year:
            url = based_url + f"students/?school_year={school_year}&pagination=true"
        else:
            url = based_url + "students/?pagination=true"

        headers = {"Authorization": f"Bearer {token}"}

        total_fetched = 0
        updated_count = 0
        failed_items = []
        idx = 0
        page_count = 0

        for page, total_fetched, page_count in _iter_rms_pages(url, headers, task=self, label='students'):
            for item in page:
                idx += 1
                if dry_run:
                    continue
                try:
                    sync_user_data(item)
                    updated_count += 1
                except ValidationError as e:
                    student_email = item.get('school_email') or item.get('email', 'Unknown')
                    logger.warning(f"Validation error for student {student_email}: {str(e)}")
                    failed_items.append({"email": student_email, "error": str(e)})
                except Exception as e:
                    student_email = item.get('school_email') or item.get('email', 'Unknown')
                    logger.error(f"Error syncing student {student_email}: {str(e)}", exc_info=True)
                    failed_items.append({"email": student_email, "error": f"Unexpected error: {str(e)}"})

                if idx % 50 == 0:
                    self.update_state(
                        state='PROGRESS',
                        meta={'current': idx, 'total': total_fetched, 'status': f'Processed {idx} students'},
                    )

        return {
            "status": "success",
            "dry_run": dry_run,
            "pages": page_count,
            "total_fetched": total_fetched,
            "updated": updated_count,
            "failed": len(failed_items),
            "failed_items": failed_items[:10],
        }
    
    except (ConnectionError, Timeout, RequestException) as exc:
        logger.warning(f"Network error in sync_student_data_task: {str(exc)}. Retrying...")
        raise self.retry(exc=exc, countdown=300 * (2 ** self.request.retries))
    except Exception as exc:
        logger.error(f"Unexpected error in sync_student_data_task: {str(exc)}", exc_info=True)
        return {"status": "failed", "error": f"Unexpected error: {str(exc)}"}


@shared_task(bind=True, max_retries=3)
def sync_courses_task(self, user_id, dry_run=False):
    """Sync departments + programs (courses) from RMS.

    Pulls `<RMS_URL>/courses/`, walks all pagination pages, then delegates
    to ``sync_courses`` which upserts Department + Course rows. Returns
    the same {total_fetched, created, updated, failed, failed_items}
    shape the UI already renders.

    Args:
        user_id: ID of the user who initiated the sync
        dry_run: If True, fetch + count pages but skip DB writes.
    """
    try:
        from rms.utils import sync_courses

        based_url = settings.RMS_URL
        token = settings.RMS_TOKEN
        url = based_url + "courses/"
        headers = {"Authorization": f"Bearer {token}"}

        # Aggregate counts across pages — sync_courses returns the same shape
        # for each page, so we sum the numeric fields and concatenate the
        # failed_items list.
        agg = {
            "total_fetched": 0,
            "departments_created": 0,
            "departments_updated": 0,
            "courses_created": 0,
            "courses_updated": 0,
            "failed": 0,
            "failed_items": [],
        }
        page_count = 0

        for page, _total, page_count in _iter_rms_pages(url, headers, task=self, label='courses'):
            active_items = [
                item for item in page
                if (item.get("status") or "").lower() != "inactive"
            ]
            if not active_items:
                continue
            if dry_run:
                agg["total_fetched"] += len(active_items)
                continue
            result = sync_courses(active_items)
            for key in ("total_fetched", "departments_created", "departments_updated",
                        "courses_created", "courses_updated", "failed"):
                agg[key] += result.get(key, 0)
            if result.get("failed_items"):
                agg["failed_items"].extend(result["failed_items"])

        agg["failed_items"] = agg["failed_items"][:10]
        return {"status": "success", "dry_run": dry_run, "pages": page_count, **agg}

    except (ConnectionError, Timeout, RequestException) as exc:
        logger.warning(f"Network error in sync_courses_task: {str(exc)}. Retrying...")
        raise self.retry(exc=exc, countdown=300 * (2 ** self.request.retries))
    except Exception as exc:
        logger.error(f"Unexpected error in sync_courses_task: {str(exc)}", exc_info=True)
        return {"status": "failed", "error": f"Unexpected error: {str(exc)}"}


@shared_task(bind=True, max_retries=1)
def sync_all_rms_data(self):
    """
    Master task to sync all RMS data in sequence.
    Runs daily via Celery Beat.
    
    This task orchestrates all RMS sync operations:
    1. Academic Terms
    2. Terms
    3. Class Schedules
    4. Student Data
    5. Student Enrollments
    """
    
    results = {
        'academic_terms': None,
        'terms': None,
        'class_schedules': None,
        'student_data': None,
        'student_enrollments': None,
        'errors': []
    }
    
    try:
        # Get current school year once
        from rms.views import fetch_current_school_year
        school_year = fetch_current_school_year()
        
        # Use Celery chain for sequential execution
        # Each task runs after the previous one completes
        workflow = chain(
            sync_academic_terms_task.si(0),
            sync_terms_task.si(0),
            sync_class_schedules_task.si(0, school_year),
            sync_student_data_task.si(0, school_year),
            sync_student_enrollments_task.si(0, school_year)
        )
        
        # Execute the chain and wait for completion
        result = workflow.apply_async()
        final_result = result.get()
        
        # Collect results from chain
        results['academic_terms'] = {"status": "completed"}
        results['terms'] = {"status": "completed"}
        results['class_schedules'] = {"status": "completed"}
        results['student_data'] = {"status": "completed"}
        results['student_enrollments'] = final_result
        
        
        return {
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "total_errors": len(results['errors'])
        }
    
    except (ConnectionError, Timeout, RequestException) as exc:
        logger.warning(f"Network error in sync_all_rms_data: {str(exc)}. Retrying...")
        if self.request.retries < 1:
            raise self.retry(exc=exc, countdown=300)
        else:
            return {
                "status": "failed",
                "error": f"Network error after retries: {str(exc)}",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as exc:
        logger.error(f"Unexpected error in sync_all_rms_data: {str(exc)}", exc_info=True)
        return {
            "status": "failed",
            "error": str(exc),
            "timestamp": datetime.now().isoformat()
        }