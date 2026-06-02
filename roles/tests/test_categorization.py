"""[Classedge LMS] CI guard — enforces PERMISSION_CATEGORIES completeness.

If any of these tests fail on a PR, the fix is to add the missing/fix the
broken entry in roles/permission_categories.py (usually one line).
"""
from django.contrib.auth.models import Permission
from django.test import TestCase

from roles.permission_categories import (
    CATEGORY_ORDER,
    EXPLICITLY_EXCLUDED_MODELS,
    PERMISSION_CATEGORIES,
)


# Apps whose permissions MUST appear in PERMISSION_CATEGORIES. Dead
# app_labels ("attendance", "studentgrade") from the pre-Phase-3 whitelist
# are NOT listed — they reference apps that don't exist in the project.
CLASSEDGE_APPS: list[str] = [
    "accounts",
    "activity",
    "calendars",
    "classroom",
    "course",
    "gradebookcomponent",
    "logs",
    "message",
    "module",
    "roles",
    "subject",
]


class CategorizationCompletenessTests(TestCase):
    def test_every_permission_from_our_apps_is_categorized(self):
        """Every Permission from a Classedge-owned app must appear in some
        category (unless its model is in EXPLICITLY_EXCLUDED_MODELS)."""
        all_categorized = {
            codename
            for perms in PERMISSION_CATEGORIES.values()
            for codename in perms
        }
        db_perms = Permission.objects.filter(
            content_type__app_label__in=CLASSEDGE_APPS
        ).exclude(
            content_type__model__in=EXPLICITLY_EXCLUDED_MODELS
        ).select_related("content_type")
        missing = sorted(
            f"{p.content_type.app_label}.{p.codename}"
            for p in db_perms
            if f"{p.content_type.app_label}.{p.codename}" not in all_categorized
        )
        self.assertEqual(
            missing,
            [],
            f"Uncategorized permissions (add each to roles/permission_categories.py): {missing}",
        )

    def test_no_permission_is_in_two_categories(self):
        """A permission must live in exactly one category — enforces the
        single-source-of-truth invariant."""
        seen: dict[str, str] = {}
        duplicates: list[tuple[str, str, str]] = []
        for category, codenames in PERMISSION_CATEGORIES.items():
            for codename in codenames:
                if codename in seen:
                    duplicates.append((codename, seen[codename], category))
                seen[codename] = category
        self.assertEqual(
            duplicates,
            [],
            f"Permissions appearing in multiple categories: {duplicates}",
        )

    def test_every_categorized_codename_resolves_to_a_real_permission(self):
        """Typos ('gradebookcomponent.add_gradebok') and orphaned entries
        (categorized codename pointing at a deleted model) fail here."""
        # Pre-index all permissions from CLASSEDGE_APPS in one query so this
        # test stays fast as PERMISSION_CATEGORIES grows.
        # Note: index covers only CLASSEDGE_APPS. If a codename is added from
        # a new app, that app must be added to CLASSEDGE_APPS first, or this
        # test reports it as "unresolved" without checking the DB.
        index = {
            (p.content_type.app_label, p.codename)
            for p in Permission.objects.filter(
                content_type__app_label__in=CLASSEDGE_APPS
            ).select_related("content_type")
        }
        unresolved: list[str] = []
        for codenames in PERMISSION_CATEGORIES.values():
            for codename_str in codenames:
                try:
                    app_label, codename = codename_str.split(".", 1)
                except ValueError:
                    unresolved.append(codename_str)
                    continue
                if (app_label, codename) not in index:
                    unresolved.append(codename_str)
        self.assertEqual(
            unresolved,
            [],
            f"Categorized codenames that don't resolve to real Permissions: {unresolved}",
        )


class CategoryOrderTests(TestCase):
    def test_category_order_matches_permission_categories_keys(self):
        """CATEGORY_ORDER must list every category defined in
        PERMISSION_CATEGORIES, with no extras."""
        self.assertEqual(
            sorted(CATEGORY_ORDER),
            sorted(PERMISSION_CATEGORIES.keys()),
            "CATEGORY_ORDER is out of sync with PERMISSION_CATEGORIES keys",
        )


class HelperFunctionTests(TestCase):
    def test_get_categorized_permissions_returns_categories_in_order(self):
        """Helper returns list[(label, list[Permission])] matching CATEGORY_ORDER."""
        from roles.permission_categories import get_categorized_permissions
        result = get_categorized_permissions()
        labels = [label for label, _ in result]
        self.assertEqual(labels, CATEGORY_ORDER)

    def test_get_categorized_permissions_each_bucket_is_nonempty(self):
        from roles.permission_categories import get_categorized_permissions
        for label, perms in get_categorized_permissions():
            self.assertGreater(
                len(perms), 0, f"Category {label!r} has no resolvable permissions"
            )

    def test_get_categorized_permissions_only_resolves_real_permissions(self):
        """Each returned Permission is a real DB row (not a mock)."""
        from roles.permission_categories import get_categorized_permissions
        for _, perms in get_categorized_permissions():
            for p in perms:
                self.assertIsNotNone(p.pk)

    def test_get_all_categorized_permissions_is_flat_superset(self):
        """get_all_categorized_permissions() returns every Permission that
        appears somewhere in the categorized list."""
        from roles.permission_categories import (
            get_all_categorized_permissions,
            get_categorized_permissions,
        )
        flat_ids = set(get_all_categorized_permissions().values_list("id", flat=True))
        grouped_ids = {
            p.id for _, perms in get_categorized_permissions() for p in perms
        }
        self.assertEqual(flat_ids, grouped_ids)
