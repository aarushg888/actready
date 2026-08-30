"""enable RLS tenant isolation

Revision ID: b1a2c3d4e5f6
Revises: a00751e3c036
Create Date: 2026-08-29 14:18:00.000000

Applies Row-Level Security on every tenant-scoped table. A transaction-local
GUC ``app.tenant_id`` (set via ``SET LOCAL app.tenant_id = <org_id>``) scopes
reads/writes so a tenant can only ever see its own rows — defense-in-depth even
if application code forgets the WHERE clause.

Two roles (mirroring backend-plan §1.3):
  * ``app_owner`` — owns the schema / runs DDL (Alembic). Granted BYPASSRLS so
    migrations are never blocked by FORCE RLS.
  * ``app_user``  — the runtime role used by the API for DML. Bound by RLS.

The connecting role that runs this migration is also granted BYPASSRLS so local
dev and CI (default superuser ``actready``) work unchanged.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "b1a2c3d4e5f6"
down_revision: str | Sequence[str] | None = "a00751e3c036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_GUC = "app.tenant_id"

# Map table -> SQL boolean expression evaluated per row. Expressions may reference
# other tables (subqueries) when the tenant key is not a direct column.
TENANT_EXPR = {
    "organizations": "id = NULLIF(current_setting('app.tenant_id','t'),'')::uuid",
    "memberships": "org_id = NULLIF(current_setting('app.tenant_id','t'),'')::uuid",
    "integration_connections": "org_id = NULLIF(current_setting('app.tenant_id','t'),'')::uuid",
    "evidence_artifacts": "org_id = NULLIF(current_setting('app.tenant_id','t'),'')::uuid",
    "control_mappings": (
        "artifact_id IN (SELECT id FROM evidence_artifacts "
        "WHERE org_id = NULLIF(current_setting('app.tenant_id','t'),'')::uuid)"
    ),
    "ingestion_runs": "org_id = NULLIF(current_setting('app.tenant_id','t'),'')::uuid",
    "report_snapshots": "org_id = NULLIF(current_setting('app.tenant_id','t'),'')::uuid",
    "share_links": (
        "snapshot_id IN (SELECT id FROM report_snapshots "
        "WHERE org_id = NULLIF(current_setting('app.tenant_id','t'),'')::uuid)"
    ),
    "ml_proposals": "org_id = NULLIF(current_setting('app.tenant_id','t'),'')::uuid",
}


def upgrade() -> None:
    # Roles via DO-blocks (idempotent; CREATE ROLE ... IF NOT EXISTS is flaky on
    # some PG 16 builds, DO-blocks are universally safe).
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='app_owner') "
        "THEN CREATE ROLE app_owner LOGIN PASSWORD 'app_owner'; END IF; END $$"
    )
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='app_user') "
        "THEN CREATE ROLE app_user LOGIN PASSWORD 'app_user'; END IF; END $$"
    )
    op.execute("ALTER ROLE app_owner BYPASSRLS")
    op.execute("ALTER ROLE app_user NOBYPASSRLS")
    op.execute("ALTER ROLE actready BYPASSRLS")

    for table, expr in TENANT_EXPR.items():
        # ENABLE + FORCE: even the table owner is filtered by the policy.
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        # Read/delete scope.
        op.execute(
            f"CREATE POLICY {table}_tenant_isolation ON {table} "
            f"USING ({expr})"
        )
        # Write scope (insert/update must belong to the active tenant).
        op.execute(
            f"CREATE POLICY {table}_tenant_write ON {table} "
            f"WITH CHECK ({expr})"
        )

    # Runtime role needs DML privileges on every table/sequence.
    op.execute("GRANT USAGE ON SCHEMA public TO app_user")
    op.execute("GRANT ALL ON ALL TABLES IN SCHEMA public TO app_user")
    op.execute("GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO app_user")
    # app_owner also needs DML for operational backfills (it keeps BYPASSRLS).
    op.execute("GRANT ALL ON ALL TABLES IN SCHEMA public TO app_owner")


def downgrade() -> None:
    for table in TENANT_EXPR:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_write ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    for stmt in ("DROP ROLE IF EXISTS app_user", "DROP ROLE IF EXISTS app_owner"):
        try:
            op.execute(stmt)
        except Exception:
            pass
