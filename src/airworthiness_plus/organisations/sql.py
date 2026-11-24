"""SQL for the approvals an organisation holds (REQ-200)."""

# Run once for each organisation by ``history.sql.for_each_organisation``: an
# organisation set up before approvals were records is given the record of the
# approval it was set up with. One that has it is left as it is.
APPROVAL_FOR_EACH_ORGANISATION = """
        INSERT INTO organisations_approval (id, organisation_id, approval, reference)
        SELECT gen_random_uuid(), one.id, one.approval_type, one.approval_reference
          FROM organisations_organisation one
         WHERE one.id = organisation
           AND NOT EXISTS (SELECT 1 FROM organisations_approval held
                            WHERE held.organisation_id = one.id
                              AND held.approval = one.approval_type);
"""
