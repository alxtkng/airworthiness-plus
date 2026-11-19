#!/usr/bin/env bash
# Restore one backup into a new, empty database.
#
#   restore.sh <backup file> <age identity file> <new database>
#
# The database must exist and be empty: this never writes over records. The
# roles the records refer to must exist already. Run as a role that may create
# objects owned by others, since the backup restores each table to its owner.
#
# After it finishes, run `python -m django check_records` against the new
# database, and `set_serial_floor` for each organisation, before the service is
# pointed at it (operations/backup-and-restore.md).
set -euo pipefail

if [ "$#" -ne 3 ]; then
    echo "usage: restore.sh <backup file> <age identity file> <new database>" >&2
    exit 2
fi
backup="$1"
identity="$2"
database="$3"

(cd "$(dirname "$backup")" && sha256sum --check --quiet "$(basename "$backup").sha256")

tables="$(psql --no-password --tuples-only --no-align --dbname "$database" \
    --command "SELECT count(*) FROM pg_class WHERE relkind = 'r' AND relnamespace = 'public'::regnamespace")"
if [ "$tables" != "0" ]; then
    echo "The database ${database} is not empty. Nothing was restored." >&2
    exit 1
fi

age --decrypt --identity "$identity" "$backup" \
    | pg_restore --exit-on-error --no-password --dbname "$database"
echo "Restored ${backup} into ${database}"
