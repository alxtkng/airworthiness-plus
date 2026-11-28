"""Protect calibration records and atomically retain the first adverse finding."""

from django.db import migrations

from airworthiness_plus.history.sql import protect_record_table

GRANT = ("delegation_id", "tooling_tooldelegation")
ORDER = ("order_id", "tooling_calibrationorder")
CERTIFICATE = ("certificate_id", "tooling_calibrationcertificate")
TABLES = {
    "tooling_toolserviceproviderauthorisation": (GRANT, ("supplier_id", "logistics_supplier")),
    "tooling_calibrationorder": (
        GRANT,
        ("tool_id", "tooling_tool"),
        ("control_id", "tooling_toolcontrolrevision"),
        ("provider_id", "tooling_toolserviceproviderauthorisation"),
    ),
    "tooling_calibrationmovement": (GRANT, ORDER),
    "tooling_calibrationcertificate": (GRANT, ORDER),
    "tooling_calibrationresult": (GRANT, CERTIFICATE),
    "tooling_certificatedecision": (GRANT, CERTIFICATE),
    "tooling_calibrationreinstatement": (
        GRANT,
        ("decision_id", "tooling_certificatedecision"),
        ("control_id", "tooling_toolcontrolrevision"),
    ),
    "tooling_toolimpactcase": (ORDER, ("trigger_id", "tooling_calibrationresult")),
}

