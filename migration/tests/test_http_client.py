import pytest
import responses
from django.test import override_settings

from migration.client.exceptions import AuthError, PermanentError, ThrottledError, TransientError
from migration.client.http import OldLmsClient


@pytest.fixture
def client():
    return OldLmsClient(base_url="http://old/", token="abc", timeout=1, max_retries=2, backoff_base=0.01)


@responses.activate
def test_fetch_page_returns_decoded_body(client):
    responses.add(
        responses.GET,
        "http://old/api/migration/roles/role/",
        json={"results": [{"id": 1}], "next_cursor": None, "has_more": False, "total_estimated": 1},
        status=200,
    )
    body = client.fetch_page("roles", "role")
    assert body["results"] == [{"id": 1}]


@responses.activate
def test_fetch_page_sends_token_header(client):
    responses.add(responses.GET, "http://old/api/migration/roles/role/",
                  json={"results": []}, status=200)
    client.fetch_page("roles", "role")
    sent = responses.calls[0].request
    assert sent.headers.get("Authorization") == "Token abc"


@responses.activate
def test_fetch_page_appends_cursor_and_limit(client):
    responses.add(responses.GET, "http://old/api/migration/roles/role/",
                  json={"results": []}, status=200)
    client.fetch_page("roles", "role", cursor="42", limit=10)
    url = responses.calls[0].request.url
    assert "cursor=42" in url
    assert "limit=10" in url


@responses.activate
def test_401_raises_authentication_error(client):
    responses.add(responses.GET, "http://old/api/migration/roles/role/", status=401)
    with pytest.raises(AuthError):
        client.fetch_page("roles", "role")


@responses.activate
def test_403_raises_authentication_error(client):
    responses.add(responses.GET, "http://old/api/migration/roles/role/", status=403)
    with pytest.raises(AuthError):
        client.fetch_page("roles", "role")


@responses.activate
def test_429_raises_throttled_with_retry_after(client):
    responses.add(
        responses.GET, "http://old/api/migration/roles/role/",
        status=429, headers={"Retry-After": "7"},
    )
    with pytest.raises(ThrottledError) as exc:
        client.fetch_page("roles", "role")
    assert exc.value.retry_after == 7.0


@responses.activate
def test_500_retries_then_raises_transient(client):
    for _ in range(3):
        responses.add(responses.GET, "http://old/api/migration/roles/role/", status=500)
    with pytest.raises(TransientError):
        client.fetch_page("roles", "role")


@responses.activate
def test_404_raises_permanent(client):
    responses.add(responses.GET, "http://old/api/migration/roles/role/", status=404)
    with pytest.raises(PermanentError):
        client.fetch_page("roles", "role")


@responses.activate
def test_health_calls_health_endpoint(client):
    responses.add(responses.GET, "http://old/api/migration/health/", json={"ok": True}, status=200)
    assert client.health()["ok"] is True


@responses.activate
def test_fetch_by_pk_uses_detail_url(client):
    responses.add(responses.GET, "http://old/api/migration/roles/role/7/", json={"id": 7}, status=200)
    assert client.fetch_by_pk("roles", "role", 7)["id"] == 7
