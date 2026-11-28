"""Case 4 station and identity lookup against actual posted Stores movements."""

from decimal import Decimal

import pytest
from django.db import DatabaseError, transaction

from airworthiness_plus.history.session import working_for
from airworthiness_plus.logistics.models import StoreLocation
from tests.support import Sample, get, post, signed_in
from tests.test_stores import _lucy, dispose, posted, receipt, today  # noqa: F401

pytestmark = pytest.mark.django_db


def test_station_lookup_groups_exact_posted_identity_including_zero_station(sample: Sample) -> None:
    manager = signed_in(sample.lucy)
    look = "/stores/?identity=PN-713"
    with working_for(sample.ours.id, sample.lucy.id):
        for name, code, quantity in (
            ("ZRH Main", "zrh", 7),
            ("ZRH Line", "ZRH", 1),
            ("BSL Main", "BSL", 1),
            ("LUG Main", "LUG", 1),
            ("GVA Main", "GVA", 0),
        ):
            location_form = post(
                manager,
                "/stores/locations/add/",
                name=name,
                station=code,
                kind="Serviceable Stores",
                holds_components="on",
            )
            assert location_form.status_code == 302, location_form.content.decode()
            place = StoreLocation.objects.get(name=name)
            assert place.station == code.upper()
            if quantity:
                posted(dispose(receipt(sample.ours, name, quantity=quantity)), _lucy(sample), place)

        main = StoreLocation.objects.get(name="ZRH Main")
        posted(
            dispose(receipt(sample.ours, "PART-EXTENSION", quantity=19)),
            _lucy(sample),
            main,
            part_number="PN-713-EXT",
        )
        posted(
            dispose(receipt(sample.ours, "TEXT-ONLY", quantity=3, item="Looks like PN-713")),
            _lucy(sample),
            main,
            part_number="PN-999",
        )
        with pytest.raises(DatabaseError), transaction.atomic():
            StoreLocation.objects.filter(pk=main.pk).update(station="BSL")

    response = get(manager, look)
    assert response.status_code == 200
    assert response.context is not None
    summary = response.context["summary"]
    assert {row.name: row.on_hand for row in summary.network} == {"Network": Decimal(10)}
    assert {row.name: row.on_hand for row in summary.stations} == {
        "ZRH": Decimal(8),
        "BSL": Decimal(1),
        "LUG": Decimal(1),
        "GVA": Decimal(0),
    }
    assert {row.name: row.on_hand for row in summary.locations} == {
        "ZRH Main": Decimal(7),
        "ZRH Line": Decimal(1),
        "BSL Main": Decimal(1),
        "LUG Main": Decimal(1),
        "GVA Main": Decimal(0),
    }
    assert all(row.available == row.on_hand and row.reserved == 0 for row in summary.locations)
    body = response.content.decode()
    assert "PART-EXTENSION" not in body
    assert "Looks like PN-713" not in body
    assert '<table aria-labelledby="station-stock">' in body
    assert '<th scope="row">GVA</th><td>Each</td><td>0</td>' in body
    assert '<th scope="row">ZRH</th><td>Each</td><td>8</td>' in body
    assert '<th scope="row">Network</th><td>Each</td><td>10</td>' in body
    assert '<th scope="row">ZRH Main</th><td>Each</td><td>7</td>' in body
    lower_case = get(manager, "/stores/?identity=pn-713")
    assert lower_case.context["summary"] == summary
