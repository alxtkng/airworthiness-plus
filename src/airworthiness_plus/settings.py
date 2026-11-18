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
    "airworthiness_plus.history",
    "airworthiness_plus.organisations",
    "airworthiness_plus.accounts",
]

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["airworthiness_plus.accounts.backends.OrganisationBackend"]
LOGIN_URL = "sign_in"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
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
SECURE_HSTS_SECONDS = 0 if DEBUG else 31_536_000
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
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
