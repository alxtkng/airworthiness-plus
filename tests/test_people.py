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
from airworthiness_plus.accounts.roles import Action, Role
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.history.sql import for_each_organisation
from airworthiness_plus.organisations import approvals
from airworthiness_plus.organisations.models import Approval, ApprovalType
from airworthiness_plus.people import services
from airworthiness_plus.people.models import Employment, Person, StaffGroup
from airworthiness_plus.people.sql import PERSON_FOR_EACH_USER
from airworthiness_plus.reviews import services as review_services
from airworthiness_plus.reviews.models import ReviewStaff
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


def test_a_new_sign_in_is_never_joined_to_a_person_by_name(sample: Sample) -> None:
    """REQ-204; independent review of 24 November 2026, finding 4. Chris Moore is
    recorded and has no sign-in. A sign-in added in the same name is another
    person's: it is given a record of its own, and nothing of Chris Moore's."""
    before = person(sample, "Chris Moore")
    assert before.user is None
    with working_for(sample.ours.id, sample.administrator.id):
        namesake = users.add_user(
            organisation=sample.ours,
            username="chris.moore@your-organisation.example",
            full_name="Chris Moore",
            roles=[Role.READ_ONLY],
            password=users.new_first_password(),
        )
        assert Person.objects.filter(full_name="Chris Moore").count() == 2
        made = Person.objects.get(user=namesake)
        assert made.pk != before.pk
        assert (made.role, made.licence, made.staff_group) == ("", "", "Other Staff")
        assert made.reports_to is None
        unchanged = Person.objects.get(pk=before.pk)
        assert unchanged.user is None
        assert (unchanged.role, unchanged.licence) == ("Certifying Staff", "Part-66 B1.2")
        assert Event.of(unchanged).count() == 1


def test_a_sign_in_is_given_to_a_person_already_recorded_only_when_chosen(sample: Sample) -> None:
    """REQ-204, finding 4. On Add a User the Administrator chooses Sam Patel, who is
    recorded and has no sign-in. The sign-in is Sam Patel's and takes that name."""
    administrator = signed_in(sample.administrator)
    sam, chris = person(sample, "Sam Patel"), person(sample, "Chris Moore")
    former = person(sample, "[Former Review Name]")
    lucy = person(sample, "Lucy Grant")
    body = page(administrator, "/users/")
    assert f'<option value="{sam.id}">Sam Patel</option>' in body
    assert '<option value="" selected>A New Person</option>' in body
    # Nobody who has a sign-in, and nobody who has left, is offered.
    assert f'value="{lucy.id}"' not in body and f'value="{former.id}"' not in body
    added = post(
        administrator,
        "/users/add/",
        person=str(sam.id),
        full_name="[Any Other Name]",
        username="sam.patel@your-organisation.example",
        roles="Read Only",
    )
    assert "First Password for Sam Patel, Shown Once" in added.content.decode()
    with working_for(sample.ours.id, sample.reader.id):
        user = User.objects.get(username="sam.patel@your-organisation.example")
        assert user.full_name == "Sam Patel"
        linked = Person.objects.get(user=user)
        assert linked.pk == sam.pk
        assert (linked.role, linked.licence) == ("Certifying Staff", "Part-66 B1.2")
        assert Person.objects.filter(full_name="Sam Patel").count() == 1
        assert Person.objects.count() == 15
    # Chosen once: a person with a sign-in is not offered or taken again.
    for chosen in (sam, lucy, former):
        refused = post(
            administrator,
            "/users/add/",
            person=str(chosen.id),
            username="second@your-organisation.example",
        )
        assert "Shown Once" not in refused.content.decode()
    with working_for(sample.ours.id, sample.administrator.id):
        assert not User.objects.filter(username="second@your-organisation.example").exists()
        # Below the page, the same: the reason is given.
        for chosen, reason in (
            (sam, "The Person Chosen Already Has a Sign-In"),
            (former, "A Person Recorded as Having Left Is Not Given a Sign-In"),
        ):
            with pytest.raises(users.RefusedError, match=reason):
                users.add_user(
                    organisation=sample.ours,
                    username="second@your-organisation.example",
                    full_name="",
                    roles=[],
                    password=users.new_first_password(),
                    person=chosen,
                )
        assert Person.objects.get(pk=chris.pk).user is None
    # A person of another organisation cannot be chosen.
    with working_for(sample.other.id, sample.stranger.id):
        with pytest.raises(users.RefusedError, match="Person of the Same Organisation"):
            users.add_user(
                organisation=sample.other,
                username="second@other-organisation.example",
                full_name="",
                roles=[],
                password=users.new_first_password(),
                person=chris,
            )
    # With neither a name nor a person, nobody is added.
    neither = post(administrator, "/users/add/", username="third@your-organisation.example")
    assert "Give a Full Name" in neither.content.decode()


