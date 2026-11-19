# The Airworthiness+ service: the application and its static files, run by Gunicorn.
#
# The base image is pinned by digest (threat TH-060). The dependencies are installed
# from uv.lock with verified hashes. The built image holds no source control folder,
# no tests and no development tools, and runs as a user that owns nothing.

FROM python:3.13-slim-bookworm@sha256:a5a7017efc5969e00ae2b91c8eb0631049a569652aa4ffc4501769049ae45c72 AS build

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m pip install --no-cache-dir "uv==0.11.32"

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

# Gather the stylesheet, the script and the fonts. No database is touched: the
# values below only let the settings load.
RUN AIRWORTHINESS_SECRET_KEY=build-only \
    AIRWORTHINESS_DATABASE_NAME=build-only \
    AIRWORTHINESS_DATABASE_USER=build-only \
    AIRWORTHINESS_STATIC_ROOT=/app/static \
    DJANGO_SETTINGS_MODULE=airworthiness_plus.settings \
    /app/.venv/bin/python -m django collectstatic --noinput

FROM python:3.13-slim-bookworm@sha256:a5a7017efc5969e00ae2b91c8eb0631049a569652aa4ffc4501769049ae45c72

RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin airworthiness

WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY --from=build /app/static /app/static

ENV PATH=/app/.venv/bin:$PATH \
    DJANGO_SETTINGS_MODULE=airworthiness_plus.settings \
    AIRWORTHINESS_STATIC_ROOT=/app/static \
    AIRWORTHINESS_BEHIND_PROXY=true \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER 10001
EXPOSE 8000

# Asks the service itself whether it can reach its database.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-m", "airworthiness_plus.interface.health"]

# Two workers suit a small server. Requests and errors go to standard output and
# standard error for the server to collect; no request body is ever logged.
CMD ["gunicorn", "airworthiness_plus.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--timeout", "60", \
     "--limit-request-line", "4094", \
     "--limit-request-fields", "50", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
