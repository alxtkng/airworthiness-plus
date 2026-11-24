"""A person record for everyone in an organisation (REQ-203 to REQ-206).

Decisions.md, Canvas Build, decision 2. The people are those of
design-system/SampleData.md, People, and the Staff board. Today in the
sample world is 18 November 2026.
"""

import re
from datetime import date

import pytest
from django.db import IntegrityError, connection, transaction
from django.http import HttpResponse
from django.test import Client

from airworthiness_plus.accounts import users
from airworthiness_plus.accounts.models import AccessEntry, User
from airworthiness_plus.accounts.roles import Role
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.history.sql import for_each_organisation
from airworthiness_plus.organisations import approvals
from airworthiness_plus.organisations.models import ApprovalType
from airworthiness_plus.people import services
from airworthiness_plus.people.models import Employment, Person, StaffGroup
from airworthiness_plus.people.sql import PERSON_FOR_EACH_USER
from airworthiness_plus.sample import build
from tests.conftest import as_owner
from tests.support import TODAY, Sample, make_sample, signed_in

pytestmark = pytest.mark.django_db


@pytest.fixture
def sample() -> Sample:
    return make_sample()


@pytest.fixture(autouse=True)
def sample_day(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aircraft_services, "today", lambda: TODAY)


def get(client: Client, path: str) -> HttpResponse:
    return client.get(path, secure=True)  # type: ignore[return-value]


def post(client: Client, path: str, **values: str) -> HttpResponse:
    return client.post(path, values, secure=True)  # type: ignore[return-value]


def page(client: Client, path: str) -> str:
    response = get(client, path)
    assert response.status_code == 200, path
    return response.content.decode()


def person(sample: Sample, name: str) -> Person:
    with working_for(sample.ours.id, sample.reader.id):
        return Person.objects.select_related("reports_to", "user").get(full_name=name)


def rows(body: str, heading: str) -> list[list[str]]:
    """Return the cells of each row of the table whose first heading is ``heading``."""
    table = next(
        part
        for part in body.split("<table>")[1:]
        if part.lstrip().startswith(f"<thead>\n<tr><th>{heading}")
    )
    found = []
    for row in re.findall(r"<tr>\s*(<td>.*?)</tr>", table.split("</table>")[0], flags=re.S):
        cells = re.findall(r"<td>(.*?)</td>", row, flags=re.S)
        found.append([re.sub(r"<[^>]+>", "", cell).strip() for cell in cells])
    return found


# Everyone has a person record


def test_every_sign_in_of_the_sample_has_its_person(sample: Sample) -> None:
    """REQ-204. The person is made with the sign-in, in the same piece of work."""
    with working_for(sample.ours.id, sample.reader.id):
        linked = {
            one.user.username: one.full_name
            for one in Person.objects.select_related("user")
            if one.user is not None
        }
        assert linked == {
            "accountable.manager@your-organisation.example": "[Accountable Manager]",
            "lucy.grant@your-organisation.example": "Lucy Grant",
            "planning@your-organisation.example": "[Planning and Records Name]",
            "review@your-organisation.example": "[Review Name]",
            "reader@your-organisation.example": "[Read Only Name]",
        }
        assert User.objects.count() == 5
        lucy = Person.objects.get(user=sample.lucy)
        entries = list(Event.of(lucy))
    assert entries[0].action == "Created"
    # Lucy Grant's sign-in was added by the Administrator, and so was her person.
    assert entries[0].actor_name == "[Accountable Manager]"


