#!/usr/bin/env bash
set -euo pipefail

APP_NAME="${APP_NAME:-gopanda-backend}"
RESOURCE_GROUP="${RESOURCE_GROUP:-Gopanda}"

echo "Running Alembic migrations on ${APP_NAME} in resource group ${RESOURCE_GROUP}..."

command -v az >/dev/null 2>&1 || {
  echo "Azure CLI is not installed or not on PATH." >&2
  exit 1
}

az account show >/dev/null 2>&1 || {
  echo "Azure CLI is not logged in. Run: az login" >&2
  exit 1
}

REMOTE_COMMAND='python - <<'"'"'PY'"'"'
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from app.db.database import engine

config = Config("alembic.ini")
script = ScriptDirectory.from_config(config)
heads = script.get_heads()
if len(heads) != 1:
    raise SystemExit(f"Expected exactly one Alembic head, found: {heads}")
head = heads[0]

with engine.connect() as connection:
    current = MigrationContext.configure(connection).get_current_revision()

print(f"Current revision before upgrade: {current}")
print(f"Expected head revision: {head}")
PY
alembic upgrade head
python - <<'"'"'PY'"'"'
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from app.db.database import engine

config = Config("alembic.ini")
script = ScriptDirectory.from_config(config)
head = script.get_heads()[0]

with engine.connect() as connection:
    current = MigrationContext.configure(connection).get_current_revision()

print(f"Current revision after upgrade: {current}")
if current != head:
    raise SystemExit(f"Migration verification failed: current={current}, head={head}")
print("Migration verified: database is at Alembic head.")
PY'

ENCODED_COMMAND="$(printf '%s' "${REMOTE_COMMAND}" | base64 | tr -d '\n')"

az containerapp exec \
  --name "${APP_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --command "/bin/sh -c \"printf '%s' '${ENCODED_COMMAND}' | base64 -d | /bin/sh\""

echo "Migration command completed and verified."
