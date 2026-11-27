"""The Dashboard page (REQ-215)."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.dashboard import services


@never_cache
@requires(Action.VIEW_RECORDS)
def dashboard_page(request: HttpRequest) -> HttpResponse:
    """Show the operational overview and its complete register."""
    user = request.user
    assert isinstance(user, User)  # noqa: S101  guaranteed by ``requires``
    panels = services.dashboard(user.organisation, aircraft_services.today())
    return render(
        request, "dashboard/dashboard.html", {"panels": panels, "triage": services.triage(panels)}
    )
