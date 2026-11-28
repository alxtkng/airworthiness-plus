#!/usr/bin/env bash
# Rehearse a populated schema upgrade and rollback in a newly created PostgreSQL cluster.
set -euo pipefail

if [[ $# -ne 3 ]]; then
    printf '%s\n' 'Usage: bash operations/rehearse-amos-cutover.sh PRIOR_WORKTREE PYTHON PG_BINDIR' >&2
    exit 2
fi

prior=$(cd "$1" && pwd)
python="$2"
pg="$3"
candidate=$(cd "$(dirname "$0")/.." && pwd)
trial=$(mktemp -d /tmp/amos-cutover.XXXXXX)
export PGHOST="$trial" PGUSER=postgres
export PGPORT=5432
export AIRWORTHINESS_DATABASE_HOST="$trial" AIRWORTHINESS_DATABASE_USER=postgres
export AIRWORTHINESS_DATABASE_PORT="$PGPORT" AIRWORTHINESS_DATABASE_NAME=trial_source
export AIRWORTHINESS_DATABASE_OWNER_WORK=true
export AIRWORTHINESS_SECRET_KEY
AIRWORTHINESS_SECRET_KEY=$("$python" -c 'import secrets; print(secrets.token_urlsafe(50))')

"$pg/initdb" --pgdata="$trial/cluster" --username=postgres --auth=trust > "$trial/init.log"
"$pg/pg_ctl" -D "$trial/cluster" -l "$trial/postgres.log" -o "-h '' -k $trial -p $PGPORT" -w start
trap '"$pg/pg_ctl" -D "$trial/cluster" -m fast -w stop' EXIT
printf 'Prior revision %s\nCandidate revision %s\n' "$(git -C "$prior" rev-parse HEAD)" "$(git -C "$candidate" rev-parse HEAD)"
"$pg/postgres" --version

manage() {
    local checkout=$1
    shift
    PYTHONPATH="$checkout/src" "$python" "$checkout/manage.py" "$@"
}

snapshot() {
    "$pg/psql" --dbname="$1" --tuples-only --no-align -v ON_ERROR_STOP=1 --command "
        SELECT 'history|' || count(*) || '|' || md5(string_agg(hash, '' ORDER BY organisation_id, record_type, record_id, sequence)) FROM history_event
        UNION ALL SELECT 'aircraft|' || count(*) FROM aircraft_aircraft
        UNION ALL SELECT 'open_defects|' || count(*) FROM defects_defect WHERE closed_on IS NULL
        UNION ALL SELECT 'pending_orders|' || count(*) FROM contracts_workorder WHERE closed_on IS NULL
        UNION ALL SELECT 'problem_entries|' || count(*) FROM acceptance_problem"
}

"$pg/createdb" trial_source
manage "$prior" migrate --noinput --verbosity 0
manage "$prior" shell -c 'import secrets; from airworthiness_plus.sample.management.commands.seed_sample_organisation import seed; seed(secrets.token_urlsafe(40))'
before=$(snapshot trial_source)
"$pg/pg_dump" --format=custom --file="$trial/pre-cutover.dump" trial_source
printf 'Readiness snapshot recorded\n%s\n' "$before"

manage "$candidate" migrate --noinput
manage "$candidate" makemigrations --check --dry-run
manage "$candidate" check_records
after=$(snapshot trial_source)
test "$before" = "$after"
printf '%s\n' 'Decision: synthetic cutover may proceed with matching records and history.'

"$pg/createdb" trial_recovered
time "$pg/pg_restore" --exit-on-error --dbname=trial_recovered "$trial/pre-cutover.dump"
restored=$(snapshot trial_recovered)
test "$before" = "$restored"
AIRWORTHINESS_DATABASE_NAME=trial_recovered manage "$prior" check_records
printf 'Fallback decision: return to the established schema and compare records before resuming.\n%s\n' "$restored"
printf 'Stabilisation review: migrated and restored copies remain available in the stopped rehearsal cluster at %s.\n' "$trial"
