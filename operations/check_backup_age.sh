#!/usr/bin/env bash
# Fail if the newest backup is older than it should be, or if there is none.
#
#   check_backup_age.sh <directory> <hours>
#
# Run on a schedule from somewhere that can raise an alert, and not only from
# the server whose backups it checks: a server that is down cannot say so
# (REQ-152, threat TH-042).
set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "usage: check_backup_age.sh <directory> <hours>" >&2
    exit 2
fi
directory="$1"
hours="$2"

newest="$(find "$directory" -maxdepth 1 -name 'airworthiness-*.dump.age' -printf '%T@ %f\n' | sort -n | tail -1)"
if [ -z "$newest" ]; then
    echo "No backup in ${directory}" >&2
    exit 1
fi
written="${newest%% *}"
name="${newest#* }"
age_hours="$(( ( $(date +%s) - ${written%.*} ) / 3600 ))"
if [ "$age_hours" -ge "$hours" ]; then
    echo "The newest backup, ${name}, is ${age_hours} hours old" >&2
    exit 1
fi
(cd "$directory" && sha256sum --check --quiet "${name}.sha256")
echo "The newest backup, ${name}, is ${age_hours} hours old and matches its checksum"
