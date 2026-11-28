"""Process entry points for the disposable browser database and loopback server."""

import json
import sys
from datetime import UTC, date, datetime
from decimal import Decimal
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from uuid import UUID
from wsgiref.simple_server import WSGIRequestHandler, make_server

import django
from django.core.management import call_command
from django.db import connection
from django.test import override_settings

LEGACY_WORK = "Test inspection with a previously recorded release reference"
LEGACY_REFERENCE = "TEST-RELEASE-10"


def seed() -> None:
    from airworthiness_plus.accounts import users
    from airworthiness_plus.accounts.models import User
    from airworthiness_plus.aircraft.models import Aircraft
    from airworthiness_plus.history.session import working_for
    from airworthiness_plus.organisations.models import Organisation
    from airworthiness_plus.programme.services import record_work

    accounts = json.load(sys.stdin)
    call_command("migrate", verbosity=0, interactive=False)
    for command, people in zip(
        ("seed_sample_organisation", "seed_second_sample_organisation"), accounts, strict=True
    ):
        administrator = people[0]
        output = StringIO()
        with patch("getpass.getpass", return_value=administrator["password"]):
            call_command(command, stdout=output)
        organisation_id = UUID(output.getvalue().splitlines()[0].split()[1])
        with working_for(organisation_id):
            organisation = Organisation.objects.get(id=organisation_id)
            actor = User.objects.get(username=administrator["username"])
        with working_for(organisation_id, actor.id):
            for person in people[1:]:
                user = User.objects.filter(username=person["username"]).first()
                if user is None:
                    users.add_user(
                        organisation=organisation,
                        username=person["username"],
                        full_name=f"[Browser Test {person['role']}]",
                        roles=[person["role"]],
                        password=person["password"],
                    )
                else:
                    users.reset_password(user, password=person["password"], by=actor)
            if command == "seed_sample_organisation":
                # The current work form cannot create a legacy reference-only entry.
                record_work(
                    Aircraft.objects.get(registration="G-ABCD"),
                    description=LEGACY_WORK,
                    dated=date(2026, 11, 10),
                    hours=Decimal("6400.0"),
                    cycles=0,
                    release_reference=LEGACY_REFERENCE,
                    release_recorded_on=date(2026, 11, 11),
                )
                # Represent an issued package from before tooling approval was pinned.
                seed_legacy_issued_package()
    connection.close()


class QuietHandler(WSGIRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        """Avoid logging URLs from account and record pages."""


def seed_legacy_issued_package() -> None:
    from airworthiness_plus.aircraft.models import Aircraft
    from airworthiness_plus.contracts.models import WorkOrder
    from airworthiness_plus.maintenance_data import services as data
    from airworthiness_plus.maintenance_data.models import Kind
    from airworthiness_plus.planning import services as planning

    day = date(2026, 11, 18)
    aircraft = Aircraft.objects.get(registration="G-ABCD")
    order = WorkOrder.objects.get(aircraft=aircraft, work="Landing Light Replacement")
    package = planning.build_package(
        aircraft,
        reference="WP-LEGACY-CUSTODY",
        title="Fictitious earlier issued job",
        location="Bay 2",
        starts_on=day,
        ends_on=day,
    )
    planning.link_order(package, order)
    manual = data.record_data(
        organisation=aircraft.organisation,
        title="Fictitious earlier job instruction",
        author="Fictitious designer",
        kind=Kind.INSTRUCTIONS,
        revision="1",
        revision_date=day,
        check_due=day,
    )
    card = planning.add_card(
        package,
        title="Fictitious earlier work card",
        data_set=manual,
        instruction="Test task evidence",
        planned_hours=Decimal("1.0"),
    )
    card.revision = data.current_revision(manual)
    card.issue_check_due = day
    card.save(update_fields=["revision", "issue_check_due"])
    package.issued_on = day
    package.save(update_fields=["issued_on"])


def serve(address_file: Path) -> None:
    from django.core.wsgi import get_wsgi_application

    with (
        # Local HTTP has no TLS terminator. Keep Django's production error pages.
        override_settings(
            SECURE_SSL_REDIRECT=False,
            SESSION_COOKIE_SECURE=False,
            CSRF_COOKIE_SECURE=False,
            SESSION_COOKIE_NAME="sessionid",
            CSRF_COOKIE_NAME="csrftoken",
        ),
        patch("airworthiness_plus.aircraft.services.today", return_value=date(2026, 11, 18)),
        patch(
            "airworthiness_plus.organisations.approvals.utc_now",
            return_value=datetime(2026, 11, 18, 12, tzinfo=UTC),
        ),
    ):
        application = get_wsgi_application()
        with make_server("127.0.0.1", 0, application, handler_class=QuietHandler) as server:
            response = address_file.with_suffix(".ready")
            response.write_text(f"http://127.0.0.1:{server.server_port}")
            response.replace(address_file)
            server.serve_forever()


if __name__ == "__main__":
    django.setup()
    if sys.argv[1] == "seed":
        seed()
    else:
        serve(Path(sys.argv[1]))
