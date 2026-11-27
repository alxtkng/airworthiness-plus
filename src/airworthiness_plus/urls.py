"""Addresses of the application."""

from django.urls import URLPattern, URLResolver, path

from airworthiness_plus.acceptance import views as acceptance
from airworthiness_plus.accounts import user_views as users
from airworthiness_plus.accounts import views as accounts
from airworthiness_plus.aircraft import views as aircraft
from airworthiness_plus.customers import views as customers
from airworthiness_plus.dashboard import views as dashboard
from airworthiness_plus.defects import views as defects
from airworthiness_plus.directives import views as directives
from airworthiness_plus.exports import views as exports
from airworthiness_plus.imports import views as imports
from airworthiness_plus.maintenance_data import views as data
from airworthiness_plus.organisations import views as settings
from airworthiness_plus.people import views as people
from airworthiness_plus.programme import views as programme
from airworthiness_plus.reviews import views as reviews

urlpatterns: list[URLPattern | URLResolver] = [
    path("", aircraft.fleet, name="home"),
    path("dashboard/", dashboard.dashboard_page, name="dashboard"),
    path("transfers/", aircraft.transfers, name="transfers"),
    path("defects/", defects.defects_page, name="defects"),
    path("defects/record/", defects.record_defect, name="record_defect"),
    path("defects/repeat/", defects.repeat_defects, name="repeat_defects"),
    path("defects/repeat/action/", defects.record_repeat_action, name="record_repeat_action"),
    path("defects/<uuid:defect_id>/", defects.defect_page, name="defect"),
    path("defects/<uuid:defect_id>/close/", defects.close_defect, name="close_defect"),
    path("aircraft/add/", aircraft.add_aircraft, name="add_aircraft"),
    path("aircraft/<uuid:aircraft_id>/", aircraft.aircraft_page, name="aircraft"),
    path("aircraft/<uuid:aircraft_id>/details/", aircraft.record_details, name="aircraft_details"),
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
    path("aircraft/<uuid:aircraft_id>/owner/", aircraft.change_owner, name="change_owner"),
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
    path("maintenance-data/", data.data_page, name="maintenance_data"),
    path("maintenance-data/add/", data.add_data, name="add_data"),
    path("maintenance-data/<uuid:data_set_id>/", data.data_set_page, name="data_set"),
    path("maintenance-data/<uuid:data_set_id>/revisions/", data.add_revision, name="add_revision"),
    path("maintenance-data/<uuid:data_set_id>/checks/", data.record_check, name="record_check"),
    path(
        "maintenance-data/<uuid:data_set_id>/customer-status/",
        data.customer_status,
        name="customer_status",
    ),
    path(
        "maintenance-data/<uuid:data_set_id>/no-longer-held/",
        data.end_holding,
        name="end_holding",
    ),
    path(
        "aircraft/<uuid:aircraft_id>/maintenance-data/",
        data.aircraft_data_page,
        name="aircraft_data",
    ),
    path("reviews/", reviews.schedule_page, name="review_schedule"),
    path("review-staff/", reviews.staff_page, name="review_staff"),
    path("review-staff/add/", reviews.add_staff, name="add_review_staff"),
    path(
        "review-staff/<uuid:staff_id>/involvement/",
        reviews.update_involvement,
        name="update_involvement",
    ),
    path(
        "review-staff/<uuid:staff_id>/restoration/",
        reviews.record_restoration,
        name="record_restoration",
    ),
    path(
        "aircraft/<uuid:aircraft_id>/review/", reviews.aircraft_review_page, name="aircraft_review"
    ),
    path(
        "aircraft/<uuid:aircraft_id>/review/certificates/",
        reviews.record_certificate,
        name="record_certificate",
    ),
    path("aircraft/<uuid:aircraft_id>/review/start/", reviews.start_review, name="start_review"),
    path("reviews/<uuid:review_id>/", reviews.review_page, name="review"),
    path("reviews/<uuid:review_id>/details/", reviews.review_details, name="review_details"),
    path("reviews/<uuid:review_id>/issue/", reviews.issue, name="issue_certificate"),
    path("review-items/<uuid:item_id>/", reviews.record_item, name="record_review_item"),
    path("review-items/<uuid:item_id>/close/", reviews.close_finding, name="close_review_finding"),
    path("certificates/<uuid:certificate_id>/", reviews.certificate_page, name="certificate"),
    path("certificates/<uuid:certificate_id>/void/", reviews.void, name="void_certificate"),
    path("certificates/<uuid:certificate_id>/extend/", reviews.extend, name="extend_certificate"),
    path(
        "certificates/<uuid:certificate_id>/copy-sent/",
        reviews.certificate_copy_sent,
        name="certificate_copy_sent",
    ),
    path(
        "extensions/<uuid:extension_id>/copy-sent/",
        reviews.extension_copy_sent,
        name="extension_copy_sent",
    ),
    path("customers/", customers.customers_page, name="customers"),
    path("customers/add/", customers.add_customer, name="add_customer"),
    path("customers/<uuid:customer_id>/", customers.customer_page, name="customer"),
    path(
        "customers/<uuid:customer_id>/change/",
        customers.change_customer,
        name="change_customer",
    ),
    path("staff/", people.staff_page, name="staff"),
    path("staff/add/", people.add_person, name="add_person"),
    path("staff/<uuid:person_id>/", people.person_page, name="person"),
    path("staff/<uuid:person_id>/change/", people.change_person, name="change_person"),
    path("records-export/", exports.exports_page, name="records_export"),
    path("records-export/organisation/", exports.export_organisation, name="export_organisation"),
    path("aircraft/<uuid:aircraft_id>/export/", exports.export_aircraft, name="export_aircraft"),
    path("imports/", imports.imports_page, name="imports"),
    path("imports/load/", imports.load, name="load_import"),
    path("imports/<uuid:load_id>/", imports.report_page, name="import_report"),
    path("imports/<uuid:load_id>/check/", imports.check, name="check_import"),
    path("problem-log/", acceptance.problem_log, name="problem_log"),
    path("problem-log/add/", acceptance.add_problem, name="add_problem"),
    path("problem-log/<uuid:problem_id>/notes/", acceptance.add_note, name="add_problem_note"),
    path("organisation/", acceptance.organisation_page, name="organisation"),
    path("organisation/approval/", acceptance.record_approval, name="record_records_approval"),
    path("organisation/parallel-run/", acceptance.record_parallel_run, name="record_parallel_run"),
    path("settings/", settings.settings_page, name="settings"),
    path("settings/details/", settings.change_details, name="change_organisation_details"),
    path("settings/approvals/", settings.record_approval_held, name="record_approval_held"),
    path(
        "settings/approvals/<uuid:approval_id>/end/",
        settings.end_approval_held,
        name="end_approval_held",
    ),
    path("settings/lead-times/", settings.set_lead_times, name="set_lead_times"),
    path(
        "settings/deferral-limits/",
        settings.set_deferral_limits,
        name="set_deferral_limits",
    ),
    path("users/", users.users_page, name="users"),
    path("users/access-log/", users.access_log, name="access_log"),
    path("users/add/", users.add_user, name="add_user"),
    path("users/<uuid:user_id>/roles/", users.set_roles, name="set_user_roles"),
    path("users/<uuid:user_id>/active/", users.set_active, name="set_user_active"),
    path("users/<uuid:user_id>/password/", users.reset_password, name="reset_user_password"),
    path(
        "users/<uuid:user_id>/second-factor/",
        users.reset_second_factor,
        name="reset_user_second_factor",
    ),
    path("users/<uuid:user_id>/sessions/", users.end_sessions, name="end_user_sessions"),
    path("account/password/", users.change_password, name="change_password"),
    path("account/sessions/", users.end_other_sessions, name="end_other_sessions"),
    path("account/sessions/<uuid:session_id>/end/", users.end_session, name="end_session"),
    path("sign-in/", accounts.sign_in_page, name="sign_in"),
    path("sign-in/code/", accounts.code_page, name="code"),
    path("sign-in/set-up/", accounts.set_up_page, name="set_up"),
    path("sign-out/", accounts.sign_out, name="sign_out"),
]
