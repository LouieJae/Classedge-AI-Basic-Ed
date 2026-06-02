import json
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from gamification.models import BadgeDefinition, StudentBadge

User = get_user_model()


class SetFeaturedBadgesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', email='alice@example.com', password='pw')
        self.other = User.objects.create_user(username='bob', email='bob@example.com', password='pw')
        self.client = Client()
        self.client.login(username='alice', password='pw')
        self.badges = []
        for i in range(7):
            defn = BadgeDefinition.objects.create(
                code=f'b{i}', name=f'Badge {i}', description='d',
                tier='bronze', icon='🥉',
            )
            self.badges.append(
                StudentBadge.objects.create(student=self.user, badge=defn)
            )

    def _post(self, ids):
        return self.client.post(
            reverse('set_featured_badges'),
            json.dumps({'badge_ids': ids}),
            content_type='application/json',
        )

    def test_requires_login(self):
        self.client.logout()
        resp = self._post([b.id for b in self.badges[:5]])
        self.assertEqual(resp.status_code, 302)

    def test_rejects_count_below_5(self):
        resp = self._post([self.badges[0].id, self.badges[1].id])
        self.assertEqual(resp.status_code, 400)

    def test_rejects_count_above_5(self):
        resp = self._post([b.id for b in self.badges[:6]])
        self.assertEqual(resp.status_code, 400)

    def test_rejects_badges_not_owned(self):
        other_defn = BadgeDefinition.objects.create(
            code='x', name='X', description='d', tier='gold', icon='🥇',
        )
        other_sb = StudentBadge.objects.create(student=self.other, badge=other_defn)
        ids = [b.id for b in self.badges[:4]] + [other_sb.id]
        resp = self._post(ids)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            StudentBadge.objects.filter(is_featured=True).count(), 0
        )

    def test_replaces_featured_set_atomically(self):
        first = [b.id for b in self.badges[:5]]
        resp = self._post(first)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            set(StudentBadge.objects
                .filter(student=self.user, is_featured=True)
                .values_list('id', flat=True)),
            set(first),
        )

        second = [b.id for b in self.badges[2:7]]
        resp = self._post(second)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            set(StudentBadge.objects
                .filter(student=self.user, is_featured=True)
                .values_list('id', flat=True)),
            set(second),
        )

    def test_get_method_not_allowed(self):
        resp = self.client.get(reverse('set_featured_badges'))
        self.assertEqual(resp.status_code, 405)

    def test_invalid_json(self):
        resp = self.client.post(
            reverse('set_featured_badges'),
            'not json',
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_rejects_duplicate_ids(self):
        """5 entries but all the same id → only 1 owned match → reject."""
        single_id = self.badges[0].id
        resp = self._post([single_id] * 5)
        self.assertEqual(resp.status_code, 400)

    def test_success_response_body_shape(self):
        """Successful POST returns featured_ids list matching what was sent."""
        ids = [b.id for b in self.badges[:5]]
        resp = self._post(ids)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('featured_ids', data)
        self.assertEqual(set(data['featured_ids']), set(ids))

    def test_error_response_body_shape(self):
        """Validation errors return an `error` key with a message."""
        resp = self._post([self.badges[0].id])
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertIn('error', data)
        self.assertTrue(isinstance(data['error'], str) and len(data['error']) > 0)
