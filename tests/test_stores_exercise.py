"""Stores lookup training and its separation from operational receipt records."""

import pytest

from airworthiness_plus.history.session import working_for
from airworthiness_plus.logistics.models import StockEntry
from tests.support import Sample, get, post, signed_in

pytestmark = pytest.mark.django_db
URL = "/stores/lookup-exercise/"


def test_stores_exercise_checks_answers_and_rejects_stale_submissions(sample: Sample) -> None:
    reader = signed_in(sample.reader)
    assert b"How many items are on hand at ZRH Main?" in get(reader, URL).content
    incorrect = post(reader, URL, question="store", quantity="8")
    assert b"Check the balance" in incorrect.content
    assert b"How many items are on hand at ZRH Main?" in incorrect.content
    assert post(reader, URL, question="store", quantity="7").status_code == 302
    assert post(reader, URL, question="store", quantity="7").status_code == 302
    assert b"How many items are on hand across ZRH?" in get(reader, URL).content

    assert post(reader, URL, question="station", quantity="8").status_code == 302
    assert post(reader, URL, question="network", quantity="10").status_code == 302
    assert b"Identity check unresolved" in get(reader, URL).content
    assert post(reader, URL, question="available", quantity="8").status_code == 302
    assert b"Exercise Complete" in get(reader, URL).content

    assert b"How many items are on hand at ZRH Main?" in get(signed_in(sample.planner), URL).content
    assert (
        b"How many items are on hand at ZRH Main?" in get(signed_in(sample.stranger), URL).content
    )
    with working_for(sample.ours.pk):
        assert not StockEntry.objects.exists()
