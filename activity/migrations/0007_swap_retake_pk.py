from django.db import migrations, models
import cuid


def run_swap_sql(apps, schema_editor):
    """Execute the Retake PK swap appropriate for the current vendor."""
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute(SWAP_SQL)
    elif schema_editor.connection.vendor == 'sqlite':
        _run_sqlite_swap(apps, schema_editor)


def _run_sqlite_swap(apps, schema_editor):
    """SQLite path: rebuild tables so FK checks pass against test DB."""
    raw_conn = schema_editor.connection.connection
    raw_conn.execute('PRAGMA foreign_keys = OFF')
    try:
        # Remap child FK values from parent.id (int) → parent.local_id (cuid)
        # BEFORE the parent rebuild drops the int id column. Without this step
        # the join key is gone and child rows keep stale int FK values that
        # don't match any local_id (mirrors the postgres SWAP_SQL UPDATE …
        # FROM … WHERE c.retake_record_id = rr.id block at the top of SWAP_SQL).
        # SQLite tolerates storing the cuid string in the existing bigint column;
        # _sqlite_fix_fk_to below rewrites the REFERENCES clause to match.
        raw_conn.execute(
            'UPDATE activity_retakerecorddetail '
            'SET retake_record_id = ('
            '  SELECT rr.local_id FROM activity_retakerecord rr '
            '  WHERE rr.id = activity_retakerecorddetail.retake_record_id'
            ') '
            'WHERE retake_record_id IS NOT NULL'
        )
        raw_conn.execute(
            'UPDATE mobile_attachment '
            'SET record_details_id = ('
            '  SELECT rrd.local_id FROM activity_retakerecorddetail rrd '
            '  WHERE rrd.id = mobile_attachment.record_details_id'
            ') '
            'WHERE record_details_id IS NOT NULL'
        )

        _sqlite_rebuild_table(raw_conn, 'activity_retakerecord', {
            'drop_columns': ['id'],
            'make_pk': 'local_id',
            'pk_type': 'varchar(36)',
        })
        _sqlite_rebuild_table(raw_conn, 'activity_retakerecorddetail', {
            'drop_columns': ['id'],
            'make_pk': 'local_id',
            'pk_type': 'varchar(36)',
        })
        _sqlite_fix_fk_to(raw_conn, 'activity_retakerecorddetail',
                          parent='activity_retakerecord')
        _sqlite_fix_fk_to(raw_conn, 'mobile_attachment',
                          parent='activity_retakerecorddetail')
    finally:
        raw_conn.execute('PRAGMA foreign_keys = ON')
        raw_conn.commit()


def _sqlite_rebuild_table(raw_conn, table_name, opts=None):
    import re

    opts = opts or {}
    drop_cols = set(opts.get('drop_columns', []))
    make_pk = opts.get('make_pk')
    pk_type = opts.get('pk_type', 'varchar(36)')

    row = raw_conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    if not row:
        return
    old_sql = row[0]

    inner_match = re.search(r'\((.+)\)\s*$', old_sql, re.DOTALL)
    if not inner_match:
        return
    inner = inner_match.group(1)
    parts = _split_sqlite_columns(inner)

    new_parts = []
    col_names_keep = []

    for part in parts:
        stripped = part.strip()
        col_match = re.match(r'^"?(\w+)"?\s+', stripped)
        if col_match:
            col = col_match.group(1)
            if col.lower() in ('primary', 'unique', 'check', 'foreign', 'constraint'):
                if col.lower() not in ('primary',):
                    new_parts.append(stripped)
                continue
            if col in drop_cols:
                continue
            if make_pk and col == make_pk:
                stripped = f'"{col}" {pk_type} NOT NULL PRIMARY KEY'
            col_names_keep.append(col)
        new_parts.append(stripped)

    tmp_name = f'new__{table_name}'
    new_sql = f'CREATE TABLE "{tmp_name}" (\n    ' + ',\n    '.join(new_parts) + '\n)'
    col_list = ', '.join(f'"{c}"' for c in col_names_keep)

    raw_conn.execute(new_sql)
    raw_conn.execute(
        f'INSERT INTO "{tmp_name}" ({col_list}) '
        f'SELECT {col_list} FROM "{table_name}"'
    )
    raw_conn.execute(f'DROP TABLE "{table_name}"')
    raw_conn.execute(f'ALTER TABLE "{tmp_name}" RENAME TO "{table_name}"')