# The Staff page


def test_the_staff_page_lists_everyone_and_those_who_have_left(sample: Sample) -> None:
    """REQ-205. Golden, from the Staff board. Reports To is the role reported to."""
    body = page(signed_in(sample.administrator), "/staff/")
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


@pytest.mark.parametrize("role", ["lucy", "planner", "reviewer", "reader"])
def test_a_user_name_is_shown_only_to_a_role_that_manages_users(sample: Sample, role: str) -> None:
    """REQ-006, REQ-205; independent review of 24 November 2026, finding 8. A user name
    is half of a sign-in, and five wrong passwords lock it for 15 minutes. Every
    role reads the Staff pages; only the Administrator is shown user names."""
    client = signed_in(getattr(sample, role))
    lucy, chris = person(sample, "Lucy Grant"), person(sample, "Chris Moore")
    for path in ("/staff/", f"/staff/{lucy.id}/", f"/staff/{chris.id}/"):
        body = page(client, path)
        assert "your-organisation.example" not in body, path
    by_name = {row[0]: row[1:] for row in rows(page(client, "/staff/"), "Name")}
    assert by_name["Lucy Grant"][-1] == "Has a Sign-In"
    assert by_name["Chris Moore"][-1] == "None"
    assert "<dt>Sign-In</dt><dd>Has a Sign-In</dd>" in page(client, f"/staff/{lucy.id}/")
    # The Administrator is shown them, here as on the Users page.
    administrator = signed_in(sample.administrator)
    assert "<dt>Sign-In</dt><dd>lucy.grant@your-organisation.example</dd>" in page(
        administrator, f"/staff/{lucy.id}/"
    )
    with working_for(sample.ours.id, sample.administrator.id):
        users.set_active(sample.planner, active=False, by=sample.administrator)
    if role != "planner":
        by_name = {row[0]: row[1:] for row in rows(page(client, "/staff/"), "Name")}
        assert by_name["[Planning and Records Name]"][-1] == "Has a Sign-In, Inactive"


