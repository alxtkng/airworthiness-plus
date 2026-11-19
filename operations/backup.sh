#!/usr/bin/env bash
# Take one encrypted backup of the database.
#
#   backup.sh <database> <age recipient> <directory>
#
# The connection comes from the usual PostgreSQL environment values (PGHOST,
# PGPORT, PGUSER) and the password file; no password is given on the command
# line. Run as the backup role, which can read every record and write nothing.
#
# The backup is encrypted to the recipient before it touches the disk, so the
# server never holds a readable backup and cannot read its own backups back:
# the matching identity is kept off the server (threat TH-040).
#
# Prints the path of the backup. Fails, leaving nothing behind, if any step fails.
set -euo pipefail

if [ "$#" -ne 3 ]; then
    echo "usage: backup.sh <database> <age recipient> <directory>" >&2
    exit 2
fi
database="$1"
recipient="$2"
directory="$3"

umask 077
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
name="airworthiness-${stamp}.dump.age"
part="${directory}/.${name}.part"
trap 'rm -f "$part"' EXIT

pg_dump --format=custom --no-password "$database" | age --recipient "$recipient" --output "$part"

mv "$part" "${directory}/${name}"
(cd "$directory" && sha256sum "$name" > "${name}.sha256")
echo "${directory}/${name}"