def test_the_people_of_the_sample_are_those_of_the_staff_board(sample: Sample) -> None:
    """REQ-203. SampleData.md, People: 13 people, 5 of them with a sign-in, and 1 who left.

    The Read Only sign-in of the sample is a fourteenth person here.
    """
    with working_for(sample.ours.id, sample.reader.id):
        here = Person.objects.filter(left_on__isnull=True)
        assert here.count() == 14
        assert here.exclude(user=None).count() == 5
        by_group = {
            group: sorted(here.filter(staff_group=group).values_list("full_name", flat=True))
            for group in StaffGroup.values
        }
    assert by_group == {
        "Management": [
            "[Accountable Manager]",
            "[Compliance Monitoring Manager]",
            "[Continuing Airworthiness Manager]",
            "[Maintenance Manager]",
        ],
        "Certifying Staff": [
            "Chris Moore",
            "Sam Patel",
            "[Certifying Staff Name]",
            "[Contract Engineer]",
        ],
        "Airworthiness Review Staff": ["Lucy Grant", "[Review Name]"],
        "Other Staff": [
            "Ellie Ward",
            "[Independent Auditor]",
            "[Planning and Records Name]",
            "[Read Only Name]",
        ],
    }
    chris = person(sample, "Chris Moore")
    assert (chris.role, chris.licence, chris.employment, chris.user) == (
        "Certifying Staff",
        "Part-66 B1.2",
        "Employed",
        None,
    )
    assert chris.reports_to is not None
    assert chris.reports_to.full_name == "[Maintenance Manager]"
    assert person(sample, "[Certifying Staff Name]").employment == "Contracted"
    assert person(sample, "Ellie Ward").joined_on == date(2025, 1, 6)
    lucy = person(sample, "Lucy Grant")
    assert lucy.reports_to is not None
    assert lucy.reports_to.role == "Continuing Airworthiness Manager"
    assert person(sample, "[Accountable Manager]").reports_to is None


def test_the_database_refuses_a_sign_in_with_no_person(sample: Sample) -> None:
    """REQ-204. Whoever makes it, and however: checked when the work is finished.

    The check is made with no organisation set, as it is when work ends:
    row-level security must not hide the person from it.
    """
    insert = (
        "INSERT INTO accounts_user (id, organisation_id, username, full_name, password,"
        " is_active, roles, second_factor_secret, second_factor_confirmed,"
        " password_must_change, session_generation)"
        " VALUES (gen_random_uuid(), %s, 'nobody@your-organisation.example', '[Nobody]',"
        " '', true, '{}', '', false, false, 0)"
    )
    with connection.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")  # every sign-in so far has its person
        cursor.execute("SET CONSTRAINTS ALL DEFERRED")
        with (
            pytest.raises(IntegrityError, match="A sign-in belongs to a person"),
            transaction.atomic(),
        ):
            with working_for(sample.ours.id, sample.administrator.id):
                cursor.execute(insert, [sample.ours.id])
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        cursor.execute("SELECT current_setting('airworthiness.organisation', true)")
        assert cursor.fetchone() in (("",), (None,))
    with working_for(sample.ours.id, sample.reader.id):
        assert not User.objects.filter(username="nobody@your-organisation.example").exists()


def test_a_sign_in_is_linked_to_the_person_of_the_same_name(sample: Sample) -> None:
    """REQ-204. Chris Moore is recorded and has no sign-in. One added in his name is his."""
    before = person(sample, "Chris Moore")
    assert before.user is None
    with working_for(sample.ours.id, sample.administrator.id):
        chris = users.add_user(
            organisation=sample.ours,
            username="chris.moore@your-organisation.example",
            full_name="Chris Moore",
            roles=[Role.READ_ONLY],
            password=users.new_first_password(),
        )
        assert Person.objects.filter(full_name="Chris Moore").count() == 1
        linked = Person.objects.get(user=chris)
        assert linked.pk == before.pk
        assert (linked.role, linked.licence) == ("Certifying Staff", "Part-66 B1.2")
        # A name nobody is recorded under makes a person record.
        new = users.add_user(
            organisation=sample.ours,
            username="new.starter@your-organisation.example",
            full_name="[New Starter]",
            roles=[],
            password=users.new_first_password(),
        )
        made = Person.objects.get(user=new)
        assert (made.full_name, made.role, made.staff_group) == ("[New Starter]", "", "Other Staff")
        # A person who has left is not taken to be the person signing in.
        again = users.add_user(
            organisation=sample.ours,
            username="former@your-organisation.example",
            full_name="[Former Review Name]",
            roles=[],
            password=users.new_first_password(),
        )
        assert Person.objects.filter(full_name="[Former Review Name]").count() == 2
        assert Person.objects.get(user=again).left_on is None


# The Staff page


