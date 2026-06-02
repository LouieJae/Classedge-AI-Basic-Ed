import cuid
from django.test import RequestFactory, TestCase

from activity.models import Activity
from mobile.serializers.activity_details import ActivitySerializer


def _ctx(platform=None):
    """Build a DRF serializer context carrying a request with optional X-Platform."""
    factory = RequestFactory()
    headers = {'HTTP_X_PLATFORM': platform} if platform is not None else {}
    request = factory.post('/api/activity_activity/', **headers)
    return {'request': request}


class ActivitySerializerClientSuppliedLocalIdTests(TestCase):
    """Offline-first sync: mobile generates the Activity cuid on-device and
    sends it via POST. The server preserves that cuid as the PK *only* when
    the caller identifies itself with `X-Platform: mobile`. Any other caller
    (web, missing header, spoofed value) gets a server-generated cuid even
    if they happen to include a local_id in the payload, so a buggy or
    rogue web client can't hijack the PK.
    """

    def test_mobile_header_preserves_client_supplied_local_id(self):
        client_cuid = cuid.cuid()

        serializer = ActivitySerializer(
            data={'local_id': client_cuid, 'activity_name': 'Mobile-Sync Activity'},
            context=_ctx(platform='mobile'),
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        activity = serializer.save()

        self.assertEqual(activity.pk, client_cuid)
        self.assertEqual(Activity.objects.get(pk=client_cuid).activity_name,
                         'Mobile-Sync Activity')

    def test_mobile_header_is_case_insensitive(self):
        client_cuid = cuid.cuid()

        serializer = ActivitySerializer(
            data={'local_id': client_cuid, 'activity_name': 'Mobile-Case'},
            context=_ctx(platform='Mobile'),
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        activity = serializer.save()

        self.assertEqual(activity.pk, client_cuid)

    def test_mobile_header_without_local_id_generates_server_cuid(self):
        serializer = ActivitySerializer(
            data={'activity_name': 'Mobile-No-Local-Id'},
            context=_ctx(platform='mobile'),
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        activity = serializer.save()

        self.assertEqual(len(activity.pk), 25)  # cuid length

    def test_web_header_ignores_client_supplied_local_id(self):
        attempted_cuid = cuid.cuid()

        serializer = ActivitySerializer(
            data={'local_id': attempted_cuid, 'activity_name': 'Web-Tries-To-Set-Id'},
            context=_ctx(platform='web'),
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        activity = serializer.save()

        self.assertNotEqual(activity.pk, attempted_cuid)
        self.assertEqual(len(activity.pk), 25)

    def test_missing_platform_header_ignores_client_supplied_local_id(self):
        attempted_cuid = cuid.cuid()

        serializer = ActivitySerializer(
            data={'local_id': attempted_cuid, 'activity_name': 'No-Header'},
            context=_ctx(platform=None),
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        activity = serializer.save()

        self.assertNotEqual(activity.pk, attempted_cuid)
        self.assertEqual(len(activity.pk), 25)

    def test_mobile_header_with_blank_local_id_generates_server_cuid(self):
        serializer = ActivitySerializer(
            data={'local_id': '', 'activity_name': 'Blank-Local-Id'},
            context=_ctx(platform='mobile'),
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        activity = serializer.save()

        self.assertEqual(len(activity.pk), 25)
