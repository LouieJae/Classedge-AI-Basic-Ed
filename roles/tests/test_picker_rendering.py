"""[Classedge LMS] Tests that the role CRUD templates render the grouped
picker with the right content and pre-selected state."""
from html import unescape

from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse

from roles.models import Role
from roles.permission_categories import CATEGORY_ORDER, PERMISSION_CATEGORIES
from roles.tests.helpers import make_it_admin


class PickerRenderingTests(TestCase):
    """[Classedge LMS] End-to-end checks that the Task 7/8 template rewrites
    render the grouped picker correctly."""

    def setUp(self):
        self.admin = make_it_admin(username="picker_admin")
        self.client = Client()
        self.client.force_login(self.admin)

    def test_add_role_modal_renders_all_categories_in_order(self):
        """GET /role_list/ includes each category header in CATEGORY_ORDER
        order (the add-role modal is embedded on that page)."""
        resp = self.client.get(reverse("role_list"))
        self.assertEqual(resp.status_code, 200)
        # Unescape HTML entities so "Roles &amp; Permissions" matches
        # "Roles & Permissions" from CATEGORY_ORDER.
        html = unescape(resp.content.decode())
        positions = []
        for category in CATEGORY_ORDER:
            idx = html.find(category)
            self.assertNotEqual(
                idx, -1, f"Category {category!r} not rendered on /role_list/",
            )
            positions.append(idx)
        self.assertEqual(
            positions,
            sorted(positions),
            "Categories rendered out of CATEGORY_ORDER",
        )

    def test_update_role_preselects_current_permissions(self):
        """Permissions currently assigned to a role appear with checked=""
        in the HTML returned by /update_role/<id>/."""
        role = Role.objects.create(name="PickerTest")
        # Assign the first permission from each of 2 different categories.
        some_codename_strs = (
            PERMISSION_CATEGORIES["Messaging"][:1]
            + PERMISSION_CATEGORIES["Gradebook"][:1]
        )
        perms_to_assign = []
        for codename_str in some_codename_strs:
            app_label, codename = codename_str.split(".", 1)
            perms_to_assign.append(
                Permission.objects.get(
                    content_type__app_label=app_label, codename=codename,
                )
            )
        role.permissions.set(perms_to_assign)

        resp = self.client.get(reverse("update_role", args=[role.pk]))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        for p in perms_to_assign:
            marker = f'value="{p.id}"'
            self.assertIn(marker, html, f"Missing perm input for {p.codename}")
            # Look for 'checked' within 300 chars of the value attribute.
            vloc = html.find(marker)
            window = html[max(0, vloc - 300):vloc + 300]
            self.assertIn(
                "checked",
                window,
                f"Perm {p.codename} input not pre-checked on update_role",
            )

    def test_picker_hides_django_internal_permissions(self):
        """Permissions like auth.session, admin logentries, etc. do not
        leak into the picker. These should be absent from /role_list/'s HTML."""
        resp = self.client.get(reverse("role_list"))
        html = resp.content.decode()
        forbidden_codenames = [
            "add_session",
            "change_session",
            "add_logentry",
            "view_logentry",
            "add_contenttype",
            "add_permission",
        ]
        for code in forbidden_codenames:
            self.assertNotIn(
                code,
                html,
                f"Unexpected Django-internal permission leaked into picker: {code}",
            )
