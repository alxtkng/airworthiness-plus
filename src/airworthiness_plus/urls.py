"""Addresses of the application."""

from django.urls import URLPattern, URLResolver, path

from airworthiness_plus.accounts import views as accounts
from airworthiness_plus.aircraft import views as aircraft
from airworthiness_plus.directives import views as directives
from airworthiness_plus.programme import views as programme

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
    path("aircraft/<uuid:aircraft_id>/programme/", programme.programme_page, name="programme"),
    path(
        "aircraft/<uuid:aircraft_id>/programme/set-up/",
        programme.set_up_programme,
        name="set_up_programme",
    ),
    path("aircraft/<uuid:aircraft_id>/programme/tasks/add/", programme.add_task, name="add_task"),
    path(
        "aircraft/<uuid:aircraft_id>/programme/review/",
        programme.record_review,
        name="record_review",
    ),
    path("aircraft/<uuid:aircraft_id>/work/add/", programme.record_work, name="record_work"),
    path("tasks/<uuid:task_id>/retire/", programme.retire_task, name="retire_task"),
    path("work/<uuid:work_id>/release/", programme.record_release, name="record_release"),
    path("directives/", directives.directives_page, name="directives"),
    path("directives/add/", directives.add_directive, name="add_directive"),
    path(
        "aircraft/<uuid:aircraft_id>/directives/",
        directives.status_page,
        name="directive_status",
    ),
    path(
        "aircraft/<uuid:aircraft_id>/directives/<uuid:directive_id>/decide/",
        directives.decide,
        name="decide_directive",
    ),
    path(
        "directive-decisions/<uuid:applicability_id>/comply/",
        directives.comply,
        name="comply_directive",
    ),
    path(
        "directive-decisions/<uuid:applicability_id>/terminate/",
        directives.terminate,
        name="terminate_directive",
    ),
    path("sign-in/", accounts.sign_in_page, name="sign_in"),
    path("sign-in/code/", accounts.code_page, name="code"),
    path("sign-in/set-up/", accounts.set_up_page, name="set_up"),
    path("sign-out/", accounts.sign_out, name="sign_out"),
]
