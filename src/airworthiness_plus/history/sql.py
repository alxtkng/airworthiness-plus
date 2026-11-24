"""The SQL that makes the record rules hold in PostgreSQL itself.

ADR-0001 and the threat model put two rules below the application, so
that a fault in application code cannot break them:

- every table carries its organisation and is scoped by row-level
  security to the organisation set on the database session; with none
  set, no rows (REQ-002, REQ-003, REQ-004, threat TH-020);
- every change to a record writes an entry to an append-only history,
  chained by hash to the entry before it, and nothing is deleted
  (REQ-130, REQ-131, threats TH-021, TH-022, TH-025).

The application connects as, or switches to, the role named here. It owns
nothing and is given only the privileges listed in these statements.
"""

APPLICATION_ROLE = "airworthiness_application"

ORGANISATION_SETTING = "airworthiness.organisation"
USER_SETTING = "airworthiness.user"

CREATE_APPLICATION_ROLE = f"""
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{APPLICATION_ROLE}') THEN
        CREATE ROLE {APPLICATION_ROLE} NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
    END IF;
END
$$;
"""

# The application's role can make nothing of its own: no table, no trigger,
# no function. In particular it cannot build a trigger of its own to write
# history entries that no change to a record produced (threat TH-026).
# PostgreSQL 15 and later give PUBLIC no right to create in the schema;
# temporary tables are withdrawn here.
WITHDRAW_TEMPORARY_TABLES = """
DO $$
BEGIN
    EXECUTE format('REVOKE TEMPORARY ON DATABASE %I FROM PUBLIC', current_database());
END
$$;
"""

RESTORE_TEMPORARY_TABLES = """
DO $$
BEGIN
    EXECUTE format('GRANT TEMPORARY ON DATABASE %I TO PUBLIC', current_database());
END
$$;
"""

CREATE_FUNCTIONS = f"""
CREATE FUNCTION airworthiness_organisation() RETURNS uuid
LANGUAGE sql STABLE AS $$
    SELECT NULLIF(current_setting('{ORGANISATION_SETTING}', true), '')::uuid
$$;

CREATE FUNCTION history_netstring(value text) RETURNS text
LANGUAGE sql IMMUTABLE AS $$
    SELECT octet_length(COALESCE(value, ''))::text || ':' || COALESCE(value, '') || ','
$$;

CREATE FUNCTION history_event_hash(event history_event) RETURNS text
LANGUAGE sql STABLE AS $$
    SELECT encode(sha256(convert_to(
           history_netstring(event.previous_hash)
        || history_netstring(event.organisation_id::text)
        || history_netstring(event.record_type)
        || history_netstring(event.record_id::text)
        || history_netstring(event.sequence::text)
        || history_netstring(event.action)
        || history_netstring(event.actor_id::text)
        || history_netstring(event.actor_name)
        || history_netstring(
               to_char(event.at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'))
        || history_netstring(array_to_string(event.changed, ','))
        || history_netstring(event.before_json)
        || history_netstring(event.after_json),
        'UTF8')), 'hex')
$$;

CREATE FUNCTION history_event_before_insert() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    previous history_event%ROWTYPE;
    acting uuid;
    acting_name text;
BEGIN
    -- History is written only by the trigger on a record, never directly.
    IF pg_trigger_depth() < 2 THEN
        RAISE EXCEPTION 'History is written only by a change to a record'
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    -- One writer at a time for each record, so the chain has no forks.
    PERFORM pg_advisory_xact_lock(hashtextextended(
        NEW.organisation_id::text || NEW.record_type || NEW.record_id::text, 0));

    SELECT * INTO previous
      FROM history_event
     WHERE organisation_id = NEW.organisation_id
       AND record_type = NEW.record_type
       AND record_id = NEW.record_id
     ORDER BY sequence DESC
     LIMIT 1;

    NEW.sequence := COALESCE(previous.sequence, 0) + 1;
    NEW.previous_hash := COALESCE(previous.hash, '');
    NEW.at := now();

    IF (SELECT rolsuper FROM pg_roles WHERE rolname = current_user)
       OR current_user = (SELECT tableowner FROM pg_tables
                           WHERE schemaname = current_schema()
                             AND tablename = 'history_event') THEN
        -- Provisioning and migrations, done by the owner of the tables.
        NEW.actor_id := NULL;
        NEW.actor_name := 'Database Role ' || session_user;
    ELSE
        acting := NULLIF(current_setting('{USER_SETTING}', true), '')::uuid;
        IF acting IS NULL THEN
            RAISE EXCEPTION 'No signed-in user is set for this change'
                USING ERRCODE = 'insufficient_privilege';
        END IF;
        SELECT full_name INTO acting_name
          FROM accounts_user
         WHERE id = acting
           AND is_active
           AND organisation_id = NEW.organisation_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'The signed-in user is not an active user of this organisation'
                USING ERRCODE = 'insufficient_privilege';
        END IF;
        NEW.actor_id := acting;
        NEW.actor_name := acting_name;
    END IF;

    NEW.hash := history_event_hash(NEW);
    RETURN NEW;
END
$$;

CREATE FUNCTION history_refuse() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Records and their history are never changed in place or deleted (% on %)',
        TG_OP, TG_TABLE_NAME
        USING ERRCODE = 'insufficient_privilege';
END
$$;

CREATE FUNCTION history_write_event() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    organisation_column text := TG_ARGV[0];
    omitted text[] := '{{}}';
    old_row jsonb;
    new_row jsonb := to_jsonb(NEW);
    changed_columns text[] := '{{}}';
BEGIN
    IF TG_NARGS > 1 THEN
        omitted := TG_ARGV[1]::text[];
    END IF;

    IF TG_OP = 'UPDATE' THEN
        old_row := to_jsonb(OLD);
        IF new_row -> 'id' IS DISTINCT FROM old_row -> 'id' THEN
            RAISE EXCEPTION 'The identifier of a record never changes'
                USING ERRCODE = 'insufficient_privilege';
        END IF;
        IF new_row -> organisation_column IS DISTINCT FROM old_row -> organisation_column THEN
            RAISE EXCEPTION 'A record never moves to another organisation'
                USING ERRCODE = 'insufficient_privilege';
        END IF;
        SELECT COALESCE(array_agg(entry.key ORDER BY entry.key), '{{}}')
          INTO changed_columns
          FROM jsonb_each(new_row) AS entry
         WHERE entry.value IS DISTINCT FROM old_row -> entry.key;
        IF cardinality(changed_columns) = 0 THEN
            RETURN NULL;
        END IF;
    END IF;

    INSERT INTO history_event
        (organisation_id, record_type, record_id, action, changed, before_json, after_json)
    VALUES (
        (new_row ->> organisation_column)::uuid,
        TG_TABLE_NAME,
        (new_row ->> 'id')::uuid,
        CASE TG_OP WHEN 'INSERT' THEN 'Created' ELSE 'Changed' END,
        changed_columns,
        (old_row - omitted)::text,
        (new_row - omitted)::text
    );
    RETURN NULL;
END
$$;
"""

