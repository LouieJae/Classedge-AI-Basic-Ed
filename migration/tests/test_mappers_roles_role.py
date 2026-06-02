import pytest

from migration.mappers.base import MapperResult
from migration.mappers.roles_role import map_role


def test_map_role_basic_fields():
    payload = {
        "id": 1, "name": "Teacher", "permissions": [],
        "created_at": "2024-01-01T00:00:00Z", "updated_at": None,
    }
    result = map_role(payload)
    assert isinstance(result, MapperResult)
    assert result.fields["name"] == "Teacher"
    assert result.fields["created_at"] == "2024-01-01T00:00:00Z"


def test_map_role_records_m2m_permission_codenames():
    payload = {
        "id": 1, "name": "Admin",
        "permissions": [
            {"app_label": "auth", "codename": "add_user"},
            {"app_label": "auth", "codename": "change_user"},
        ],
        "created_at": "2024-01-01T00:00:00Z", "updated_at": None,
    }
    result = map_role(payload)
    assert "permissions" in result.m2m_resolutions
    assert result.m2m_resolutions["permissions"] == [
        ("auth", "add_user"), ("auth", "change_user"),
    ]


def test_map_role_missing_name_raises_keyerror():
    with pytest.raises(KeyError):
        map_role({"id": 1, "permissions": []})