def _sqlite_fix_fk_to(raw_conn, table_name, parent):
    """Rewrite a child table's FK to reference parent(local_id) instead of parent(id)."""
    import re

    row = raw_conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    if not row:
        return
    old_sql = row[0]

    if parent not in old_sql:
        return

    new_sql = re.sub(
        r'REFERENCES\s+"' + re.escape(parent) + r'"\s+\("id"\)',
        f'REFERENCES "{parent}" ("local_id")',
        old_sql,
    )
    new_sql = re.sub(
        r'REFERENCES\s+"' + re.escape(parent) + r'"\("id"\)',
        f'REFERENCES "{parent}" ("local_id")',
        new_sql,
    )
    new_sql = re.sub(
        r'REFERENCES "' + re.escape(parent) + r'"(?!\s*\("local_id"\))(?!\s*\("\w)',
        f'REFERENCES "{parent}" ("local_id")',
        new_sql,
    )

    if new_sql == old_sql:
        return

    tmp_name = f'new__{table_name}'
    new_create = re.sub(
        r'CREATE TABLE "' + re.escape(table_name) + '"',
        f'CREATE TABLE "{tmp_name}"',
        new_sql,
    )

    col_info = raw_conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    col_names = [r[1] for r in col_info]
    col_list = ', '.join(f'"{c}"' for c in col_names)

    raw_conn.execute(new_create)
    raw_conn.execute(
        f'INSERT INTO "{tmp_name}" ({col_list}) '
        f'SELECT {col_list} FROM "{table_name}"'
    )
    raw_conn.execute(f'DROP TABLE "{table_name}"')
    raw_conn.execute(f'ALTER TABLE "{tmp_name}" RENAME TO "{table_name}"')


def _split_sqlite_columns(inner):
    parts = []
    depth = 0
    current = []
    for char in inner:
        if char == '(':
            depth += 1
            current.append(char)
        elif char == ')':
            depth -= 1
            current.append(char)
        elif char == ',' and depth == 0:
            parts.append(''.join(current).strip())
            current = []
        else:
            current.append(char)
    if current:
        parts.append(''.join(current).strip())
    return [p for p in parts if p]