DROP_FUNCTIONS = """
DROP FUNCTION history_write_event();
DROP FUNCTION history_refuse();
DROP FUNCTION history_event_before_insert();
DROP FUNCTION history_event_hash(history_event);
DROP FUNCTION history_netstring(text);
DROP FUNCTION airworthiness_organisation();
"""

PROTECT_HISTORY = f"""
ALTER TABLE history_event ENABLE ROW LEVEL SECURITY;
ALTER TABLE history_event FORCE ROW LEVEL SECURITY;
CREATE POLICY organisation_scope ON history_event
    USING (organisation_id = airworthiness_organisation())
    WITH CHECK (organisation_id = airworthiness_organisation());
REVOKE ALL ON history_event FROM PUBLIC;
GRANT SELECT, INSERT ON history_event TO {APPLICATION_ROLE};
CREATE TRIGGER history_chain BEFORE INSERT ON history_event
    FOR EACH ROW EXECUTE FUNCTION history_event_before_insert();
CREATE TRIGGER history_refuse_change BEFORE UPDATE OR DELETE ON history_event
    FOR EACH ROW EXECUTE FUNCTION history_refuse();
CREATE TRIGGER history_refuse_truncate BEFORE TRUNCATE ON history_event
    FOR EACH STATEMENT EXECUTE FUNCTION history_refuse();
"""

UNPROTECT_HISTORY = f"""
DROP TRIGGER history_refuse_truncate ON history_event;
DROP TRIGGER history_refuse_change ON history_event;
DROP TRIGGER history_chain ON history_event;
REVOKE ALL ON history_event FROM {APPLICATION_ROLE};
DROP POLICY organisation_scope ON history_event;
ALTER TABLE history_event NO FORCE ROW LEVEL SECURITY;
ALTER TABLE history_event DISABLE ROW LEVEL SECURITY;
"""


def _identifier(name: str) -> str:
    """Return ``name`` if it is a plain lower-case identifier, or refuse."""
    if not name or not all(character.islower() or character in "_0123456789" for character in name):
        raise ValueError(f"Not a plain identifier: {name!r}")
    return name


