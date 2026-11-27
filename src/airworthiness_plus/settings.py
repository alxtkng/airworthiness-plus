"""Django settings for Airworthiness+.

Every deployment value and every secret is read from the environment
(``airworthiness_plus.environment``). Nothing here differs between a
developer's machine, the pipeline and the server except through it.
"""

from pathlib import Path

from airworthiness_plus.environment import flag, listed, optional, required
from airworthiness_plus.history.sql import APPLICATION_ROLE

BASE_DIR = Path(__file__).resolve().parent

SECRET_KEY = required("AIRWORTHINESS_SECRET_KEY")
DEBUG = flag("AIRWORTHINESS_DEBUG")
ALLOWED_HOSTS = listed("AIRWORTHINESS_ALLOWED_HOSTS")

# The administration interface is deliberately absent: there is no vendor or
# support route into an organisation's records (REQ-004, threat TH-024).
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "airworthiness_plus.history",
    "airworthiness_plus.organisations",
    "airworthiness_plus.accounts",
    "airworthiness_plus.people",
    "airworthiness_plus.interface",
    "airworthiness_plus.customers",
    "airworthiness_plus.defects",
    "airworthiness_plus.aircraft",
    "airworthiness_plus.programme",
    "airworthiness_plus.directives",
    "airworthiness_plus.maintenance_data",
    "airworthiness_plus.reviews",
    "airworthiness_plus.exports",
    "airworthiness_plus.acceptance",
    "airworthiness_plus.imports",
    "airworthiness_plus.dashboard",
    "airworthiness_plus.sample",
]

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["airworthiness_plus.accounts.backends.OrganisationBackend"]
LOGIN_URL = "sign_in"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "airworthiness_plus.interface.security.SecurityHeadersMiddleware",
    "airworthiness_plus.interface.health.HealthMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "airworthiness_plus.accounts.middleware.OrganisationContextMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "airworthiness_plus.urls"
WSGI_APPLICATION = "airworthiness_plus.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "airworthiness_plus.interface.navigation.navigation",
            ],
        },
    },
]

# The application works as a database role that owns nothing, cannot delete
# and is subject to row-level security (REQ-003, REQ-131, threats TH-020,
# TH-021). Migrations and the setting up of a new organisation are run
# separately, as the owner of the tables, with this flag set (threat TH-024).
DATABASE_OWNER_WORK = flag("AIRWORTHINESS_DATABASE_OWNER_WORK")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": required("AIRWORTHINESS_DATABASE_NAME"),
        "USER": required("AIRWORTHINESS_DATABASE_USER"),
        "PASSWORD": optional("AIRWORTHINESS_DATABASE_PASSWORD"),
        "HOST": optional("AIRWORTHINESS_DATABASE_HOST"),
        "PORT": optional("AIRWORTHINESS_DATABASE_PORT"),
        # Each request is one transaction, so a response that reports a write
        # as saved is sent only after the write is committed (REQ-138).
        "ATOMIC_REQUESTS": True,
        "OPTIONS": {} if DATABASE_OWNER_WORK else {"assume_role": APPLICATION_ROLE},
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# The stylesheet, the script and the font files are served by the application
# itself, so a page asks nothing of any other site (threat TH-005). They are
# gathered into STATIC_ROOT by ``manage.py collectstatic`` when the service is
# built, and served from there by WhiteNoise.
STATIC_URL = "static/"
STATIC_ROOT = optional("AIRWORTHINESS_STATIC_ROOT") or BASE_DIR.parent.parent / "static-collected"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    # No rule on which characters a password is made of (OWASP ASVS 5.0, 6.2.5).
    {"NAME": "airworthiness_plus.accounts.passwords.ContextWordsValidator"},
]

# The time of every entry is stored in Coordinated Universal Time. Regulatory
# dates are dates with no time, counted in UK local dates by
# ``airworthiness_rules.dates`` (REQ-137).
USE_TZ = True
TIME_ZONE = "UTC"
LANGUAGE_CODE = "en-gb"
USE_I18N = False

# Transport and cookies (threats TH-002, TH-003, TH-005). The application
# runs behind the reverse proxy, which ends HTTPS and sets this header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = not DEBUG
# The health page is asked for inside the container, where there is no HTTPS.
SECURE_REDIRECT_EXEMPT = [r"^health/$"]
SECURE_HSTS_SECONDS = 0 if DEBUG else 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
# No script needs the forgery token: every form carries it in the page.
CSRF_COOKIE_HTTPONLY = True
# A cookie named with this prefix is accepted by a browser only over HTTPS,
# for this host alone and for every path of it (OWASP ASVS 5.0, 3.3.1, 3.3.3).
SESSION_COOKIE_NAME = "sessionid" if DEBUG else "__Host-sessionid"
CSRF_COOKIE_NAME = "csrftoken" if DEBUG else "__Host-csrftoken"
# The address of each request is taken from the reverse proxy only when the
# service is told it runs behind one (OWASP ASVS 5.0, 15.3.4).
BEHIND_PROXY = flag("AIRWORTHINESS_BEHIND_PROXY")

# A form is small. The largest is the check of an import: two fields for each
# value of a file of 2,000 rows.
DATA_UPLOAD_MAX_MEMORY_SIZE = 1_000_000
DATA_UPLOAD_MAX_NUMBER_FIELDS = 50_000
FILE_UPLOAD_MAX_MEMORY_SIZE = 1_000_000

# Unexpected errors and security events go to standard error, one line each,
# with the time in Coordinated Universal Time, for the server to collect
# (OWASP ASVS 5.0, 16.2.1, 16.2.2, 16.3.4). No request body, password or
# session identifier is ever written to a log.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "line": {
            "()": "airworthiness_plus.interface.logs.UtcFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "standard_error": {"class": "logging.StreamHandler", "formatter": "line"},
    },
    "root": {"handlers": ["standard_error"], "level": "WARNING"},
    "loggers": {
        "django": {"handlers": ["standard_error"], "level": "WARNING", "propagate": False},
    },
}
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
# A session ends when the browser closes, 30 minutes after its last request,
# and 12 hours after sign-in whatever happens. The two time limits are kept
# by ``airworthiness_plus.accounts.middleware``.
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 12 * 60 * 60
CSRF_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"

# HTTP Strict Transport Security is set for this host only. Including
# subdomains or preloading would bind every other service under the domain,
# which this application does not own.
SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W021"]
