"""Whether the service is up and can reach its database.

The page at ``/health/`` says OK or Unavailable and nothing else. It needs
no sign-in and shows no record, version or setting (OWASP ASVS 5.0,
13.4.5). It is answered by a middleware, not a view, so that it answers
when the database does not. Run as a program, this module asks that page of the service in
the same container, which is how the container's health is checked.
"""

import os
import sys
import urllib.error
import urllib.request
from collections.abc import Callable

from django.db import DatabaseError, connection
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed

ADDRESS = "/health/"
TEXT = "text/plain; charset=utf-8"


def database_answers() -> bool:
    """Return whether the database answers a question that needs no table."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return False
    return True


class HealthMiddleware:
    """Answer the health page before anything that needs a session or the database.

    If the database is down, every other page fails; this one must still
    answer, to say so.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.path != ADDRESS:
            return self.get_response(request)
        if request.method not in ("GET", "HEAD"):
            return HttpResponseNotAllowed(["GET", "HEAD"])
        if database_answers():
            return HttpResponse("OK", content_type=TEXT)
        return HttpResponse("Unavailable", status=503, content_type=TEXT)


def main() -> int:
    """Ask the service in this container for its health page. 0 means healthy."""
    host = os.environ.get("AIRWORTHINESS_ALLOWED_HOSTS", "localhost").split(",")[0].strip()
    request = urllib.request.Request("http://127.0.0.1:8000/health/", headers={"Host": host})
    try:
        with urllib.request.urlopen(request, timeout=4) as response:  # noqa: S310
            return 0 if response.status == 200 else 1
    except (urllib.error.URLError, OSError):
        return 1


if __name__ == "__main__":
    sys.exit(main())
