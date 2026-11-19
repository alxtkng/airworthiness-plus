"""What every response carries, and which requests are answered at all (REQ-132).

Threats TH-004 and TH-005; OWASP ASVS 5.0, 3.4.3, 3.4.6, 13.4.4, 14.3.1 and
14.3.2. A page loads its stylesheet, its script and its fonts from the
application and from nowhere else, runs no script of its own, cannot be
put in a frame, and is not kept by the browser once it has been shown.
"""

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed

# The application has pages and forms and nothing else.
METHODS = ("GET", "HEAD", "POST")

CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'none'",
        "script-src 'self'",
        "style-src 'self'",
        "font-src 'self'",
        "img-src 'self'",
        "connect-src 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "base-uri 'none'",
        "object-src 'none'",
    )
)

# No page uses any of these, so none is allowed to it or to anything it frames.
PERMISSIONS_POLICY = "camera=(), geolocation=(), microphone=(), payment=(), usb=()"


class SecurityHeadersMiddleware:
    """Refuse methods the application does not use, and set the headers of every response."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.method not in METHODS:
            response: HttpResponse = HttpResponseNotAllowed(METHODS)
        else:
            response = self.get_response(request)
        response["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
        response["Permissions-Policy"] = PERMISSIONS_POLICY
        response["X-Frame-Options"] = "DENY"
        # Static files say how long they may be kept; nothing else is kept at all.
        if not response.has_header("Cache-Control"):
            response["Cache-Control"] = "no-store"
        return response
