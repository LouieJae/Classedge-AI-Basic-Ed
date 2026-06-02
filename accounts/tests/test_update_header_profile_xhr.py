import json
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import Profile

User = get_user_model()


class UpdateHeaderProfileXHRTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alice', password='pw', email='alice-xhr@example.com'
        )
        # Profile may or may not exist depending on signals; ensure one exists.
        self.profile, _ = Profile.objects.get_or_create(user=self.user)
        self.client = Client()
        self.client.login(username='alice', password='pw')
        self.url = reverse('update_header_profile', kwargs={'user_id': self.user.id})

    def test_xhr_success_returns_json_with_redirect(self):
        resp = self.client.post(
            self.url,
            data={'phone_number': '+639170000000', 'address': '123 Test St'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body.get('ok'))
        self.assertIn('redirect', body)

    def test_xhr_validation_error_returns_400_json(self):
        resp = self.client.post(
            self.url,
            data={'date_of_birth': '2999-01-01'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertFalse(body.get('ok'))
        self.assertIn('errors', body)

    def test_non_xhr_still_redirects(self):
        resp = self.client.post(
            self.url,
            data={'phone_number': '+639170000000'},
        )
        self.assertEqual(resp.status_code, 302)