SWAP_SQL = r"""
-- 1. Add new varchar(36) FK columns (nullable for now) on the two child tables.
ALTER TABLE activity_retakerecorddetail ADD COLUMN retake_record_new_id varchar(36);
ALTER TABLE mobile_attachment ADD COLUMN record_details_new_id varchar(36);

-- 2. Populate from existing integer-FK joins. Parent integer ids still exist.
UPDATE activity_retakerecorddetail c
   SET retake_record_new_id = rr.local_id
  FROM activity_retakerecord rr
 WHERE c.retake_record_id = rr.id;

UPDATE mobile_attachment a
   SET record_details_new_id = rrd.local_id
  FROM activity_retakerecorddetail rrd
 WHERE a.record_details_id = rrd.id;

-- 3. Drop the old FK columns (CASCADE drops Django-named FK constraint + index).
ALTER TABLE activity_retakerecorddetail DROP COLUMN retake_record_id CASCADE;
ALTER TABLE mobile_attachment DROP COLUMN record_details_id CASCADE;

-- 4. Rename new columns into place.
ALTER TABLE activity_retakerecorddetail RENAME COLUMN retake_record_new_id TO retake_record_id;
ALTER TABLE mobile_attachment RENAME COLUMN record_details_new_id TO record_details_id;

SET CONSTRAINTS ALL IMMEDIATE;

-- 5. Swap activity_retakerecorddetail PK: drop integer PK, drop UNIQUE on local_id
--    (added by 0006; hash-suffixed name varies per environment), promote local_id to PK.
ALTER TABLE activity_retakerecorddetail DROP CONSTRAINT activity_retakerecorddetail_pkey CASCADE;
ALTER TABLE activity_retakerecorddetail DROP COLUMN id;
DO $$
DECLARE uniq_name text;
BEGIN
    SELECT conname INTO uniq_name FROM pg_constraint
     WHERE conrelid = 'activity_retakerecorddetail'::regclass
       AND contype = 'u'
       AND conkey = ARRAY[(SELECT attnum FROM pg_attribute
                            WHERE attrelid = 'activity_retakerecorddetail'::regclass
                              AND attname = 'local_id')];
    IF uniq_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE activity_retakerecorddetail DROP CONSTRAINT %%I', uniq_name);
    END IF;
END $$;
ALTER TABLE activity_retakerecorddetail ALTER COLUMN local_id SET NOT NULL;
ALTER TABLE activity_retakerecorddetail ADD PRIMARY KEY (local_id);

-- 6. Same for activity_retakerecord.
ALTER TABLE activity_retakerecord DROP CONSTRAINT activity_retakerecord_pkey CASCADE;
ALTER TABLE activity_retakerecord DROP COLUMN id;
DO $$
DECLARE uniq_name text;
BEGIN
    SELECT conname INTO uniq_name FROM pg_constraint
     WHERE conrelid = 'activity_retakerecord'::regclass
       AND contype = 'u'
       AND conkey = ARRAY[(SELECT attnum FROM pg_attribute
                            WHERE attrelid = 'activity_retakerecord'::regclass
                              AND attname = 'local_id')];
    IF uniq_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE activity_retakerecord DROP CONSTRAINT %%I', uniq_name);
    END IF;
END $$;
ALTER TABLE activity_retakerecord ALTER COLUMN local_id SET NOT NULL;
ALTER TABLE activity_retakerecord ADD PRIMARY KEY (local_id);

-- 7. Recreate FKs against the new string PKs.
ALTER TABLE activity_retakerecorddetail
    ADD CONSTRAINT activity_retakerecorddetail_retake_record_id_fkey
    FOREIGN KEY (retake_record_id) REFERENCES activity_retakerecord(local_id)
    ON DELETE CASCADE
    DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE mobile_attachment
    ADD CONSTRAINT mobile_attachment_record_details_id_fkey
    FOREIGN KEY (record_details_id) REFERENCES activity_retakerecorddetail(local_id)
    DEFERRABLE INITIALLY DEFERRED;

CREATE INDEX IF NOT EXISTS activity_retakerecorddetail_retake_record_id_idx
    ON activity_retakerecorddetail(retake_record_id);
CREATE INDEX IF NOT EXISTS mobile_attachment_record_details_id_idx
    ON mobile_attachment(record_details_id);
"""


class Migration(migrations.Migration):

    dependencies = [
        ('activity', '0006_retake_local_id_unique'),
        ('mobile', '0002_attachment_activity_question_and_more'),
    ]

    operations = [
        migrations.RunPython(
            code=run_swap_sql,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(model_name='retakerecord', name='id'),
                migrations.RemoveField(model_name='retakerecorddetail', name='id'),
                migrations.AlterField(
                    model_name='retakerecord',
                    name='local_id',
                    field=models.CharField(
                        max_length=36, primary_key=True,
                        default=cuid.cuid, editable=False, serialize=False,
                    ),
                ),
                migrations.AlterField(
                    model_name='retakerecorddetail',
                    name='local_id',
                    field=models.CharField(
                        max_length=36, primary_key=True,
                        default=cuid.cuid, editable=False, serialize=False,
                    ),
                ),
                migrations.AlterField(
                    model_name='retakerecorddetail',
                    name='retake_record',
                    field=models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name='retake_record_details',
                        null=True, blank=True,
                        to='activity.retakerecord',
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