CREATE_SAME_ORGANISATION = """
CREATE FUNCTION history_same_organisation() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    parent_table text := TG_ARGV[0];
    parent_column text := TG_ARGV[1];
    parent_id uuid := (to_jsonb(NEW) ->> parent_column)::uuid;
    parent_organisation uuid;
BEGIN
    IF parent_id IS NULL THEN
        RETURN NEW;
    END IF;
    EXECUTE format('SELECT organisation_id FROM %I WHERE id = $1', parent_table)
       INTO parent_organisation
      USING parent_id;
    IF parent_organisation IS DISTINCT FROM (to_jsonb(NEW) ->> 'organisation_id')::uuid THEN
        RAISE EXCEPTION 'A record refers only to records of its own organisation'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    RETURN NEW;
END
$$;
"""

DROP_SAME_ORGANISATION = "DROP FUNCTION history_same_organisation();"


def protect_record_table(
    table: str,
    *,
    organisation_column: str = "organisation_id",
    privileges: tuple[str, ...] = ("SELECT", "INSERT", "UPDATE"),
    omitted: tuple[str, ...] = (),
    parents: tuple[tuple[str, str], ...] = (),
) -> tuple[str, str]:
    """Return the SQL that puts a record table under the rules, and its reverse.

    Every table of records is passed through here in a migration. A test
    fails the build if a table exists that has not been
    (``tests/test_data_layer.py``).

    ``privileges`` never includes DELETE or TRUNCATE. ``omitted`` names
    columns, such as a password, whose values are kept out of the history;
    that they changed is still recorded. ``parents`` lists each column that
    refers to another record, with the table it refers to: the database
    then refuses a row that refers to a record of another organisation
    (REQ-002, threat TH-020).
    """
    _identifier(table)
    _identifier(organisation_column)
    allowed = {"SELECT", "INSERT", "UPDATE"}
    if not privileges or not set(privileges) <= allowed:
        raise ValueError("A record table is given SELECT, INSERT or UPDATE only")
    omitted_literal = "{" + ",".join(_identifier(column) for column in omitted) + "}"
    forward = f"""
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
CREATE POLICY organisation_scope ON {table}
    USING ({organisation_column} = airworthiness_organisation())
    WITH CHECK ({organisation_column} = airworthiness_organisation());
REVOKE ALL ON {table} FROM PUBLIC;
GRANT {", ".join(privileges)} ON {table} TO {APPLICATION_ROLE};
CREATE TRIGGER history_write AFTER INSERT OR UPDATE ON {table}
    FOR EACH ROW EXECUTE FUNCTION history_write_event('{organisation_column}', '{omitted_literal}');
CREATE TRIGGER history_refuse_delete BEFORE DELETE ON {table}
    FOR EACH ROW EXECUTE FUNCTION history_refuse();
CREATE TRIGGER history_refuse_truncate BEFORE TRUNCATE ON {table}
    FOR EACH STATEMENT EXECUTE FUNCTION history_refuse();
"""
    reverse_parents = ""
    for column, parent in parents:
        _identifier(column)
        _identifier(parent)
        forward += f"""
CREATE TRIGGER same_organisation_{column} BEFORE INSERT OR UPDATE ON {table}
    FOR EACH ROW EXECUTE FUNCTION history_same_organisation('{parent}', '{column}');
"""
        reverse_parents += f"DROP TRIGGER same_organisation_{column} ON {table};\n"
    reverse = f"""
{reverse_parents}DROP TRIGGER history_refuse_truncate ON {table};
DROP TRIGGER history_refuse_delete ON {table};
DROP TRIGGER history_write ON {table};
REVOKE ALL ON {table} FROM {APPLICATION_ROLE};
DROP POLICY organisation_scope ON {table};
ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;
ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
"""
    return forward, reverse


