import pytest

from migration.mappers import get_mapper, register_mapper
from migration.mappers.base import MapperResult, MissingFKError, require_fk
from migration.models import IDMap


def test_register_and_get_mapper():
    @register_mapper("dummy", "Thing")
    def mapper(payload):
        return MapperResult(fields={"id": payload["id"]})

    assert get_mapper("dummy", "Thing") is mapper


def test_get_mapper_unknown_raises():
    with pytest.raises(KeyError):
        get_mapper("nope", "Nope")


def test_require_fk_returns_new_pk_when_idmap_present():
    IDMap.objects.create(app_label="roles", model_name="Role", old_pk="5", new_pk="55")
    assert require_fk("roles", "Role", 5) == "55"


def test_require_fk_raises_when_missing():
    with pytest.raises(MissingFKError) as exc:
        require_fk("roles", "Role", 999)
    assert exc.value.target_app == "roles"
    assert exc.value.target_model == "Role"
    assert exc.value.old_pk == "999"
