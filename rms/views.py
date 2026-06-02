import logging
from datetime import datetime
import requests
from requests.exceptions import ConnectionError, Timeout, RequestException
from django.http import JsonResponse

logger = logging.getLogger(__name__)
from django.conf import settings
from rms.utils import sync_semesters, sync_subject_and_schedule, sync_terms, sync_enrollment, sync_user_data
from rms.utils.sync_enrollments import create_placeholder_enrollments_for_empty_subjects
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from course.models import Semester
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, permission_required
from decimal import Decimal
from rest_framework import status

def _is_empty_payload(data):
    """Return True if upstream JSON is empty (None, [], {}, or paginated with no results)."""
    if data is None:
        return True
    if isinstance(data, (list, tuple, str)) and len(data) == 0:
        return True
    if isinstance(data, dict):
        if not data:
            return True
        if 'results' in data and not data.get('results'):
            return True
    return False



based_url = settings.RMS_URL
token = settings.RMS_TOKEN

def fetch_current_school_year():
    url = based_url + "academic-terms/?current_semester=true"
    
    headers = {
        "Authorization": f"Bearer {token}",
    }
    terms = []
    while url:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return None
            
        data = response.json()
        
        if isinstance(data, dict) and 'results' in data:
            terms.extend(data['results'])
            url = data.get('next')
        elif isinstance(data, list):
            terms.extend(data)
            url = None
        else:
            return None

    current_terms = [item for item in terms if item.get("current_semester") is True]
    
    if not current_terms:
        return None
        
    for term in current_terms:
        start = term.get("start_date")
        end = term.get("end_date")
        school_year = term.get("school_year")
        
        if not start or not end or not school_year:
            continue
            
        try:
            start_date = datetime.strptime(start, "%Y-%m-%d").date()
            end_date = datetime.strptime(end, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
            
        semester_exists = Semester.objects.filter(start_date=start_date, end_date=end_date).exists()
        
        if semester_exists:
            return school_year
    
    fallback = current_terms[0].get("school_year")
    return fallback


def fetch_current_semester():
    url = based_url + "academic-terms/?current_semester=true"
    headers = {
        "Authorization": f"Bearer {token}",
    }
    terms = []
    while url:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return None
            
        data = response.json()
        
        if isinstance(data, dict) and 'results' in data:
            terms.extend(data['results'])
            url = data.get('next')
        elif isinstance(data, list):
            terms.extend(data)
            url = None
        else:
            return None

    current_terms = [item for item in terms if item.get("current_semester") is True]
    
    if not current_terms:
        return None
        
    for term in current_terms:
        start = term.get("start_date")
        end = term.get("end_date")
        year_level = term.get("year_level")
        semester = term.get("semester")
        
        if not start or not end or not year_level or not semester:
            continue
            
        try:
            start_date = datetime.strptime(start, "%Y-%m-%d").date()
            end_date = datetime.strptime(end, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
            
        semester_exists = Semester.objects.filter(start_date=start_date, end_date=end_date).exists()
        
        if semester_exists:
            return semester
    
    fallback = current_terms[0].get("semester")
    return fallback



@login_required
def academic_terms(request):
    """Queue academic terms sync as Celery task"""
    from rms.tasks import sync_academic_terms_task
    
    task = sync_academic_terms_task.delay(request.user.id)
    
    return JsonResponse({
        'status': 'queued',
        'message': 'Academic terms sync started in background',
        'task_id': task.id
    })


@login_required
def academic_terms_sync(request):
    """Original synchronous version (kept for reference/fallback)"""
    url = based_url + "academic-terms/?current_semester=true"
    headers = {
        "Authorization": f"Bearer {token}",
    }

    all_items = []
    try:
        while url:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return JsonResponse({'error': 'Failed to fetch data'}, status=500)

            data = response.json()

            if isinstance(data, dict) and 'results' in data:
                all_items.extend(data['results'])
                url = data.get('next') 
            elif isinstance(data, list):
                all_items.extend(data)
                url = None 
            else:
                return JsonResponse({'error': 'Unexpected data structure'}, status=500)

        filtered_data = [item for item in all_items if item.get("current_semester") == True]
        
        sync_semesters(filtered_data)

        return JsonResponse(filtered_data, safe=False)
    
    except ConnectionError:
        return JsonResponse({
            'error': 'Unable to connect to RMS server. Please check if the server is running.',
            'details': f'Connection refused to {based_url}'
        }, status=503)
    except Timeout:
        return JsonResponse({
            'error': 'Request to RMS server timed out. Please try again later.',
        }, status=504)
    except RequestException as e:
        return JsonResponse({
            'error': 'Failed to communicate with RMS server.',
            'details': str(e)
        }, status=503)



@login_required
def class_schedule(request):
    """Queue class schedule sync as Celery task"""
    from rms.tasks import sync_class_schedules_task
    
    school_year = fetch_current_school_year()
    task = sync_class_schedules_task.delay(request.user.id, school_year)
    
    return JsonResponse({
        'status': 'queued',
        'message': f'Class schedule sync started in background{" for " + school_year if school_year else ""}',
        'task_id': task.id,
        'school_year': school_year
    })


@login_required
def class_schedule_sync(request):
    """Original synchronous version (kept for reference/fallback)"""
    school_year = fetch_current_school_year()
    if school_year:
        url = based_url + f"class-schedules/?academic_term__school_year={school_year}&pagination=true"
    else:
        url = based_url + "class-schedules/"
    headers = {
        "Authorization": f"Bearer {token}",
    }

    all_items = []
    try:
        while url:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return JsonResponse({'error': 'Failed to fetch data'}, status=response.status_code)

            data = response.json()

            if isinstance(data, dict) and 'results' in data:
                all_items.extend(data['results'])
                url = data.get('next')
            elif isinstance(data, list):
                all_items.extend(data)
                url = None
            else:
                return JsonResponse({'error': 'Unexpected data structure'}, status=500)


        # --- Integrate creation logic ---
        created_count = 0
        updated_count = 0
        failed_items = []

        for idx, item in enumerate(all_items, 1):
            try:
                subject_name = item.get('subject', {}).get('subject_name', 'Unknown')
                # sync_subject_and_schedule already has @transaction.atomic
                schedule_obj = sync_subject_and_schedule(item)
                # Assume created if no exception - actual tracking would need function modification
                updated_count += 1
            except ValidationError as e:
                failed_items.append({
                    "data": item,
                    "error": str(e)
                })
            except Exception as e:
                failed_items.append({
                    "data": item,
                    "error": f"Unexpected error: {str(e)}"
                })

        result = {
            "total_fetched": len(all_items),
            "created": created_count,
            "updated": updated_count,
            "failed": len(failed_items),
            "failed_items": failed_items[:5], 
        }

        return JsonResponse(result, safe=False)
    
    except ConnectionError:
        return JsonResponse({
            'error': 'Unable to connect to RMS server. Please check if the server is running.',
            'details': f'Connection refused to {based_url}'
        }, status=503)
    except Timeout:
        return JsonResponse({
            'error': 'Request to RMS server timed out. Please try again later.',
        }, status=504)
    except RequestException as e:
        return JsonResponse({
            'error': 'Failed to communicate with RMS server.',
            'details': str(e)
        }, status=503)

@login_required
def student_enrollment(request):
    """Queue student enrollment sync as Celery task"""
    from .tasks import sync_student_enrollments_task
    
    school_year = fetch_current_school_year()
    task = sync_student_enrollments_task.delay(request.user.id, school_year)
    
    return JsonResponse({
        'status': 'queued',
        'message': f'Student enrollment sync started in background{" for " + school_year if school_year else ""}',
        'task_id': task.id,
        'school_year': school_year
    })


@login_required
def student_enrollment_sync(request):
    """Original synchronous version (kept for reference/fallback)"""
    school_year = fetch_current_school_year()
    
    # If no school year found, fetch all enrollments
    if school_year:
        url = based_url + f"student-schedules/?student_subject__subject_template__academic_term__school_year={school_year}&pagination=true"
    else:
        url = based_url + "student-schedules/?pagination=true"
    
    headers = {
        "Authorization": f"Bearer {token}",
    }

    all_items = []
    try:
        while url:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return JsonResponse({'error': 'Failed to fetch data'}, status=response.status_code)

            data = response.json()

            if isinstance(data, dict) and 'results' in data:
                all_items.extend(data['results'])
                url = data.get('next') 
            elif isinstance(data, list):
                all_items.extend(data)
                url = None 
            else:
                return JsonResponse({'error': 'Unexpected data structure'}, status=500)


        # --- Integrate enrollment sync logic ---
        created_count = 0
        updated_count = 0
        failed_items = []

        for idx, item in enumerate(all_items, 1):
            try:
                student_email = item.get('student_school_email') or item.get('student_email', 'Unknown')
                subject_name = item.get('subject_name', 'Unknown')
                
                enrollment_obj = sync_enrollment(item)
                updated_count += 1
            except ValidationError as e:
                failed_items.append({
                    "data": item,
                    "error": str(e)
                })
            except Exception as e:
                failed_items.append({
                    "data": item,
                    "error": f"Unexpected error: {str(e)}"
                })

        # Create placeholder enrollments for subjects with no students
        placeholders_created = 0
        try:
            placeholders_created = create_placeholder_enrollments_for_empty_subjects()
        except Exception:
            pass

        result = {
            "total_fetched": len(all_items),
            "created": created_count,
            "updated": updated_count,
            "failed": len(failed_items),
            "placeholders_created": placeholders_created,
            "failed_items": failed_items[:5],  # Return first 5 failures
        }

        return JsonResponse(result, safe=False)
    
    except ConnectionError:
        return JsonResponse({
            'error': 'Unable to connect to RMS server. Please check if the server is running.',
            'details': f'Connection refused to {based_url}'
        }, status=503)
    except Timeout:
        return JsonResponse({
            'error': 'Request to RMS server timed out. Please try again later.',
        }, status=504)
    except RequestException as e:
        return JsonResponse({
            'error': 'Failed to communicate with RMS server.',
            'details': str(e)
        }, status=503)


@login_required
def term_data(request):
    """Queue terms sync as Celery task"""
    from rms.tasks import sync_terms_task
    
    task = sync_terms_task.delay(request.user.id)
    
    return JsonResponse({
        'status': 'queued',
        'message': 'Terms sync started in background',
        'task_id': task.id
    })


@login_required
def term_data_sync(request):
    """Original synchronous version (kept for reference/fallback)"""
    url = based_url + "terms/?current_semester=true"
    headers = {
        "Authorization": f"Bearer {token}",
    }

    all_items = []
    try:
        while url:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return JsonResponse({'error': 'Failed to fetch data'}, status=500)

            data = response.json()

            if isinstance(data, dict) and 'results' in data:
                all_items.extend(data['results'])
                url = data.get('next') 
            elif isinstance(data, list):
                all_items.extend(data)
                url = None 
            else:
                return JsonResponse({'error': 'Unexpected data structure'}, status=500)

        data = [item for item in all_items]
        sync_terms(data)

        return JsonResponse(data, safe=False)
    
    except ConnectionError:
        return JsonResponse({
            'error': 'Unable to connect to RMS server. Please check if the server is running.',
            'details': f'Connection refused to {based_url}'
        }, status=503)
    except Timeout:
        return JsonResponse({
            'error': 'Request to RMS server timed out. Please try again later.',
        }, status=504)
    except RequestException as e:
        return JsonResponse({
            'error': 'Failed to communicate with RMS server.',
            'details': str(e)
        }, status=503)


@login_required
def student_data(request):
    """Queue student data sync as Celery task"""
    from .tasks import sync_student_enrollments_task
    
    school_year = fetch_current_school_year()
    task = sync_student_enrollments_task.delay(request.user.id, school_year)
    
    return JsonResponse({
        'status': 'queued',
        'message': f'Student data sync started in background{" for " + school_year if school_year else ""}',
        'task_id': task.id,
        'school_year': school_year
    })


@login_required
def student_data_sync(request):
    """
    Original synchronous version (kept for reference/fallback).
    Sync student data from RMS API.
    Fetches student information and creates/updates user profiles.
    """
    school_year = fetch_current_school_year()   
    # Build URL with school year filter if available
    if school_year:
        url = based_url + f"students/?school_year={school_year}&has_school_email=true&pagination=true"
    else:
        url = based_url + "students/?has_school_email=true&pagination=true"
    
    headers = {
        "Authorization": f"Bearer {token}",
    }

    all_items = []
    try:
        while url:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return JsonResponse({'error': 'Failed to fetch data'}, status=response.status_code)

            data = response.json()

            if isinstance(data, dict) and 'results' in data:
                all_items.extend(data['results'])
                url = data.get('next')
            elif isinstance(data, list):
                all_items.extend(data)
                url = None
            else:
                return JsonResponse({'error': 'Unexpected data structure'}, status=500)


        # Sync student data
        created_count = 0
        updated_count = 0
        failed_items = []

        for idx, item in enumerate(all_items, 1):
            try:
                student_email = item.get('school_email') or item.get('email', 'Unknown')
                student_name = f"{item.get('first_name', '')} {item.get('last_name', '')}".strip()
                
                # sync_user_data has @transaction.atomic
                user_obj = sync_user_data(item)
                updated_count += 1
            except ValidationError as e:
                failed_items.append({
                    "email": item.get('school_email') or item.get('email', 'Unknown'),
                    "error": str(e)
                })
            except Exception as e:
                failed_items.append({
                    "email": item.get('school_email') or item.get('email', 'Unknown'),
                    "error": f"Unexpected error: {str(e)}"
                })

        result = {
            "total_fetched": len(all_items),
            "created": created_count,
            "updated": updated_count,
            "failed": len(failed_items),
            "failed_items": failed_items[:10],  # Return first 10 failures
        }

        return JsonResponse(result, safe=False)
    
    except ConnectionError:
        return JsonResponse({
            'error': 'Unable to connect to RMS server. Please check if the server is running.',
            'details': f'Connection refused to {based_url}'
        }, status=503)
    except Timeout:
        return JsonResponse({
            'error': 'Request to RMS server timed out. Please try again later.',
        }, status=504)
    except RequestException as e:
        return JsonResponse({
            'error': 'Failed to communicate with RMS server.',
            'details': str(e)
        }, status=503)


@login_required
def student_finances(request):
    user = request.user.email
    school_year = fetch_current_school_year()    
    semester = fetch_current_semester()

    url = based_url + f"student-finances/?academic_term_school_year={school_year}&academic_term_semester={semester}&email={user}"

    headers = {
        "Authorization": f"Bearer {token}",
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() 
        data = response.json()
        return JsonResponse(data, safe=False)

    except requests.exceptions.RequestException as e:
        return JsonResponse({"error": "Failed to fetch data", "details": str(e)}, status=500)


class StudentFinancesAPIView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_email = getattr(request.user, 'email', None)
        if not user_email:
            raise ValidationError({"email": "Authenticated user has no email."})

        params = {"school_email": user_email}

        school_year = request.query_params.get("school_year") or request.query_params.get("academic_term_school_year")
        semester = request.query_params.get("semester") or request.query_params.get("academic_term_semester")
        page = request.query_params.get("page")
        page_size = request.query_params.get("page_size")
        search = request.query_params.get("search")

        if school_year:
            params["academic_term_school_year"] = school_year
        if semester:
            params["academic_term_semester"] = semester
        if page:
            params["page"] = page
        if page_size:
            params["page_size"] = page_size
        if search:
            params["search"] = search

        url = based_url + "student-finances/"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if _is_empty_payload(data):
                return Response({"message": "No student finance records found.", "data": data}, status=status.HTTP_200_OK)
            return Response(data)
        except requests.exceptions.RequestException as e:
            return Response({"message": f"Failed to fetch student finances: {e}", "data": None}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as e:
            return Response({"message": f"Unexpected error: {e}", "data": None}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TermsAPIView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_email = getattr(request.user, 'email', None)
        if not user_email:
            raise ValidationError({"email": "Authenticated user has no email."})

        params = {"school_email": user_email}

        url = based_url + "academic-terms/"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if _is_empty_payload(data):
                return Response({"message": "No academic terms found.", "data": data}, status=status.HTTP_200_OK)
            return Response(data)
        except requests.exceptions.RequestException as e:
            return Response({"message": f"Failed to fetch academic terms: {e}", "data": None}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as e:
            return Response({"message": f"Unexpected error: {e}", "data": None}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GradesAPIView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_email = getattr(request.user, 'email', None)

        if not user_email:
            raise ValidationError({
                "email": "Authenticated user has no email."
            })

        school_year = request.query_params.get("school_year")

        # keep the email
        params = {
            "school_email": user_email
        }

        # optionally add school year
        if school_year:
            params["school_year"] = school_year

        url = based_url + "grades/grading-subjects/"

        headers = {
            "Authorization": f"Bearer {token}"
        }

        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=10
            )

            print(response.url)

            response.raise_for_status()

            data = response.json()
            if _is_empty_payload(data):
                return Response({"message": "No grades found.", "data": data}, status=status.HTTP_200_OK)
            return Response(data)

        except requests.exceptions.RequestException as e:
            return Response({"message": f"Failed to fetch grades: {e}", "data": None}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as e:
            return Response({"message": f"Unexpected error: {e}", "data": None}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@login_required
@permission_required('roles.view_role', raise_exception=True)
def rms_data_import(request):
    return render(request, 'rms/rms_import.html')


@login_required
def courses(request):
    """Queue the RMS courses + departments sync as a Celery task."""
    from rms.tasks import sync_courses_task

    task = sync_courses_task.delay(request.user.id)
    return JsonResponse({
        'status': 'queued',
        'message': 'Courses & departments sync started in background',
        'task_id': task.id,
    })


@login_required
@permission_required('roles.view_role', raise_exception=True)
def rms_import_task_status(request, task_id):
    """Return the status of a queued RMS sync Celery task. The UI polls this
    so it can show the real result (success/failure + reason) instead of
    stopping at the 'queued' acknowledgement.
    """
    try:
        from celery.result import AsyncResult
    except Exception as exc:
        logger.exception("Celery is not installed or configured: %s", exc)
        return JsonResponse({'error': 'Celery is not available', 'details': str(exc)}, status=500)

    try:
        result = AsyncResult(task_id)
        payload = {
            'task_id': task_id,
            'state': result.state,
            'ready': result.ready(),
            'successful': result.successful() if result.ready() else None,
        }
        if result.ready():
            if result.successful():
                payload['result'] = result.result
            else:
                # result.result holds the exception when failed.
                err = result.result
                payload['error'] = str(err) if err else 'Task failed without a message.'
                payload['traceback'] = result.traceback or ''
        return JsonResponse(payload)
    except Exception as exc:
        logger.exception("Failed to read task status for %s", task_id)
        return JsonResponse({'error': 'Failed to fetch task status', 'details': str(exc)}, status=500)

@login_required
def student_soa(request):
    user = request.user.email
    school_year = fetch_current_school_year()
    semester = fetch_current_semester()

    url = based_url + (
        f"student-finances/?academic_term_school_year={school_year}"
        f"&academic_term_semester={semester}&email={user}"
    )

    headers = {
        "Authorization": f"Bearer {token}",
    }

    finances = []
    error = None

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            finances = data.get("results", [])
        else:
            finances = data
    except requests.exceptions.RequestException as e:
        error = f"Failed to fetch data: {e}"

    def to_decimal(value):
        try:
            return Decimal(str(value))
        except Exception:
            return Decimal("0")

    context = {
        'finances': finances,
        'error': error,
        'misc_fees': [],
        'total_misc': Decimal("0"),
        'misc_payments_total': Decimal("0"),
        'misc_balance': Decimal("0"),
        'lab_fees': False,
        'lab_count': 0,
        'tuition_fees': False,
        'total_units': 0,
        'total_lab': Decimal("0"),
        'tuition_total': Decimal("0"),
        'total_lab_tuition': Decimal("0"),
        'scholarship_total': Decimal("0"),
        'adjusted_tuition_due': Decimal("0"),
        'tuition_payments_total': Decimal("0"),
        'tuition_balance': Decimal("0"),
        'other_fees': [],
        'total_other_fees': Decimal("0"),
        'other_payments_total': Decimal("0"),
        'other_balance': Decimal("0"),
        'outstanding_balance': Decimal("0"),
        'debug': None,
    }

    if finances:
        finance = finances[0]

        # --- Miscellaneous vs Other fees ---
        misc_raw = finance.get('miscellaneous_fees') or []
        misc_fees = []
        other_fees = []
        for fee in misc_raw:
            name = (fee.get('fee_item_name') or '').strip()
            amount = to_decimal(fee.get('final_cost'))
            entry = {'name': name, 'amount': amount}
            if name.lower().startswith('documentation'):
                other_fees.append(entry)
            else:
                misc_fees.append(entry)

        total_misc = sum((f['amount'] for f in misc_fees), Decimal("0"))
        total_other_fees = sum((f['amount'] for f in other_fees), Decimal("0"))

        misc_payments_total = Decimal("0")
        misc_balance = total_misc - misc_payments_total

        other_payments_total = Decimal("0")
        other_balance = total_other_fees - other_payments_total

        # --- Laboratory & Tuition fees from subject_fees ---
        subject_fees = finance.get('subject_fees') or []
        lab_count = 0
        total_lab = Decimal("0")
        tuition_total = Decimal("0")

        for sf in subject_fees:
            cost = to_decimal(sf.get('final_cost'))
            # Heuristic: large per-subject amounts (e.g. 2500) are lab fees
            if cost >= Decimal('2000'):
                lab_count += 1
                total_lab += cost
            else:
                tuition_total += cost

        total_lab_tuition = total_lab + tuition_total

        if tuition_total > 0:
            per_unit_rate = Decimal('200')
            total_units = int((tuition_total / per_unit_rate).quantize(Decimal('1')))
        else:
            total_units = 0

        lab_fees = lab_count > 0
        tuition_fees = tuition_total > 0

        # --- Scholarships and tuition info ---
        scholarships = finance.get('granted_scholarships') or []
        scholarship_total = sum((to_decimal(s.get('tuition_amount')) for s in scholarships), Decimal('0'))

        adjusted_tuition_due = total_lab_tuition - scholarship_total

        tuition_info = finance.get('tuition') or {}
        tuition_payments_total = to_decimal(tuition_info.get('amount_paid'))
        balance_value = tuition_info.get('balance')
        if balance_value is not None:
            tuition_balance = to_decimal(balance_value)
        else:
            tuition_balance = adjusted_tuition_due - tuition_payments_total

        outstanding_balance = misc_balance + tuition_balance + other_balance

        debug = {
            'terms_to_use': [finance.get('academic_term', {}).get('academic_term_code', '')],
            'student_subject_fees_count': len(subject_fees),
            'student_miscellaneous_fees_count': len(misc_raw),
        }

        context.update({
            'misc_fees': misc_fees,
            'total_misc': total_misc,
            'misc_payments_total': misc_payments_total,
            'misc_balance': misc_balance,
            'lab_fees': lab_fees,
            'lab_count': lab_count,
            'tuition_fees': tuition_fees,
            'total_units': total_units,
            'total_lab': total_lab,
            'tuition_total': tuition_total,
            'total_lab_tuition': total_lab_tuition,
            'scholarship_total': scholarship_total,
            'adjusted_tuition_due': adjusted_tuition_due,
            'tuition_payments_total': tuition_payments_total,
            'tuition_balance': tuition_balance,
            'other_fees': other_fees,
            'total_other_fees': total_other_fees,
            'other_payments_total': other_payments_total,
            'other_balance': other_balance,
            'outstanding_balance': outstanding_balance,
            'debug': debug,
        })

    return render(request, 'rms/student_SOA.html', context)


def fetch_student_total_payment(user_email):
    """Fetch total payment for a student from RMS API"""
    try:
        school_year = fetch_current_school_year()
        semester = fetch_current_semester()
        
        url = based_url + (
            f"student-finances/?academic_term_school_year={school_year}"
            f"&academic_term_semester={semester}&email={user_email}"
        )
        
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        finances = data.get("results", []) if isinstance(data, dict) else data
        
        if finances:
            finance = finances[0]

            def to_decimal(value):
                try:
                    return Decimal(str(value))
                except Exception:
                    return Decimal("0")

            outstanding_raw = finance.get('outstanding_balance')
            if outstanding_raw is not None:
                return to_decimal(outstanding_raw)

            misc_raw = finance.get('miscellaneous_fees') or []
            total_misc = sum((to_decimal(fee.get('final_cost')) for fee in misc_raw if not (fee.get('fee_item_name') or '').strip().lower().startswith('documentation')), Decimal('0'))
            total_other = sum((to_decimal(fee.get('final_cost')) for fee in misc_raw if (fee.get('fee_item_name') or '').strip().lower().startswith('documentation')), Decimal('0'))

            misc_balance = total_misc
            other_balance = total_other

            tuition_info = finance.get('tuition') or {}
            tuition_balance = to_decimal(tuition_info.get('balance'))
            if tuition_balance == Decimal('0') and tuition_info.get('balance') in (None, ''):
                tuition_payments_total = to_decimal(tuition_info.get('amount_paid'))
                subject_fees = finance.get('subject_fees') or []
                total_lab = Decimal('0')
                tuition_total = Decimal('0')
                for sf in subject_fees:
                    cost = to_decimal(sf.get('final_cost'))
                    if cost >= Decimal('2000'):
                        total_lab += cost
                    else:
                        tuition_total += cost

                scholarships = finance.get('granted_scholarships') or []
                scholarship_total = sum((to_decimal(s.get('tuition_amount')) for s in scholarships), Decimal('0'))
                adjusted_tuition_due = (total_lab + tuition_total) - scholarship_total
                tuition_balance = adjusted_tuition_due - tuition_payments_total

            return misc_balance + tuition_balance + other_balance
            
        
        return Decimal("0")
    except Exception as e:
        return Decimal("0")