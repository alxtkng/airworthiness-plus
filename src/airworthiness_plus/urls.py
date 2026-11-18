"""Addresses of the application."""

from django.urls import URLPattern, URLResolver, path

from airworthiness_plus.accounts import views as accounts

urlpatterns: list[URLPattern | URLResolver] = [
    path("", accounts.home, name="home"),
    path("sign-in/", accounts.sign_in_page, name="sign_in"),
    path("sign-in/code/", accounts.code_page, name="code"),
    path("sign-in/set-up/", accounts.set_up_page, name="set_up"),
    path("sign-out/", accounts.sign_out, name="sign_out"),
]
