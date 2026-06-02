"""[Classedge LMS] Smoke tests for the streaming RMS sync helpers.

These tests exercise the new `_iter_rms_pages` generator and verify that
each sync task processes pages incrementally rather than buffering the
entire payload. They mock `requests.get` so no live RMS calls happen.
"""
from unittest import mock

from django.test import TestCase

from rms import tasks


def _page_response(results, next_url=None):
    """Build a fake DRF-style paginated response object."""
    resp = mock.Mock()
    resp.status_code = 200
    resp.json.return_value = {"results": results, "next": next_url}
    return resp


class IterRmsPagesTest(TestCase):
    """[Classedge LMS] Streaming generator must process page-by-page."""

    def test_appends_page_size_when_missing(self):
        with mock.patch("rms.tasks.requests.get") as gget:
            gget.return_value = _page_response([], next_url=None)
            list(tasks._iter_rms_pages("https://rms/api/foo/", {}, label="x"))
            called_url = gget.call_args_list[0][0][0]
            self.assertIn("page_size=500", called_url)

    def test_does_not_double_append_page_size(self):
        with mock.patch("rms.tasks.requests.get") as gget:
            gget.return_value = _page_response([], next_url=None)
            list(tasks._iter_rms_pages(
                "https://rms/api/foo/?page_size=100", {}, label="x",
            ))
            called_url = gget.call_args_list[0][0][0]
            self.assertEqual(called_url.count("page_size="), 1)
            self.assertIn("page_size=100", called_url)

    def test_streams_pages_in_order_and_aggregates_total(self):
        with mock.patch("rms.tasks.requests.get") as gget:
            gget.side_effect = [
                _page_response([{"id": 1}, {"id": 2}], next_url="https://rms/api/foo/?cursor=p2"),
                _page_response([{"id": 3}], next_url="https://rms/api/foo/?cursor=p3"),
                _page_response([{"id": 4}, {"id": 5}], next_url=None),
            ]
            collected = []
            page_numbers = []
            running_totals = []
            for page, total, page_no in tasks._iter_rms_pages(
                "https://rms/api/foo/", {}, label="x",
            ):
                collected.extend(page)
                page_numbers.append(page_no)
                running_totals.append(total)
            self.assertEqual([x["id"] for x in collected], [1, 2, 3, 4, 5])
            self.assertEqual(page_numbers, [1, 2, 3])
            self.assertEqual(running_totals, [2, 3, 5])

    def test_handles_unpaginated_list_response(self):
        with mock.patch("rms.tasks.requests.get") as gget:
            resp = mock.Mock()
            resp.status_code = 200
            resp.json.return_value = [{"id": 7}, {"id": 8}]
            gget.return_value = resp
            pages = list(tasks._iter_rms_pages("https://rms/api/foo/", {}, label="x"))
            self.assertEqual(len(pages), 1)
            self.assertEqual([x["id"] for x in pages[0][0]], [7, 8])

    def test_raises_on_non_200(self):
        with mock.patch("rms.tasks.requests.get") as gget:
            resp = mock.Mock()
            resp.status_code = 500
            gget.return_value = resp
            with self.assertRaises(Exception):
                list(tasks._iter_rms_pages("https://rms/api/foo/", {}, label="x"))


class SyncTermsTaskStreamingTest(TestCase):
    """[Classedge LMS] sync_terms_task should call sync_terms once per page."""

    def test_calls_sync_terms_per_page(self):
        pages = [
            _page_response([{"term_name": "Prelim"}, {"term_name": "Midterm"}],
                           next_url="https://rms/api/terms/?cursor=p2"),
            _page_response([{"term_name": "Final"}], next_url=None),
        ]
        with mock.patch("rms.tasks.requests.get", side_effect=pages), \
             mock.patch("rms.utils.sync_terms") as msync:
            result = tasks.sync_terms_task.apply(args=[1]).get()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["total_synced"], 3)
        self.assertEqual(msync.call_count, 2)
        self.assertEqual(len(msync.call_args_list[0][0][0]), 2)
        self.assertEqual(len(msync.call_args_list[1][0][0]), 1)


class SyncAcademicTermsTaskStreamingTest(TestCase):
    """[Classedge LMS] sync_academic_terms_task filters per page before syncing."""

    def test_filters_current_semester_per_page(self):
        pages = [
            _page_response([
                {"semester": "1st", "current_semester": True},
                {"semester": "2nd", "current_semester": False},
            ], next_url="https://rms/api/academic-terms/?cursor=p2"),
            _page_response([
                {"semester": "Summer", "current_semester": True},
            ], next_url=None),
        ]
        with mock.patch("rms.tasks.requests.get", side_effect=pages), \
             mock.patch("rms.utils.sync_semesters") as msync:
            result = tasks.sync_academic_terms_task.apply(args=[1]).get()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["total_synced"], 2)
        self.assertEqual(msync.call_count, 2)
        self.assertEqual(len(msync.call_args_list[0][0][0]), 1)
        self.assertEqual(len(msync.call_args_list[1][0][0]), 1)


class DryRunTest(TestCase):
    """[Classedge LMS] dry_run=True must skip every sync_* call but still walk pages."""

    def test_terms_dry_run_does_not_write(self):
        pages = [
            _page_response([{"term_name": "Prelim"}], next_url="https://rms/api/terms/?cursor=p2"),
            _page_response([{"term_name": "Midterm"}], next_url=None),
        ]
        with mock.patch("rms.tasks.requests.get", side_effect=pages), \
             mock.patch("rms.utils.sync_terms") as msync:
            result = tasks.sync_terms_task.apply(args=[1, True]).get()
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["pages"], 2)
        self.assertEqual(result["total_synced"], 2)
        msync.assert_not_called()

    def test_courses_dry_run_skips_writes_but_counts(self):
        pages = [
            _page_response([
                {"course_name": "BSIT", "status": "active"},
                {"course_name": "BSCS", "status": "inactive"},
            ], next_url="https://rms/api/courses/?cursor=p2"),
            _page_response([
                {"course_name": "BSCpE", "status": "active"},
            ], next_url=None),
        ]
        with mock.patch("rms.tasks.requests.get", side_effect=pages), \
             mock.patch("rms.utils.sync_courses") as msync:
            result = tasks.sync_courses_task.apply(args=[1, True]).get()
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["pages"], 2)
        # 2 active rows counted; the inactive one was filtered out
        self.assertEqual(result["total_fetched"], 2)
        # Real write helper must not have run
        msync.assert_not_called()


class SyncCoursesTaskStreamingTest(TestCase):
    """[Classedge LMS] sync_courses_task aggregates counts across pages."""

    def test_aggregates_counts_and_skips_inactive(self):
        pages = [
            _page_response([
                {"course_name": "BSIT", "status": "active"},
                {"course_name": "BSCS", "status": "inactive"},
            ], next_url="https://rms/api/courses/?cursor=p2"),
            _page_response([
                {"course_name": "BSCpE", "status": "active"},
            ], next_url=None),
        ]
        def fake_sync(items):
            return {
                "total_fetched": len(items),
                "departments_created": 0,
                "departments_updated": 0,
                "courses_created": len(items),
                "courses_updated": 0,
                "failed": 0,
                "failed_items": [],
            }
        with mock.patch("rms.tasks.requests.get", side_effect=pages), \
             mock.patch("rms.utils.sync_courses", side_effect=fake_sync) as msync:
            result = tasks.sync_courses_task.apply(args=[1]).get()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["courses_created"], 2)
        self.assertEqual(result["total_fetched"], 2)
        self.assertEqual(msync.call_count, 2)