def test_the_staff_page_lists_everyone_and_those_who_have_left(sample: Sample) -> None:
    """REQ-205. Golden, from the Staff board. Reports To is the role reported to."""
    body = page(signed_in(sample.reader), "/staff/")
    current = rows(body, "Name")
    assert len(current) == 14
    assert "<p>14 People</p>" in body
    by_name = {row[0]: row[1:] for row in current}
    assert by_name["Chris Moore"] == [
        "Certifying Staff",
        "Maintenance Manager",
        "Employed",
        "Part-66 B1.2",
        "Certifying Staff",
        "",
        "None",
    ]
    assert by_name["Lucy Grant"] == [
        "Airworthiness Review Staff",
        "Continuing Airworthiness Manager",
        "Employed",
        "",
        "Airworthiness Review Staff",
        "",
        "lucy.grant@your-organisation.example",
    ]
    assert by_name["Ellie Ward"][:4] == [
        "Mechanic, Trainee",
        "Maintenance Manager",
        "Employed",
        "Working Toward Part-66 B1.2",
    ]
    assert by_name["Ellie Ward"][5] == "6 January 2025"
    assert by_name["[Independent Auditor]"][:3] == [
        "Auditor",
        "Compliance Monitoring Manager",
        "Contracted",
    ]
    assert by_name["[Accountable Manager]"][1] == ""
    former = rows(body, "Name</th><th>Role</th><th>Left")
    assert [row[:4] for row in former] == [
        [
            "[Former Review Name]",
            "Airworthiness Review Staff",
            "30 June 2025",
            "30 June 2027, 2 Years After Leaving",
        ]
    ]
    # How the day was worked out, with its source (REQ-139).
    assert "<dt>Left</dt><dd>30 June 2025</dd>" in body
    assert "<dt>Source</dt><dd>CAO.A.045(e)</dd>" in body
    assert "[Former Review Name]" not in {row[0] for row in current}


def test_the_record_of_a_former_person_is_kept_3_years_by_a_part_145(sample: Sample) -> None:
    """REQ-206. CAMO.A.220 and 145.A.55, Personnel Records: 30 June 2025 and 3 years."""
    with working_for(sample.ours.id, sample.administrator.id):
        approvals.record(sample.ours, approval=ApprovalType.PART_145, reference="UK.145.[Number]")
    body = page(signed_in(sample.reader), "/staff/")
    assert "<td>30 June 2028, 3 Years After Leaving</td>" in body
    assert "<dt>Source</dt><dd>145.A.55, Personnel Records</dd>" in body


def test_part_cao_gives_no_period_for_staff_who_are_not_review_staff(sample: Sample) -> None:
    """REQ-206. CAO.A.035(e) gives none; the page says so and shows no day of its own."""
    administrator = signed_in(sample.administrator)
    ellie = person(sample, "Ellie Ward")
    response = post(
        administrator,
        f"/staff/{ellie.id}/change/",
        full_name="Ellie Ward",
        role="Mechanic, Trainee",
        staff_group="Other Staff",
        employment="Employed",
        licence="Working Toward Part-66 B1.2",
        joined_on="2025-01-06",
        left_on="2026-11-18",
    )
    assert response.status_code == 302
    former = rows(page(administrator, "/staff/"), "Name</th><th>Role</th><th>Left")
    assert ["Ellie Ward", "Mechanic, Trainee", "18 November 2026"] in [row[:3] for row in former]
    assert next(row for row in former if row[0] == "Ellie Ward")[3] == "No Period Given in Part-CAO"


# Adding and changing


def test_the_administrator_adds_a_person_who_has_no_sign_in(sample: Sample) -> None:
    """REQ-203. Not everyone signs in. The record and who made it are in the history."""
    administrator = signed_in(sample.administrator)
    manager = person(sample, "[Maintenance Manager]")
    response = post(
        administrator,
        "/staff/add/",
        full_name="  [Stores Name]  ",
        role="Stores",
        staff_group="Other Staff",
        reports_to=str(manager.id),
        employment="Contracted",
        licence="",
        joined_on="2026-11-02",
    )
    assert response.status_code == 302
    added = person(sample, "[Stores Name]")
    assert response["Location"] == f"/staff/{added.id}/"
    assert (added.role, added.employment, added.joined_on, added.user) == (
        "Stores",
        "Contracted",
        date(2026, 11, 2),
        None,
    )
    assert added.reports_to == manager
    with working_for(sample.ours.id, sample.reader.id):
        entry = Event.of(added).get()
    assert (entry.action, entry.actor_name) == ("Created", "[Accountable Manager]")
    body = page(administrator, f"/staff/{added.id}/")
    assert "<h1>[Stores Name]</h1>\n<p>Stores</p>" in body
    assert "<dt>Sign-In</dt><dd>None</dd>" in body
    assert f'<a href="/staff/{added.id}/">[Stores Name]</a>' in page(
        administrator, f"/staff/{manager.id}/"
    )