@pytest.mark.parametrize("role", ["administrator", "lucy", "planner", "reviewer", "reader"])
def test_the_staff_pages_offer_only_what_the_role_may_do(sample: Sample, role: str) -> None:
    """REQ-006, finding 8. Add a Person and the form that changes a record are shown to
    the Administrator, who may use them, and to nobody the server would refuse."""
    user = getattr(sample, role)
    client = signed_in(user)
    chris = person(sample, "Chris Moore")
    main = [page(client, path).split("<main", 1)[1] for path in ("/staff/", f"/staff/{chris.id}/")]
    may = user.may(Action.ADD_OR_CHANGE_PERSON)
    assert may == (role == "administrator")
    assert ('href="/staff/add/"' in main[0]) == may
    assert ("<form" in main[1]) == may
    assert (f'action="/staff/{chris.id}/change/"' in main[1]) == may
    # What is recorded is read by every role.
    assert "<dt>Licence</dt><dd>Part-66 B1.2</dd>" in main[1]


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
    and recording oneself as having left (REQ-010)."""
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
    # Nobody records themselves as having left: it would make their own sign-in inactive.
    assert "A User Does Not Make Themselves Inactive" in change(accountable, left_on="2026-11-18")
    del lucy
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


def test_recording_that_a_person_left_makes_their_sign_in_inactive_at_once(
    sample: Sample,
) -> None:
    """REQ-010, REQ-205; independent review of 24 November 2026, findings 5 and 6.
    Lucy Grant is recorded as having left on 17 November 2026. Her sign-in is
    inactive from that moment, her sessions end, and her review staff record
    carries the day. She cannot be made active while she is recorded as left."""
    with working_for(sample.ours.id, sample.administrator.id):
        staff = review_services.add_review_staff(
            user=sample.lucy,
            authorisation_reference="[Authorisation Reference 1]",
            accepted_on=date(2023, 6, 9),
        )
    hers = signed_in(sample.lucy)
    assert get(hers, "/staff/").status_code == 200
    administrator = signed_in(sample.administrator)
    lucy = person(sample, "Lucy Grant")
    generation = sample.lucy.session_generation
    left = post(
        administrator,
        f"/staff/{lucy.id}/change/",
        full_name="Lucy Grant",
        role="Airworthiness Review Staff",
        staff_group="Airworthiness Review Staff",
        employment="Employed",
        left_on="2026-11-17",
    )
    assert left.status_code == 302
    with working_for(sample.ours.id, sample.reader.id):
        user = User.objects.get(pk=sample.lucy.pk)
        assert (user.is_active, user.session_generation) == (False, generation + 1)
        assert ReviewStaff.objects.get(pk=staff.pk).left_on == date(2026, 11, 17)
    # Her session has ended.
    ended = get(hers, "/staff/")
    assert (ended.status_code, ended["Location"][:9]) == (302, "/sign-in/")
    # She is not made active while recorded as having left: on the page, and below it.
    refused = post(administrator, f"/users/{sample.lucy.id}/active/", active="yes")
    assert "A Person Recorded as Having Left Is Not Made Active" in refused.content.decode()
    with working_for(sample.ours.id, sample.administrator.id):
        with pytest.raises(users.RefusedError, match="Recorded as Having Left"):
            users.set_active(
                User.objects.get(pk=sample.lucy.pk), active=True, by=sample.administrator
            )
        assert not User.objects.get(pk=sample.lucy.pk).is_active
    # The day taken off her record, she can be made active again.
    back = post(
        administrator,
        f"/staff/{lucy.id}/change/",
        full_name="Lucy Grant",
        role="Airworthiness Review Staff",
        staff_group="Airworthiness Review Staff",
        employment="Employed",
    )
    assert back.status_code == 302
    assert post(administrator, f"/users/{sample.lucy.id}/active/", active="yes").status_code == 302
    with working_for(sample.ours.id, sample.reader.id):
        assert User.objects.get(pk=sample.lucy.pk).is_active
        # The day on the review staff record is a record of its own and stays.
        assert ReviewStaff.objects.get(pk=staff.pk).left_on == date(2026, 11, 17)


def test_the_last_administrator_is_not_recorded_as_having_left(sample: Sample) -> None:
    """REQ-005, REQ-205. It would leave the organisation with nobody to manage its users."""
    with working_for(sample.ours.id, sample.administrator.id):
        second = users.add_user(
            organisation=sample.ours,
            username="second.administrator@your-organisation.example",
            full_name="[Second Administrator]",
            roles=[Role.ADMINISTRATOR],
            password=users.new_first_password(),
        )
        users.set_roles(User.objects.get(pk=sample.administrator.pk), [Role.READ_ONLY])
        only = Person.objects.get(user=second)
        with pytest.raises(services.RefusedError, match="Always Has an Active Administrator"):
            services.change_person(
                only,
                full_name=only.full_name,
                role="",
                staff_group=StaffGroup.OTHER,
                reports_to=None,
                employment=Employment.EMPLOYED,
                licence="",
                joined_on=None,
                left_on=TODAY,
                by=User.objects.get(pk=sample.administrator.pk),
            )
        assert Person.objects.get(pk=only.pk).left_on is None
        assert User.objects.get(pk=second.pk).is_active


def former_row(sample: Sample, name: str) -> list[str]:
    body = page(signed_in(sample.reader), "/staff/")
    former = rows(body, "Name</th><th>Role</th><th>Left")
    return next(row for row in former if row[0] == name)


def leave(sample: Sample, name: str, on: date, group: StaffGroup | None = None) -> Person:
    """Record, as the Administrator, that a person left, in the group given or their own."""
    with working_for(sample.ours.id, sample.administrator.id):
        one = Person.objects.get(full_name=name)
        services.change_person(
            one,
            full_name=one.full_name,
            role=one.role,
            staff_group=group or StaffGroup(one.staff_group),
            reports_to=None,
            employment=Employment(one.employment),
            licence=one.licence,
            joined_on=one.joined_on,
            left_on=on,
            by=sample.administrator,
        )
        return one


def test_record_kept_until_uses_the_approvals_held_on_the_day_the_person_left(
    sample: Sample,
) -> None:
    """REQ-206, finding 6. [Former Review Name] left on 30 June 2025. With Part-145
    held then, the record is kept 3 years, to 30 June 2028 (145.A.55, Personnel
    Records). Giving Part-145 up afterwards does not shorten it. Had Part-145
    ended on or before the day the person left, it would give nothing."""
    with working_for(sample.ours.id, sample.administrator.id):
        held = approvals.record(
            sample.ours, approval=ApprovalType.PART_145, reference="UK.145.[Number]"
        )
    assert former_row(sample, "[Former Review Name]")[3] == "30 June 2028, 3 Years After Leaving"
    with working_for(sample.ours.id, sample.administrator.id):
        approvals.end(held, on=date(2026, 11, 18))
    row = former_row(sample, "[Former Review Name]")
    assert row[3] == "30 June 2028, 3 Years After Leaving"
    body = page(signed_in(sample.reader), "/staff/")
    assert "<dt>Approvals Held on That Day</dt><dd>Part-CAO, Part-145</dd>" in body
    assert "<dt>Airworthiness Review Staff</dt><dd>Yes</dd>" in body
    # A person who leaves after Part-145 ended is not given its 3 years.
    leave(sample, "[Review Name]", date(2026, 11, 18))
    assert former_row(sample, "[Review Name]")[3] == "18 November 2028, 2 Years After Leaving"
    # Held to the day before: no longer held from 30 June 2025 is not held on 30 June 2025.
    with working_for(sample.ours.id, sample.administrator.id):
        approvals.record(sample.ours, approval=ApprovalType.PART_145, reference="UK.145.[Number]")
        approvals.end(Approval.objects.get(pk=held.pk), on=date(2025, 7, 1))
    assert former_row(sample, "[Former Review Name]")[3] == "30 June 2028, 3 Years After Leaving"
    with working_for(sample.ours.id, sample.administrator.id):
        approvals.record(sample.ours, approval=ApprovalType.PART_145, reference="UK.145.[Number]")
        approvals.end(Approval.objects.get(pk=held.pk), on=date(2025, 6, 30))
    assert former_row(sample, "[Former Review Name]")[3] == "30 June 2027, 2 Years After Leaving"


def test_a_person_who_was_ever_review_staff_keeps_the_2_years(sample: Sample) -> None:
    """REQ-206, CAO.A.045(e): "all its airworthiness review staff"; finding 6.
    Lucy Grant has a review staff record. Moved to Management and recorded as
    having left, her record is still kept 2 years. So is that of a person with
    no review staff record whose record once said the group and no longer does."""
    with working_for(sample.ours.id, sample.administrator.id):
        review_services.add_review_staff(
            user=sample.lucy,
            authorisation_reference="[Authorisation Reference 1]",
            accepted_on=date(2023, 6, 9),
        )
    # A person with a review staff record whose record never said the group.
    with working_for(sample.ours.id, sample.administrator.id):
        review_services.add_review_staff(
            user=sample.planner,
            authorisation_reference="[Authorisation Reference 3]",
            accepted_on=date(2024, 1, 8),
        )
    leave(sample, "Lucy Grant", date(2026, 11, 17), StaffGroup.MANAGEMENT)
    assert former_row(sample, "Lucy Grant")[3] == "17 November 2028, 2 Years After Leaving"
    leave(sample, "[Planning and Records Name]", date(2026, 11, 17))
    assert (
        former_row(sample, "[Planning and Records Name]")[3]
        == "17 November 2028, 2 Years After Leaving"
    )
    # Regrouped after leaving: the history still says what the person was.
    leave(sample, "[Former Review Name]", date(2025, 6, 30), StaffGroup.OTHER)
    assert former_row(sample, "[Former Review Name]")[3] == "30 June 2027, 2 Years After Leaving"
    # A person who was never review staff has no period in Part-CAO.
    leave(sample, "Chris Moore", date(2026, 11, 17))
    assert former_row(sample, "Chris Moore")[3] == "No Period Given in Part-CAO"


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
        assert build.add_person_records(sample.ours, sample.administrator) == 0
        assert Person.objects.count() == count
