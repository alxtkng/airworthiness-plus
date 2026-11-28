"""Browser coverage of the tooling write forms and saved labels."""

from playwright.sync_api import Browser, expect

from tests.e2e.browser import save, signed_in
from tests.e2e.conftest import Account


def test_tools_control_and_delegation_workflows(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    administrator, manager, *_ = personas["your-organisation"]
    with signed_in(chromium, live_site, administrator) as page:
        page.get_by_role("navigation", name="Sections").get_by_role(
            "link", name="Tools and Equipment", exact=True
        ).click()
        expect(page.get_by_role("heading", name="Tool and Equipment Register")).to_be_visible()
        page.get_by_role("link", name="Tool Delegations", exact=True).click()
        delegation = {
            "approval": "Part-CAO",
            "person": "[Browser Test Continuing Airworthiness Manager]",
            "site": "Browser Workshop",
            "starts_on": "2026-11-18",
            "ends_on": "2026-12-31",
            "procedure": "Sample CAE C.3 rev 1",
        }
        for action in (
            "Register a Tool",
            "Approve a Control Basis",
            "Accept Control Evidence",
            "Record Tool Condition",
            "Authorise Return to Use",
        ):
            text = f"Browser fixture authority for {action}"
            page.get_by_role("link", name="Record Tool Delegation", exact=True).click()
            save(
                page,
                "Record Tool Delegation",
                dict(delegation, action=action, authority=text),
                text,
            )
        page.get_by_role("link", name="Record Tool Delegation", exact=True).click()
        spare = dict(
            delegation, action="Register a Tool", site="Another Site", authority="Spare delegation"
        )
        save(page, "Record Tool Delegation", spare, "Spare delegation")
        row = page.get_by_role("row").filter(has_text="Spare delegation")
        row.get_by_role("link", name="Withdraw", exact=False).click()
        save(
            page,
            "Withdraw Tool Delegation",
            {"evidence": "Browser fixture withdrawal"},
            "Browser fixture withdrawal",
        )

    with signed_in(chromium, live_site, manager) as page:
        page.get_by_role("navigation", name="Sections").get_by_role(
            "link", name="Tools and Equipment", exact=True
        ).click()
        page.get_by_role("link", name="Register a Tool", exact=True).click()
        save(
            page,
            "Register a Tool",
            {
                "asset_id": "BROWSER-0201",
                "description": "Workshop Grease Gun",
                "owner": "Organisation",
                "site": "Browser Workshop",
                "location": "Tool Board 1",
            },
            "Control basis to verify",
        )
        common = {
            "instruction": "Fictitious workshop instruction",
            "instruction_revision": "Rev 1",
            "method": "Fictitious workshop procedure",
            "limits": "Fictitious acceptance basis",
            "decision_basis": "Browser fixture",
            "scope": "Asset BROWSER-0201",
        }
        for kind, months in (("Servicing", "6"), ("Calibration", "12"), ("Before each use", "")):
            page.get_by_role("link", name="Record Control Basis", exact=True).click()
            save(
                page,
                "Record Control Basis",
                dict(common, kind=kind, interval_months=months, standard="Sample standard"),
                "Fictitious workshop instruction",
            )
        for kind, day, result, control in (
            ("Servicing completed", "2026-08-03", "3 February 2027", "Servicing"),
            ("Calibration completed", "2026-09-14", "14 September 2027", "Calibration"),
            ("Pre-use inspection", "2026-11-18", "Before each use", "Before each use"),
            ("Unserviceable", "2026-11-18", "Unserviceable", ""),
            ("Repair completed", "2026-11-18", "Repair completed", ""),
            ("Return to use", "2026-11-18", "Return to use", ""),
            ("Withdrawn", "2026-11-18", "Withdrawn", ""),
        ):
            page.get_by_role("link", name="Record Tool Event", exact=True).click()
            fields = {"kind": kind, "occurred_on": day, "evidence": f"Browser fixture {kind}"}
            if control:
                fields["control"] = (
                    f"{control} · Part-CAO · Fictitious workshop instruction (Rev 1)"
                )
            save(page, "Record Tool Event", fields, result)
        page.get_by_role("navigation", name="Sections").get_by_role(
            "link", name="Tools and Equipment", exact=True
        ).click()
        page.reload()
        row = page.get_by_role("row").filter(has_text="Workshop Grease Gun")
        expect(row).to_contain_text("Withdrawn")
        expect(row).to_contain_text("3 February 2027")