def for_each_organisation(statements: str) -> str:
    """Return SQL that runs ``statements`` once for each organisation, in a migration.

    The owner of the tables is under row-level security like anyone else
    (ADR-0002): with no organisation set it sees no rows, so a migration
    that must give existing records something new cannot do it in one
    statement. This lifts the forcing from the organisation table alone,
    for the length of the list of organisations, inside the migration's own
    transaction and under the lock that changing a table takes; nothing
    else can read through it. Each organisation's rows are then read and
    written with that organisation set, as the application does, and the
    history records the work against the database role (REQ-004, REQ-130).

    ``statements`` is PL/pgSQL, fixed text written in a migration, and may
    use the variable ``organisation``. Deferred checks are run before the
    forcing goes back, so that a later step of the migration can change
    the tables.
    """
    return f"""
ALTER TABLE organisations_organisation NO FORCE ROW LEVEL SECURITY;
DO $$
DECLARE
    organisation uuid;
BEGIN
    FOR organisation IN SELECT id FROM organisations_organisation ORDER BY id LOOP
        PERFORM set_config('{ORGANISATION_SETTING}', organisation::text, true);
{statements}
    END LOOP;
    PERFORM set_config('{ORGANISATION_SETTING}', '', true);
END
$$;
SET CONSTRAINTS ALL IMMEDIATE;
SET CONSTRAINTS ALL DEFERRED;
ALTER TABLE organisations_organisation FORCE ROW LEVEL SECURITY;
"""


# Sign-in (REQ-008, REQ-009). While a user name is being checked, before any
# organisation is known, the application may read the one user with that
# name and the access log entries for that name, and nothing else.
SIGNING_IN_SETTING = "airworthiness.signing_in"

CREATE_SIGN_IN = f"""
CREATE FUNCTION airworthiness_signing_in() RETURNS text
LANGUAGE sql STABLE AS $$
    SELECT NULLIF(current_setting('{SIGNING_IN_SETTING}', true), '')
$$;

CREATE POLICY sign_in_lookup ON accounts_user FOR SELECT
    USING (username = airworthiness_signing_in());

-- The secret shared with the authenticator application stays out of the history.
DROP TRIGGER history_write ON accounts_user;
CREATE TRIGGER history_write AFTER INSERT OR UPDATE ON accounts_user
    FOR EACH ROW EXECUTE FUNCTION
    history_write_event('organisation_id', '{{password,second_factor_secret}}');

CREATE FUNCTION accounts_accessentry_before_insert() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.at := now();
    RETURN NEW;
END
$$;

ALTER TABLE accounts_accessentry ENABLE ROW LEVEL SECURITY;
ALTER TABLE accounts_accessentry FORCE ROW LEVEL SECURITY;
CREATE POLICY organisation_scope ON accounts_accessentry FOR SELECT
    USING (organisation_id = airworthiness_organisation());
CREATE POLICY sign_in_lookup ON accounts_accessentry FOR SELECT
    USING (username = airworthiness_signing_in());
CREATE POLICY entries_added ON accounts_accessentry FOR INSERT
    WITH CHECK (organisation_id = airworthiness_organisation()
                OR username = airworthiness_signing_in());
REVOKE ALL ON accounts_accessentry FROM PUBLIC;
GRANT SELECT, INSERT ON accounts_accessentry TO {APPLICATION_ROLE};
CREATE TRIGGER access_time BEFORE INSERT ON accounts_accessentry
    FOR EACH ROW EXECUTE FUNCTION accounts_accessentry_before_insert();
CREATE TRIGGER history_refuse_change BEFORE UPDATE OR DELETE ON accounts_accessentry
    FOR EACH ROW EXECUTE FUNCTION history_refuse();
CREATE TRIGGER history_refuse_truncate BEFORE TRUNCATE ON accounts_accessentry
    FOR EACH STATEMENT EXECUTE FUNCTION history_refuse();

-- Sessions are not records: they are made, renewed and removed as users
-- sign in and out.
GRANT SELECT, INSERT, UPDATE, DELETE ON django_session TO {APPLICATION_ROLE};
"""

DROP_SIGN_IN = f"""
REVOKE ALL ON django_session FROM {APPLICATION_ROLE};
DROP TRIGGER history_refuse_truncate ON accounts_accessentry;
DROP TRIGGER history_refuse_change ON accounts_accessentry;
DROP TRIGGER access_time ON accounts_accessentry;
REVOKE ALL ON accounts_accessentry FROM {APPLICATION_ROLE};
DROP POLICY entries_added ON accounts_accessentry;
DROP POLICY sign_in_lookup ON accounts_accessentry;
DROP POLICY organisation_scope ON accounts_accessentry;
ALTER TABLE accounts_accessentry NO FORCE ROW LEVEL SECURITY;
ALTER TABLE accounts_accessentry DISABLE ROW LEVEL SECURITY;
DROP FUNCTION accounts_accessentry_before_insert();
DROP TRIGGER history_write ON accounts_user;
CREATE TRIGGER history_write AFTER INSERT OR UPDATE ON accounts_user
    FOR EACH ROW EXECUTE FUNCTION history_write_event('organisation_id', '{{password}}');
DROP POLICY sign_in_lookup ON accounts_user;
DROP FUNCTION airworthiness_signing_in();
"""
