import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from migration.mappers.base import MapperResult
from migration.models import IDMap
from migration.writers.base import RowWriter
from roles.models import Role


@pytest.fixture
def writer():
    return RowWriter(app_label="roles", model_name="Role", target_model=Role)


def test_writer_creates_new_row_and_idmap(writer):
    result = MapperResult(fields={"name": "Teacher"}, m2m_resolutions={})
    obj = writer.write(old_pk="1", mapper_result=result)
    assert obj.pk is not None
    assert Role.objects.get(pk=obj.pk).name == "Teacher"
    assert IDMap.resolve("roles", "Role", "1") == str(obj.pk)


def test_writer_is_idempotent_on_rerun(writer):
    r1 = writer.write(old_pk="1", mapper_result=MapperResult(fields={"name": "Teacher"}))
    r2 = writer.write(old_pk="1", mapper_result=MapperResult(fields={"name": "Teacher"}))
    assert r1.pk == r2.pk
    assert Role.objects.filter(name="Teacher").count() == 1


def test_writer_resolves_m2m_permission_codenames(writer):
    ct = ContentType.objects.first()
    perm = Permission.objects.create(content_type=ct, codename="dummy_xyz", name="Dummy")
    result = MapperResult(
        fields={"name": "Admin"},
        m2m_resolutions={"permissions": [(perm.content_type.app_label, "dummy_xyz")]},
    )
    role = writer.write(old_pk="2", mapper_result=result)
    assert list(role.permissions.values_list("codename", flat=True)) == ["dummy_xyz"]


def test_writer_dry_run_skips_save(writer):
    obj = writer.write(old_pk="3", mapper_result=MapperResult(fields={"name": "T"}), dry_run=True)
    assert obj is None
    assert not Role.objects.filter(name="T").exists()
    assert IDMap.resolve("roles", "Role", "3") is None