FORWARD = """
CREATE FUNCTION tooling_calibration_links() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE
    grant_record tooling_tooldelegation%ROWTYPE;
    order_grant tooling_tooldelegation%ROWTYPE;
    certificate tooling_calibrationcertificate%ROWTYPE;
    decision tooling_certificatedecision%ROWTYPE;
    episode tooling_calibrationorder%ROWTYPE;
    asset tooling_tool%ROWTYPE;
    required_action text;
    signer uuid;
BEGIN
    required_action := TG_ARGV[0];
    signer := NULLIF(current_setting('airworthiness.user', true), '')::uuid;
    SELECT * INTO STRICT grant_record FROM tooling_tooldelegation WHERE id = NEW.delegation_id;
    IF required_action <> grant_record.action
       OR NEW.signed_on NOT BETWEEN grant_record.starts_on AND grant_record.ends_on
       OR grant_record.approval_reference IS DISTINCT FROM
            organisations_approval_reference_on(grant_record.approval_id, NEW.signed_on)
       OR EXISTS (SELECT 1 FROM tooling_tooldelegationwithdrawal WHERE delegation_id=grant_record.id)
       OR NOT EXISTS (
            SELECT 1 FROM people_person WHERE id = grant_record.person_id AND user_id = signer
              AND (joined_on IS NULL OR joined_on <= NEW.signed_on)
              AND (left_on IS NULL OR left_on > NEW.signed_on)
       ) THEN
        RAISE EXCEPTION 'A current site and approval delegation is required' USING ERRCODE = '23514';
    END IF;

    IF TG_TABLE_NAME = 'tooling_toolserviceproviderauthorisation' THEN
        RETURN NEW;
    END IF;

    IF TG_TABLE_NAME = 'tooling_calibrationorder' THEN
        SELECT * INTO STRICT asset FROM tooling_tool WHERE id = NEW.tool_id;
        IF NEW.serial = '' OR NEW.serial <> asset.serial OR NEW.component_ids <> asset.component_ids
           OR lower(asset.site) <> lower(grant_record.site)
           OR NOT EXISTS (
               SELECT 1 FROM tooling_toolcontrolrevision control
               JOIN tooling_tooldelegation basis ON basis.id = control.delegation_id
               WHERE control.id = NEW.control_id AND control.tool_id = asset.id
                 AND control.kind = 'Calibration' AND control.effective_on <= NEW.signed_on
                 AND (basis.approval_id, basis.approval_reference) =
                     (grant_record.approval_id, grant_record.approval_reference)
           ) OR NOT EXISTS (
               SELECT 1 FROM tooling_toolserviceproviderauthorisation provider
               JOIN tooling_tooldelegation scope ON scope.id = provider.delegation_id
               WHERE provider.id = NEW.provider_id AND provider.status = 'Authorised' AND provider.service = 'Calibration'
                 AND (scope.approval_id, scope.approval_reference, lower(scope.site)) =
                     (grant_record.approval_id, grant_record.approval_reference, lower(grant_record.site))
                 AND lower(provider.measurement) = lower(NEW.measurement) AND provider.unit = NEW.unit
                 AND provider.range_from <= NEW.range_from AND provider.range_to >= NEW.range_to
                 AND NEW.signed_on BETWEEN provider.valid_from AND provider.valid_to
           ) THEN
            RAISE EXCEPTION 'Order requires matching tool, control and provider scope'
                USING ERRCODE = '23514';
        END IF;
        RETURN NEW;
    END IF;

    IF TG_TABLE_NAME IN ('tooling_calibrationcertificate', 'tooling_calibrationmovement') THEN
        SELECT * INTO STRICT episode FROM tooling_calibrationorder WHERE id = NEW.order_id;
    ELSE
        IF TG_TABLE_NAME = 'tooling_calibrationreinstatement' THEN
            SELECT * INTO STRICT decision FROM tooling_certificatedecision WHERE id = NEW.decision_id;
            SELECT * INTO STRICT certificate FROM tooling_calibrationcertificate
                WHERE id = decision.certificate_id;
        ELSE
            SELECT * INTO STRICT certificate FROM tooling_calibrationcertificate WHERE id = NEW.certificate_id;
        END IF;
        SELECT * INTO STRICT episode FROM tooling_calibrationorder WHERE id = certificate.order_id;
    END IF;

    SELECT * INTO STRICT order_grant FROM tooling_tooldelegation WHERE id = episode.delegation_id;
    IF (grant_record.approval_id, grant_record.approval_reference, lower(grant_record.site)) <>
       (order_grant.approval_id, order_grant.approval_reference, lower(order_grant.site)) THEN
        RAISE EXCEPTION 'Calibration evidence must use the order approval and site' USING ERRCODE = '23514';
    END IF;

    IF TG_TABLE_NAME = 'tooling_calibrationcertificate' THEN
        IF NOT EXISTS (
            SELECT 1 FROM tooling_calibrationmovement
            WHERE order_id = episode.id AND kind = 'Despatched' AND occurred_on <= NEW.calibrated_on
        ) THEN
            RAISE EXCEPTION 'Calibration must follow despatch' USING ERRCODE = '23514';
        END IF;
    ELSIF TG_TABLE_NAME = 'tooling_calibrationmovement' THEN
        IF NEW.kind = 'Returned' AND NOT EXISTS (
            SELECT 1 FROM tooling_calibrationmovement
            WHERE order_id = episode.id AND kind = 'Despatched' AND occurred_on <= NEW.occurred_on
        ) THEN
            RAISE EXCEPTION 'Physical return must follow despatch' USING ERRCODE = '23514';
        END IF;
    ELSIF TG_TABLE_NAME = 'tooling_calibrationresult' THEN
        IF EXISTS (SELECT 1 FROM tooling_certificatedecision WHERE certificate_id = certificate.id) THEN
            RAISE EXCEPTION 'Results are fixed after the first decision' USING ERRCODE = '23514';
        END IF;
    ELSIF TG_TABLE_NAME = 'tooling_certificatedecision' THEN
        IF NEW.outcome = 'Accepted' AND (
            certificate.serial <> episode.serial OR certificate.component_ids <> episode.component_ids
            OR btrim(certificate.traceability) = '' OR certificate.configuration <> episode.configuration
            OR NOT EXISTS (
                SELECT 1 FROM tooling_toolserviceproviderauthorisation provider
                JOIN tooling_toolcontrolrevision basis ON basis.id = episode.control_id
                WHERE provider.id = episode.provider_id AND certificate.method = provider.method
                  AND certificate.facility = provider.facility AND certificate.standard = basis.standard
                  AND certificate.calibrated_on BETWEEN provider.valid_from AND provider.valid_to
            )
        ) THEN
            RAISE EXCEPTION 'Acceptance requires serial-matched scope and traceability' USING ERRCODE = '23514';
        END IF;
    ELSIF TG_TABLE_NAME = 'tooling_calibrationreinstatement' THEN
        IF decision.outcome <> 'Accepted' OR NEW.occurred_on <> certificate.calibrated_on OR NOT EXISTS (
            SELECT 1 FROM tooling_calibrationmovement
            WHERE order_id = episode.id AND kind = 'Returned' AND occurred_on >= certificate.calibrated_on
        ) OR NOT EXISTS (
            SELECT 1 FROM tooling_toolcontrolrevision basis
            JOIN tooling_toolcontrolrevision ordered ON ordered.id = episode.control_id
            JOIN tooling_tooldelegation basis_grant ON basis_grant.id = basis.delegation_id
            WHERE basis.id = NEW.control_id AND basis.tool_id = episode.tool_id
              AND basis.kind = 'Calibration' AND basis.effective_on <= NEW.signed_on
              AND (basis_grant.approval_id, basis_grant.approval_reference) =
                  (grant_record.approval_id, grant_record.approval_reference)
              AND (basis.instruction, basis.instruction_revision, basis.standard, basis.method,
                   basis.limits, basis.scope, basis.loan_task, basis.loan_evidence, basis.loan_identity)
                = (ordered.instruction, ordered.instruction_revision, ordered.standard, ordered.method,
                   ordered.limits, ordered.scope, ordered.loan_task, ordered.loan_evidence, ordered.loan_identity)
              AND NEW.due_on = (certificate.calibrated_on + make_interval(months => basis.interval_months))::date
        ) THEN
            RAISE EXCEPTION 'Reinstatement requires a returned tool and accepted calibration'
                USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END
$$;

CREATE FUNCTION tooling_case_from_result() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE
    cert public.tooling_calibrationcertificate%ROWTYPE;
    episode public.tooling_calibrationorder%ROWTYPE;
BEGIN
    SELECT * INTO STRICT cert FROM public.tooling_calibrationcertificate WHERE id = NEW.certificate_id;
    SELECT * INTO STRICT episode FROM public.tooling_calibrationorder WHERE id = cert.order_id;
    IF NEW.statement = 'Nonconforming' OR abs(NEW.error) > episode.error_limit THEN
        INSERT INTO public.tooling_toolimpactcase (id, entered_at, organisation_id, order_id, trigger_id, opened_on, provisional)
        VALUES (
            gen_random_uuid(), NEW.entered_at, NEW.organisation_id, episode.id, NEW.id, NEW.signed_on,
            NEW.phase <> 'As found' OR btrim(cert.rule) = '' OR btrim(cert.traceability) = '' OR NEW.uncertainty IS NULL
            OR btrim(NEW.coverage) = '' OR btrim(NEW.convention) = '' OR NEW.measured_value IS NULL
            OR cert.serial <> episode.serial OR cert.component_ids <> episode.component_ids
            OR cert.configuration <> episode.configuration
            OR NEW.reference_value NOT BETWEEN episode.range_from AND episode.range_to
            OR NEW.statement <> 'Nonconforming'
            OR NOT EXISTS (
                SELECT 1 FROM public.tooling_toolserviceproviderauthorisation provider
                JOIN public.tooling_toolcontrolrevision basis ON basis.id = episode.control_id
                WHERE provider.id = episode.provider_id AND cert.method = provider.method
                  AND cert.facility = provider.facility AND cert.standard = basis.standard
                  AND cert.calibrated_on BETWEEN provider.valid_from AND provider.valid_to
            )
        ) ON CONFLICT (order_id) DO NOTHING;
    END IF;
    RETURN NULL;
END
$$;

REVOKE ALL ON FUNCTION tooling_case_from_result() FROM PUBLIC;
CREATE TRIGGER case_from_calibration_result AFTER INSERT ON tooling_calibrationresult
    FOR EACH ROW EXECUTE FUNCTION tooling_case_from_result();
"""