@pytest.mark.parametrize("role", ["lucy", "planner", "reviewer", "reader"])
def test_only_the_administrator_adds_or_changes_a_person(sample: Sample, role: str) -> None:
    """REQ-006. Refused on the server, and the refusal is in the access log."""
    client = signed_in(getattr(sample, role))
    chris = person(sample, "Chris Moore")
    assert get(client, "/staff/").status_code == 200
    assert get(client, f"/staff/{chris.id}/").status_code == 200
    for path in ("/staff/add/", f"/staff/{chris.id}/change/"):
        assert post(client, path, full_name="[Someone Else]").status_code == 403, path
    assert get(client, "/staff/add/").status_code == 403
    assert person(sample, "Chris Moore").full_name == "Chris Moore"
    with as_owner():
        refused = AccessEntry.objects.filter(kind="Action Refused", detail="Add or Change Person")
        assert refused.count() == 3


def test_a_change_of_name_is_the_sign_ins_change_of_name(sample: Sample) -> None:
    """REQ-204. One person, one name: the history from then on names them as changed."""
    administrator = signed_in(sample.administrator)
    reviewer = person(sample, "[Review Name]")
    response = post(
        administrator,
        f"/staff/{reviewer.id}/change/",
        full_name="[Second Review Name]",
        role="Airworthiness Review Staff",
        staff_group="Airworthiness Review Staff",
        reports_to=str(reviewer.reports_to_id),
        employment="Employed",
    )
    assert response.status_code == 302
    with working_for(sample.ours.id, sample.reader.id):
        assert User.objects.get(pk=sample.reviewer.pk).full_name == "[Second Review Name]"
        changed = Person.objects.get(pk=reviewer.pk)
        assert Event.of(changed).last().changed == ["full_name"]  # type: ignore[union-attr]


def test_what_cannot_be_true_of_a_person_is_refused_with_the_reason(sample: Sample) -> None:
    """REQ-203. Reporting in a circle, leaving before joining, dates after today,
    and leaving while the sign-in is still active (REQ-010)."""
    administrator = signed_in(sample.administrator)
    accountable = person(sample, "[Accountable Manager]")
    maintenance = person(sample, "[Maintenance Manager]")
    chris = person(sample, "Chris Moore")
    lucy = person(sample, "Lucy Grant")

    def change(one: Person, **values: str) -> str:
        sent = {
            "full_name": one.full_name,
            "staff_group": one.staff_group,
            "employment": one.employment,
            **values,
        }
        response = post(administrator, f"/staff/{one.id}/change/", **sent)
        assert response.status_code == 200, values
        return response.content.decode()

    # The Accountable Manager cannot report to someone who reports to them, however far down.
    assert "A Chain of Reporting Does Not Come Back to Where It Began" in change(
        accountable, reports_to=str(chris.id)
    )
    # Nobody is offered themselves to report to.
    assert "Select a valid choice" in change(maintenance, reports_to=str(maintenance.id))
    assert "A Person Does Not Leave Before Joining" in change(
        chris, joined_on="2026-11-10", left_on="2026-11-09"
    )
    assert "Left Is Not After Today" in change(chris, left_on="2026-11-19")
    assert "Joined Is Not After Today" in change(chris, joined_on="2026-11-19")
    assert "A Person with an Active Sign-In Has Not Left" in change(lucy, left_on="2026-11-18")
    for name in ("[Accountable Manager]", "Chris Moore", "Lucy Grant"):
        unchanged = person(sample, name)
        assert (unchanged.left_on, unchanged.joined_on) == (None, None)
    assert person(sample, "[Accountable Manager]").reports_to is None
    # The database holds to the same rules whoever asks.
    with working_for(sample.ours.id, sample.administrator.id):
        for values, constraint in (
            ({"reports_to": chris}, "person_does_not_report_to_themselves"),
            (
                {"joined_on": date(2026, 11, 10), "left_on": date(2026, 11, 9)},
                "person_did_not_leave_before_joining",
            ),
            ({"staff_group": "Directors"}, "person_has_a_name_a_known_group_and_employment"),
            ({"full_name": ""}, "person_has_a_name_a_known_group_and_employment"),
        ):
            with pytest.raises(IntegrityError, match=constraint), transaction.atomic():
                Person.objects.filter(pk=chris.pk).update(**values)


