"""Display settings: the person's own, applied to every page (REQ-405 to REQ-410).

Until a person chooses, nothing is written on the page and the device decides
through the stylesheet's media queries: prefers-color-scheme,
prefers-contrast and prefers-reduced-motion. A choice is written on <html> as
a data attribute that drives the tokens in app.css.
"""

import re

import pytest

from airworthiness_plus.accounts.models import User
from airworthiness_plus.history.session import working_for
from tests.support import Sample, page, post, signed_in

pytestmark = pytest.mark.django_db

CHOSEN = {
    "appearance": "Dark",
    "contrast": "High",
    "text_size": "Larger",
    "density": "Comfortable",
    "reduce_motion": "On",
}


def html_tag(body: str) -> str:
    found = re.search(r"<html[^>]*>", body)
    assert found
    return found.group(0)


def test_until_a_person_chooses_the_device_decides(sample: Sample) -> None:
    """REQ-410. Nothing is written, so each media query of the stylesheet applies."""
    assert html_tag(page(signed_in(sample.reader), "/dashboard/")) == '<html lang="en-GB">'


def test_the_choices_are_kept_for_the_person_and_shown_on_every_page(sample: Sample) -> None:
    """REQ-405 to REQ-410. Kept on the account; written on every page the person opens."""
    client = signed_in(sample.reader)
    form = page(client, "/account/display/")
    assert "<legend>Appearance</legend>" in form and "<legend>Reduce Motion</legend>" in form
    response = post(client, "/account/display/", **CHOSEN)
    assert response.status_code == 302
    with working_for(sample.ours.id, sample.reader.id):
        reader = User.objects.get(pk=sample.reader.pk)
    assert {name: getattr(reader, name) for name in CHOSEN} == CHOSEN
    for path in ("/dashboard/", "/account/display/", "/"):
        assert html_tag(page(client, path)) == (
            '<html lang="en-GB" data-appearance="dark" data-contrast="high"'
            ' data-text-size="larger" data-density="comfortable" data-reduce-motion="on">'
        )
    # Another person's pages are not changed.
    assert html_tag(page(signed_in(sample.lucy), "/dashboard/")) == '<html lang="en-GB">'


def test_choosing_standard_or_off_overrides_the_device(sample: Sample) -> None:
    """REQ-406, REQ-409. Standard and Off are written, so a device preference is set aside."""
    client = signed_in(sample.reader)
    post(
        client,
        "/account/display/",
        **(CHOSEN | {"appearance": "Light", "contrast": "Standard", "reduce_motion": "Off"}),
    )
    tag = html_tag(page(client, "/dashboard/"))
    assert 'data-appearance="light"' in tag
    assert 'data-contrast="standard"' in tag
    assert 'data-reduce-motion="off"' in tag


def test_a_choice_that_is_not_offered_is_refused_with_its_reason(sample: Sample) -> None:
    """REQ-397. The error summary links to the setting; nothing is kept."""
    client = signed_in(sample.reader)
    response = post(client, "/account/display/", **(CHOSEN | {"density": "Huge"}))
    body = response.content.decode()
    assert response.status_code == 200
    assert "There Is a Problem" in body and 'href="#id_density_0"' in body
    with working_for(sample.ours.id, sample.reader.id):
        assert User.objects.get(pk=sample.reader.pk).density == "Compact"


def test_the_page_is_linked_beside_the_persons_other_settings(sample: Sample) -> None:
    """REQ-398. Display sits with Change Password and Passkeys, on every page."""
    body = page(signed_in(sample.reader), "/dashboard/")
    account = body.split('<div class="account">', 1)[1].split("</div>", 1)[0]
    assert '<a href="/account/display/">Display</a>' in account
