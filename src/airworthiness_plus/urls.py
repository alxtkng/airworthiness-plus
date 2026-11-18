"""Addresses of the application."""

from django.urls import URLPattern, URLResolver, path

from airworthiness_plus.accounts import views as accounts
from airworthiness_plus.aircraft import views as aircraft

urlpatterns: list[URLPattern | URLResolver] = [
    path("", aircraft.fleet, name="home"),
    path("transfers/", aircraft.transfers, name="transfers"),
    path("aircraft/add/", aircraft.add_aircraft, name="add_aircraft"),
    path("aircraft/<uuid:aircraft_id>/", aircraft.aircraft_page, name="aircraft"),
    path(
        "aircraft/<uuid:aircraft_id>/hours-and-cycles/",
        aircraft.enter_utilisation,
        name="enter_utilisation",
    ),
    path(
        "aircraft/<uuid:aircraft_id>/unserviceable/",
        aircraft.make_unserviceable,
        name="make_unserviceable",
    ),
    path(
        "aircraft/<uuid:aircraft_id>/serviceable/",
        aircraft.make_serviceable,
        name="make_serviceable",
    ),
    path("aircraft/<uuid:aircraft_id>/counters/", aircraft.add_counter, name="add_counter"),
    path(
        "aircraft/<uuid:aircraft_id>/records-received/",
        aircraft.records_received,
        name="records_received",
    ),
    path("sign-in/", accounts.sign_in_page, name="sign_in"),
    path("sign-in/code/", accounts.code_page, name="code"),
    path("sign-in/set-up/", accounts.set_up_page, name="set_up"),
    path("sign-out/", accounts.sign_out, name="sign_out"),
]