def test_a_person_whose_sign_in_is_inactive_can_be_recorded_as_having_left(
    sample: Sample,
) -> None:
    """REQ-010, REQ-205. The sign-in is made inactive first; the person is then a former one."""
    with working_for(sample.ours.id, sample.administrator.id):
        users.set_active(sample.reviewer, active=False, by=sample.administrator)
        reviewer = Person.objects.get(user=sample.reviewer)
        services.change_person(
            reviewer,
            full_name=reviewer.full_name,
            role=reviewer.role,
            staff_group=StaffGroup(reviewer.staff_group),
            reports_to=reviewer.reports_to,
            employment=Employment(reviewer.employment),
            licence="",
            joined_on=None,
            left_on=date(2026, 11, 17),
        )
    former = rows(page(signed_in(sample.reader), "/staff/"), "Name</th><th>Role</th><th>Left")
    assert [
        "[Review Name]",
        "Airworthiness Review Staff",
        "17 November 2026",
        "17 November 2028, 2 Years After Leaving",
    ] in [row[:4] for row in former]


# Another organisation


def test_another_organisations_people_are_not_found_or_shown(sample: Sample) -> None:
    """REQ-003. Not on a page, not in a choice, and not to be reported to."""
    stranger = signed_in(sample.stranger)
    chris = person(sample, "Chris Moore")
    with working_for(sample.other.id, sample.stranger.id):
        theirs = Person.objects.get()
        assert theirs.full_name == "[Other Name]"
    assert get(stranger, f"/staff/{chris.id}/").status_code == 404
    assert post(stranger, f"/staff/{chris.id}/change/", full_name="X").status_code == 404
    body = page(stranger, "/staff/")
    assert "Chris Moore" not in body
    assert "<p>1 Person</p>" in body
    assert "Chris Moore" not in page(stranger, "/staff/add/")
    refused = post(
        stranger,
        "/staff/add/",
        full_name="[Their Person]",
        staff_group="Other Staff",
        employment="Employed",
        reports_to=str(chris.id),
    )
    assert refused.status_code == 200
    assert "Select a valid choice" in refused.content.decode()
    with (
        working_for(sample.other.id, sample.stranger.id),
        pytest.raises(Exception, match="refers only to records of its own organisation"),
        transaction.atomic(),
    ):
        Person.objects.filter(pk=theirs.pk).update(reports_to=chris.pk)
    assert get(signed_in(sample.reader), f"/staff/{theirs.id}/").status_code == 404


# A sample seeded before person records


def test_a_sign_in_from_before_person_records_is_given_its_person(sample: Sample) -> None:
    """REQ-204. The migration's own statement: it adds what is missing and no more."""
    earlier = "5f1e7d0a-0000-4000-8000-000000000002"
    with as_owner(), connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('airworthiness.organisation', %s, true)", [str(sample.ours.id)]
        )
        cursor.execute(
            "INSERT INTO accounts_user (id, organisation_id, username, full_name, password,"
            " is_active, roles, second_factor_secret, second_factor_confirmed,"
            " password_must_change, session_generation)"
            " VALUES (%s, %s, 'earlier@your-organisation.example', '[Earlier Name]',"
            " '', true, '{}', '', false, false, 0)",
            [earlier, sample.ours.id],
        )
        cursor.execute("SELECT set_config('airworthiness.organisation', '', true)")
        cursor.execute("SELECT count(*) FROM people_person")
        (before,) = cursor.fetchone()

        cursor.execute(for_each_organisation(PERSON_FOR_EACH_USER))

        cursor.execute("SELECT count(*) FROM people_person")
        assert cursor.fetchone() == (before + 1,)
        cursor.execute(
            "SELECT full_name, role, staff_group, employment, organisation_id::text "
            "FROM people_person WHERE user_id = %s",
            [earlier],
        )
        assert cursor.fetchall() == [
            ("[Earlier Name]", "", "Other Staff", "Employed", str(sample.ours.id))
        ]
        # And the sample's own people can be completed afterwards, changing nobody recorded.
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
    with working_for(sample.ours.id, sample.administrator.id):
        count = Person.objects.count()
        build.add_person_records(sample)
        assert Person.objects.count() == count
