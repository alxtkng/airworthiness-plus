"""Pages for customers (REQ-207, REQ-210).

Every view names the action it takes, and the role matrix is checked on
the server before it runs (REQ-006). A customer of another organisation is
not found, because the database does not show them (REQ-003).
"""

import uuid

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.customers import services
from airworthiness_plus.customers.forms import CustomerForm
from airworthiness_plus.customers.models import Customer


def _user(request: HttpRequest) -> User:
    user = request.user
    assert isinstance(user, User)  # noqa: S101  guaranteed by ``requires``
    return user


@never_cache
@requires(Action.VIEW_RECORDS)
def customers_page(request: HttpRequest) -> HttpResponse:
    """Every customer, with their aircraft (REQ-210)."""
    lines = services.customer_lines()
    aircraft = sum(len(line.registrations) for line in lines)
    return render(request, "customers/customers.html", {"lines": lines, "aircraft": aircraft})


def _customer_page(request: HttpRequest, customer: Customer, form: CustomerForm) -> HttpResponse:
    return render(
        request,
        "customers/customer.html",
        {"customer": customer, "aircraft": customer.aircraft.all(), "form": form},
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def customer_page(request: HttpRequest, customer_id: uuid.UUID) -> HttpResponse:
    """One customer: what is recorded of them, and their aircraft."""
    customer = get_object_or_404(Customer, pk=customer_id)
    form = CustomerForm(
        initial={
            "name": customer.name,
            "kind": customer.kind,
            "members": customer.members,
            "customer_since": customer.customer_since,
        }
    )
    return _customer_page(request, customer, form)


@never_cache
@requires(Action.ADD_OR_CHANGE_CUSTOMER)
@require_http_methods(["GET", "POST"])
def add_customer(request: HttpRequest) -> HttpResponse:
    """Add a customer (REQ-207)."""
    form = CustomerForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            customer = services.add_customer(
                organisation=_user(request).organisation, **form.cleaned_data
            )
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("customer", customer_id=customer.id)
    return render(request, "customers/add_customer.html", {"form": form})


@never_cache
@requires(Action.ADD_OR_CHANGE_CUSTOMER)
@require_POST
def change_customer(request: HttpRequest, customer_id: uuid.UUID) -> HttpResponse:
    """Change what is recorded of a customer."""
    customer = get_object_or_404(Customer, pk=customer_id)
    form = CustomerForm(request.POST)
    if form.is_valid():
        try:
            services.change_customer(customer, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("customer", customer_id=customer.id)
    customer.refresh_from_db()
    return _customer_page(request, customer, form)
