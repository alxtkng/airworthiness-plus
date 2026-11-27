"""Pages for components and life limits (REQ-230 to REQ-239).

Every view names the action it takes, and the role matrix is checked on
the server before it runs (REQ-006). A component of another organisation
is not found, because the database does not show it (REQ-003).
"""

import uuid
from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.components import services
from airworthiness_plus.components.forms import (
    ComponentForm,
    FitForm,
    LifeFromForm,
    LimitForm,
    RemoveForm,
    ReviewForm,
)
from airworthiness_plus.components.models import Basis, Component, Installation
from airworthiness_plus.interface.forms import Form


def _user(request: HttpRequest) -> User:
    user = request.user
    assert isinstance(user, User)  # noqa: S101  guaranteed by ``requires``
    return user


@never_cache
@requires(Action.VIEW_RECORDS)
def components_page(request: HttpRequest) -> HttpResponse:
    """Components and their limits across the fleet, the nearest first (REQ-234)."""
    lines = services.component_lines(aircraft_services.today())
    return render(
        request,
        "components/components.html",
        {
            "lines": lines,
            "counts": services.counts(lines),
            "may_record": _user(request).may(Action.RECORD_AIRCRAFT_CONFIGURATION),
        },
    )


@never_cache
@requires(Action.RECORD_AIRCRAFT_CONFIGURATION)
@require_http_methods(["GET", "POST"])
def add_component(request: HttpRequest) -> HttpResponse:
    """Add a component with its limit (REQ-230)."""
    form = ComponentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            component = services.add_component(_user(request).organisation, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("component", component_id=component.id)
    return render(request, "components/add.html", {"form": form})


def _page(request: HttpRequest, component: Component, **forms: Form) -> HttpResponse:
    """Show one component, with any form that was refused."""
    line = services.component_line(component, aircraft_services.today())
    fitting = line.fitting
    initial = {
        field: getattr(component, field)
        for field in LimitForm.base_fields
        if getattr(component, field) is not None
    }
    context: dict[str, Any] = {
        "component": component,
        "line": line,
        "fittings": Installation.objects.filter(component=component).order_by("-fitted_on", "-id"),
        "may_record": _user(request).may(Action.RECORD_AIRCRAFT_CONFIGURATION),
        "on_condition": component.basis == Basis.ON_CONDITION,
        "needs_life_from": line.fitted and fitting is not None and fitting.life_from is None,
        "fit_form": FitForm(),
        "remove_form": RemoveForm(),
        "review_form": ReviewForm(),
        "life_form": LifeFromForm(),
        "limit_form": LimitForm(initial=initial),
    }
    context.update(forms)
    return render(request, "components/component.html", context)


@never_cache
@requires(Action.VIEW_RECORDS)
def component_page(request: HttpRequest, component_id: uuid.UUID) -> HttpResponse:
    """One component: its limit, what remains, and where it has been fitted (REQ-235)."""
    return _page(request, get_object_or_404(Component, pk=component_id))


@never_cache
@requires(Action.RECORD_AIRCRAFT_CONFIGURATION)
@require_POST
def fit_component(request: HttpRequest, component_id: uuid.UUID) -> HttpResponse:
    """Record that a component was fitted to an aircraft (REQ-231)."""
    component = get_object_or_404(Component, pk=component_id)
    form = FitForm(request.POST)
    if form.is_valid():
        values = dict(form.cleaned_data)
        try:
            services.fit_component(component, values.pop("aircraft"), **values)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("component", component_id=component.id)
    return _page(request, component, fit_form=form)


@never_cache
@requires(Action.RECORD_AIRCRAFT_CONFIGURATION)
@require_POST
def remove_component(request: HttpRequest, component_id: uuid.UUID) -> HttpResponse:
    """Record that a component was removed (REQ-231)."""
    component = get_object_or_404(Component, pk=component_id)
    form = RemoveForm(request.POST)
    if form.is_valid():
        fitting = services.current_installation(component)
        try:
            if fitting is None:
                raise services.RefusedError("This Component Is Not Fitted")
            services.remove_component(fitting, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("component", component_id=component.id)
    return _page(request, component, remove_form=form)


@never_cache
@requires(Action.RECORD_AIRCRAFT_CONFIGURATION)
@require_POST
def review_component(request: HttpRequest, component_id: uuid.UUID) -> HttpResponse:
    """Record a review of a component kept on condition (REQ-233)."""
    component = get_object_or_404(Component, pk=component_id)
    form = ReviewForm(request.POST)
    if form.is_valid():
        try:
            services.record_review(component, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("component", component_id=component.id)
    return _page(request, component, review_form=form)


@never_cache
@requires(Action.RECORD_AIRCRAFT_CONFIGURATION)
@require_POST
def component_life_from(request: HttpRequest, component_id: uuid.UUID) -> HttpResponse:
    """Record the day a fitted component was new or last overhauled (REQ-232)."""
    component = get_object_or_404(Component, pk=component_id)
    form = LifeFromForm(request.POST)
    if form.is_valid():
        fitting = services.current_installation(component)
        try:
            if fitting is None:
                raise services.RefusedError("This Component Is Not Fitted")
            services.record_life_from(fitting, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("component", component_id=component.id)
    return _page(request, component, life_form=form)


@never_cache
@requires(Action.RECORD_AIRCRAFT_CONFIGURATION)
@require_POST
def change_component_limit(request: HttpRequest, component_id: uuid.UUID) -> HttpResponse:
    """Record another limit for a component (REQ-230)."""
    component = get_object_or_404(Component, pk=component_id)
    form = LimitForm(request.POST)
    if form.is_valid():
        try:
            services.change_limit(component, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("component", component_id=component.id)
    return _page(request, component, limit_form=form)