LINKS = {
    "tooling_toolserviceproviderauthorisation": "Provider",
    "tooling_calibrationorder": "Order",
    "tooling_calibrationmovement": "Receipt",
    "tooling_calibrationcertificate": "Result",
    "tooling_calibrationresult": "Result",
    "tooling_certificatedecision": "Certificate",
    "tooling_calibrationreinstatement": "Reinstate",
}


def table_rules(table: str) -> migrations.RunSQL:
    # Names and actions are fixed above.
    before = f"""CREATE TRIGGER history_refuse_update BEFORE UPDATE ON {table}
        FOR EACH ROW EXECUTE FUNCTION history_refuse();"""
    after = f"DROP TRIGGER history_refuse_update ON {table};"
    if table in LINKS:
        before += f"""CREATE TRIGGER calibration_link_rules BEFORE INSERT ON {table}
            FOR EACH ROW EXECUTE FUNCTION tooling_calibration_links('{LINKS[table]}');"""
        after += f"DROP TRIGGER calibration_link_rules ON {table};"
    return migrations.RunSQL(before, after)


class Migration(migrations.Migration):
    dependencies = [("tooling", "0003_calibration_records")]
    operations = [
        migrations.RunSQL(
            *protect_record_table(
                table,
                privileges=("SELECT",)
                if table == "tooling_toolimpactcase"
                else ("SELECT", "INSERT"),
                parents=parents,
            )
        )
        for table, parents in TABLES.items()
    ]
    operations += [
        migrations.RunSQL(
            FORWARD,
            """DROP TRIGGER case_from_calibration_result ON tooling_calibrationresult;
            DROP FUNCTION tooling_case_from_result();
            DROP FUNCTION tooling_calibration_links();""",
        ),
        *(table_rules(table) for table in TABLES),
    ]
