"""Browser journeys for provider scope, calibration custody and evidence."""

from playwright.sync_api import Browser, expect

from tests.e2e.browser import save, signed_in
from tests.e2e.conftest import Account

HOME = "/tools/providers/"
SITE = "Calibration Browser Workshop"


def test_calibration_scope_order_and_certificate_workflows(
    chromium: Browser,
    live_site: str,
    personas: dict[str, tuple[Account, ...]],
) -> None:
    administrator, manager, _, _, reader = personas["your-organisation"]
    with signed_in(chromium, live_site, reader) as page:
        page.goto(HOME)
        page.get_by_role("link", name="2026-C07", exact=True).click()
        expect(page.locator("main")).to_contain_text("20 November 2026")
        expect(page.locator("main")).to_contain_text("28 November 2026")
        page.goto(HOME)
        page.get_by_role("link", name="2026-C06", exact=True).click()
        expect(page.locator("main")).to_contain_text("Certificate lacks traceability")
        expect(page.locator("main")).to_contain_text("Calibration hold")

    with signed_in(chromium, live_site, administrator) as page:
        for action in (
            "Register a Tool",
            "Approve a Control Basis",
            "Authorise a Tool Service Provider",
            "Place a Calibration Order",
            "Record Calibration Custody",
            "Record a Calibration Result",
            "Decide Certificate Acceptance",
            "Authorise Return to Use",
        ):
            page.goto("/tools/delegations/add/")
            save(
                page,
                "Record Tool Delegation",
                {
                    "approval": "Part-CAO",
                    "person": "[Browser Test Continuing Airworthiness Manager]",
                    "action": action,
                    "site": SITE,
                    "starts_on": "2026-11-18",
                    "ends_on": "2027-12-31",
                    "procedure": "Fictitious CAE C.3, revision 1",
                    "authority": f"Fictitious authority for {action}",
                },
                f"Fictitious authority for {action}",
            )

    with signed_in(chromium, live_site, manager) as page:
        page.goto(HOME)
        page.get_by_role("link", name="Record Provider Scope").click()
        save(
            page,
            "Record Provider Scope",
            {
                "approval": "Part-CAO",
                "supplier": "[Calibration Laboratory]",
                "site": SITE,
                "facility": "Browser Laboratory",
                "measurement": "Torque",
                "method": "Browser Torque Method Revision 1",
                "unit": "Nm",
                "range_from": "20",
                "range_to": "20",
                "valid_from": "2026-11-01",
                "valid_to": "2027-11-02",
                "evidence": "Fictitious browser scope evidence",
            },
            "Fictitious browser scope evidence",
        )
        page.goto("/tools/add/")
        save(
            page,
            "Register a Tool",
            {
                "approval": "Part-CAO",
                "asset_id": "E2E-CAL-1",
                "description": "Browser Torque Tool",
                "owner": "Organisation",
                "site": SITE,
                "location": "Tool Board",
                "serial": "E2E-0142",
            },
            "Browser Torque Tool",
        )
        tool = page.url
        page.get_by_role("link", name="Record Control Basis").click()
        save(
            page,
            "Record Control Basis",
            {
                "kind": "Calibration",
                "interval_months": "6",
                "instruction": "Browser instruction",
                "instruction_revision": "1",
                "method": "Browser Torque Method Revision 1",
                "limits": "Plus or minus 4 percent",
                "decision_basis": "Fictitious browser rule",
                "scope": "Browser Torque Tool, 20 Nm",
                "standard": "Fictitious approved standard",
            },
            "Browser instruction",
        )
        page.get_by_role("link", name="Place Calibration Order").click()
        save(
            page,
            "Place Calibration Order",
            {
                "provider": "[Calibration Laboratory] · Browser Laboratory · Calibration · "
                "Torque · Browser Torque Method Revision 1 · Nm",
                "reference": "BROWSER-2026-C05",
                "measurement": "Torque",
                "unit": "Nm",
                "range_from": "20",
                "range_to": "20",
                "points": "20",
                "configuration": "Clockwise",
                "error_limit": "4",
                "error_unit": "Percent",
                "limits_source": "Browser instruction",
                "uncertainty_required": "on",
            },
            "BROWSER-2026-C05",
        )
        order = page.url
        for kind, stamp, extra in (
            ("Despatched", "2026-11-12", {"expected_on": "2026-11-28"}),
            ("Returned", "2026-11-16", {}),
        ):
            page.get_by_role("link", name="Record Calibration Custody").click()
            save(
                page,
                "Record Calibration Custody",
                {
                    "kind": kind,
                    "occurred_on": stamp,
                    "evidence": f"Fictitious {kind} evidence",
                    **extra,
                },
                f"Fictitious {kind} evidence",
            )
        page.get_by_role("link", name="Record Certificate Version").click()
        save(
            page,
            "Record Calibration Certificate",
            {
                "number": "BROWSER-CERT-1",
                "revision": "1",
                "source": "Fictitious browser certificate",
                "calibrated_on": "2026-11-14",
                "received_on": "2026-11-16",
                "serial": "E2E-0142",
                "facility": "Browser Laboratory",
                "standard": "Fictitious approved standard",
                "method": "Browser Torque Method Revision 1",
                "configuration": "Clockwise",
                "traceability": "Fictitious chain to a standard",
                "rule": "Fictitious reported rule",
            },
            "BROWSER-CERT-1",
        )
        for phase, reading, error, statement in (
            ("As Found", "21.04", "5.2", "Nonconforming"),
            ("As Left", "20.1", "0.5", "Conforming"),
        ):
            page.get_by_role("link", name="Record Calibration Result").click()
            save(
                page,
                "Record Calibration Result",
                {
                    "phase": phase,
                    "reference_value": "20",
                    "measured_value": reading,
                    "error": error,
                    "uncertainty": "0.2",
                    "coverage": "k=2",
                    "convention": "Indication less reference",
                    "statement": statement,
                },
                statement,
            )
        page.get_by_role("link", name="Decide Certificate Acceptance").click()
        save(
            page,
            "Decide Certificate Acceptance",
            {
                "outcome": "Accepted",
                "reason": "Browser evidence review",
            },
            "Browser evidence review",
        )
        page.goto(tool)
        expect(page.locator("main")).to_contain_text("Calibration hold")
        page.goto(order)
        expect(page.locator("main")).to_contain_text("Open affected-work case")
        page.get_by_role("link", name="Authorise Return to Use").click()
        save(
            page,
            "Authorise Return to Use",
            {
                "evidence": "Fictitious browser return-to-use decision",
            },
            "Fictitious browser return-to-use decision",
        )
        expect(page.locator("main")).to_contain_text("Open affected-work case")
        page.goto(tool)
        expect(page.locator("main")).to_contain_text("14 May 2027")
