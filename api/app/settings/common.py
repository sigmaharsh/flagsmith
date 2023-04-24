"""
Django settings for app project.

Generated by 'django-admin startproject' using Django 1.9.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""
import importlib
import json
import logging
import os
import sys
import warnings
from datetime import datetime, timedelta
from importlib import reload

import dj_database_url
import pytz
import requests
from corsheaders.defaults import default_headers
from django.core.management.utils import get_random_secret_key
from environs import Env

from task_processor.task_run_method import TaskRunMethod

env = Env()

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

ENV = env("ENVIRONMENT", default="local")
if ENV not in ("local", "dev", "staging", "production"):
    warnings.warn(
        "ENVIRONMENT env variable must be one of local, dev, staging, production"
    )

DEBUG = env.bool("DEBUG", default=False)

ADMINS = []
MANAGERS = []

# Enables the sending of telemetry data to the central Flagsmith API for usage tracking
ENABLE_TELEMETRY = env.bool("ENABLE_TELEMETRY", default=True)

# Enables gzip compression
ENABLE_GZIP_COMPRESSION = env.bool("ENABLE_GZIP_COMPRESSION", default=False)

SECRET_KEY = env("DJANGO_SECRET_KEY", default=get_random_secret_key())

HOSTED_SEATS_LIMIT = env.int("HOSTED_SEATS_LIMIT", default=0)

# Google Analytics Configuration
GOOGLE_ANALYTICS_KEY = env("GOOGLE_ANALYTICS_KEY", default="")
GOOGLE_SERVICE_ACCOUNT = env("GOOGLE_SERVICE_ACCOUNT", default=None)
GA_TABLE_ID = env("GA_TABLE_ID", default=None)

INFLUXDB_TOKEN = env.str("INFLUXDB_TOKEN", default="")
INFLUXDB_BUCKET = env.str("INFLUXDB_BUCKET", default="")
INFLUXDB_URL = env.str("INFLUXDB_URL", default="")
INFLUXDB_ORG = env.str("INFLUXDB_ORG", default="")

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])
USE_X_FORWARDED_HOST = env.bool("USE_X_FORWARDED_HOST", default=False)

USE_POSTGRES_FOR_ANALYTICS = env.bool("USE_POSTGRES_FOR_ANALYTICS", default=False)

CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

INTERNAL_IPS = ["127.0.0.1"]

# In order to run a load balanced solution, we need to whitelist the internal ip
try:
    internal_ip = requests.get("http://instance-data/latest/meta-data/local-ipv4").text
except requests.exceptions.ConnectionError:
    pass
else:
    ALLOWED_HOSTS.append(internal_ip)
del requests

if sys.version[0] == "2":
    reload(sys)
    sys.setdefaultencoding("utf-8")

# Application definition

INSTALLED_APPS = [
    "core.custom_admin.apps.CustomAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "rest_framework",
    "rest_framework.authtoken",
    # Used for managing api keys
    "rest_framework_api_key",
    "djoser",
    "django.contrib.sites",
    "custom_auth",
    "admin_sso",
    "api",
    "core",
    "corsheaders",
    "users",
    "organisations",
    "organisations.invites",
    "organisations.permissions",
    "organisations.roles",
    "projects",
    "sales_dashboard",
    "environments",
    "environments.permissions",
    "environments.identities",
    "environments.identities.traits",
    "features",
    "features.multivariate",
    "features.workflows.core",
    "segments",
    "app",
    "e2etests",
    "simple_history",
    "drf_yasg2",
    "audit",
    "permissions",
    "projects.tags",
    "api_keys",
    # 2FA
    "trench",
    # health check plugins
    "health_check",
    "health_check.db",
    "health_check.contrib.migrations",
    # Used for ordering models (e.g. FeatureSegment)
    "ordered_model",
    # Third party integrations
    "integrations.datadog",
    "integrations.amplitude",
    "integrations.sentry",
    "integrations.new_relic",
    "integrations.segment",
    "integrations.heap",
    "integrations.mixpanel",
    "integrations.rudderstack",
    "integrations.slack",
    "integrations.webhook",
    "integrations.dynatrace",
    # Rate limiting admin endpoints
    "axes",
    "telemetry",
    # for filtering querysets on viewsets
    "django_filters",
    "import_export",
    "task_processor",
    "softdelete",
    "metadata",
    "app_analytics",
]

SITE_ID = 1

db_conn_max_age = env.int("DJANGO_DB_CONN_MAX_AGE", 60)
DJANGO_DB_CONN_MAX_AGE = None if db_conn_max_age == -1 else db_conn_max_age

DATABASE_ROUTERS = ["app.routers.PrimaryReplicaRouter"]
NUM_DB_REPLICAS = 0
# Allows collectstatic to run without a database, mainly for Docker builds to collectstatic at build time
if "DATABASE_URL" in os.environ:
    DATABASES = {
        "default": dj_database_url.parse(
            env("DATABASE_URL"), conn_max_age=DJANGO_DB_CONN_MAX_AGE
        ),
    }
    REPLICA_DATABASE_URLS_DELIMITER = env("REPLICA_DATABASE_URLS_DELIMITER", ",")
    REPLICA_DATABASE_URLS = env.list(
        "REPLICA_DATABASE_URLS", default=[], delimiter=REPLICA_DATABASE_URLS_DELIMITER
    )
    NUM_DB_REPLICAS = len(REPLICA_DATABASE_URLS)
    for i, db_url in enumerate(REPLICA_DATABASE_URLS, start=1):
        DATABASES[f"replica_{i}"] = dj_database_url.parse(
            db_url, conn_max_age=DJANGO_DB_CONN_MAX_AGE
        )

    if "ANALYTICS_DATABASE_URL" in os.environ:
        DATABASES["analytics"] = dj_database_url.parse(
            env("ANALYTICS_DATABASE_URL"), conn_max_age=DJANGO_DB_CONN_MAX_AGE
        )
        DATABASE_ROUTERS.insert(0, "app.routers.AnalyticsRouter")
elif "DJANGO_DB_NAME" in os.environ:
    # If there is no DATABASE_URL configured, check for old style DB config parameters
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["DJANGO_DB_NAME"],
            "USER": os.environ["DJANGO_DB_USER"],
            "PASSWORD": os.environ["DJANGO_DB_PASSWORD"],
            "HOST": os.environ["DJANGO_DB_HOST"],
            "PORT": os.environ["DJANGO_DB_PORT"],
            "CONN_MAX_AGE": DJANGO_DB_CONN_MAX_AGE,
        },
    }
    if "DJANGO_DB_NAME_ANALYTICS" in os.environ:
        DATABASES["analytics"] = {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["DJANGO_DB_NAME_ANALYTICS"],
            "USER": os.environ["DJANGO_DB_USER_ANALYTICS"],
            "PASSWORD": os.environ["DJANGO_DB_PASSWORD_ANALYTICS"],
            "HOST": os.environ["DJANGO_DB_HOST_ANALYTICS"],
            "PORT": os.environ["DJANGO_DB_PORT_ANALYTICS"],
            "CONN_MAX_AGE": DJANGO_DB_CONN_MAX_AGE,
        }

        DATABASE_ROUTERS.insert(0, "app.routers.AnalyticsRouter")

LOGIN_THROTTLE_RATE = env("LOGIN_THROTTLE_RATE", "20/min")
SIGNUP_THROTTLE_RATE = env("SIGNUP_THROTTLE_RATE", "10000/min")
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
    ),
    "PAGE_SIZE": 10,
    "UNICODE_JSON": False,
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "DEFAULT_THROTTLE_RATES": {
        "login": LOGIN_THROTTLE_RATE,
        "signup": SIGNUP_THROTTLE_RATE,
        "mfa_code": "5/min",
        "invite": "10/min",
    },
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
}
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    # Add master api key object to request
    "api_keys.middleware.MasterAPIKeyMiddleware",
]

ADD_NEVER_CACHE_HEADERS = env.bool("ADD_NEVER_CACHE_HEADERS", True)
if ADD_NEVER_CACHE_HEADERS:
    MIDDLEWARE.append("core.middleware.cache_control.NeverCacheMiddleware")

APPLICATION_INSIGHTS_CONNECTION_STRING = env.str(
    "APPLICATION_INSIGHTS_CONNECTION_STRING", default=None
)
OPENCENSUS_SAMPLING_RATE = env.float("OPENCENSUS_SAMPLING_RATE", 1.0)

if APPLICATION_INSIGHTS_CONNECTION_STRING:
    MIDDLEWARE.insert(
        0, "integrations.opencensus.middleware.OpenCensusDbTraceMiddleware"
    )
    MIDDLEWARE.insert(0, "opencensus.ext.django.middleware.OpencensusMiddleware")
    OPENCENSUS = {
        "TRACE": {
            "SAMPLER": f"opencensus.trace.samplers.ProbabilitySampler(rate={OPENCENSUS_SAMPLING_RATE})",
            "EXPORTER": f"""opencensus.ext.azure.trace_exporter.AzureExporter(
                connection_string='{APPLICATION_INSIGHTS_CONNECTION_STRING}',
            )""",
        }
    }

if ENABLE_GZIP_COMPRESSION:
    # ref: https://docs.djangoproject.com/en/2.2/ref/middleware/#middleware-ordering
    MIDDLEWARE.insert(1, "django.middleware.gzip.GZipMiddleware")

if GOOGLE_ANALYTICS_KEY:
    MIDDLEWARE.append("app_analytics.middleware.GoogleAnalyticsMiddleware")

if INFLUXDB_TOKEN:
    MIDDLEWARE.append("app_analytics.middleware.InfluxDBMiddleware")

if USE_POSTGRES_FOR_ANALYTICS:
    if INFLUXDB_TOKEN:
        raise RuntimeError("Cannot use both InfluxDB and Postgres for analytics")

    MIDDLEWARE.append("app_analytics.middleware.APIUsageMiddleware")

ALLOWED_ADMIN_IP_ADDRESSES = env.list("ALLOWED_ADMIN_IP_ADDRESSES", default=list())
if len(ALLOWED_ADMIN_IP_ADDRESSES) > 0:
    warnings.warn(
        "Restricting access to the admin site for ip addresses %s"
        % ", ".join(ALLOWED_ADMIN_IP_ADDRESSES)
    )
    MIDDLEWARE.append("core.middleware.admin.AdminWhitelistMiddleware")

ROOT_URLCONF = "app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": ["templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "app.wsgi.application"

# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = [
    "admin_sso.auth.DjangoSSOAuthBackend",
    "django.contrib.auth.backends.ModelBackend",
]

DJANGO_ADMIN_SSO_OAUTH_CLIENT_ID = env.str("OAUTH_CLIENT_ID", default="")
DJANGO_ADMIN_SSO_OAUTH_CLIENT_SECRET = env.str("OAUTH_CLIENT_SECRET", default="")

# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(PROJECT_ROOT, "../../static/")

MEDIA_URL = "/media/"  # unused but needs to be different from STATIC_URL in django 3

# CORS settings

CORS_ORIGIN_ALLOW_ALL = True
FLAGSMITH_CORS_EXTRA_ALLOW_HEADERS = env.list(
    "FLAGSMITH_CORS_EXTRA_ALLOW_HEADERS", default=["sentry-trace"]
)
CORS_ALLOW_HEADERS = [
    *default_headers,
    *FLAGSMITH_CORS_EXTRA_ALLOW_HEADERS,
    "X-Environment-Key",
    "X-E2E-Test-Auth-Token",
]

DEFAULT_FROM_EMAIL = env("SENDER_EMAIL", default="noreply@flagsmith.com")
EMAIL_CONFIGURATION = {
    # Invitations with name is anticipated to take two arguments. The persons name and the
    # organisation name they are invited to.
    "INVITE_SUBJECT_WITH_NAME": "%s has invited you to join the organisation '%s' on Flagsmith",
    # Invitations without a name is anticipated to take one arguments. The organisation name they
    # are invited to.
    "INVITE_SUBJECT_WITHOUT_NAME": "You have been invited to join the organisation '%s' on "
    "Flagsmith",
    # The email address invitations will be sent from.
    "INVITE_FROM_EMAIL": DEFAULT_FROM_EMAIL,
}

AWS_SES_REGION_NAME = env("AWS_SES_REGION_NAME", default=None)
AWS_SES_REGION_ENDPOINT = env("AWS_SES_REGION_ENDPOINT", default=None)

# Used on init to create admin user for the site, update accordingly before hitting /auth/init
ALLOW_ADMIN_INITIATION_VIA_URL = True
ADMIN_EMAIL = "admin@example.com"
ADMIN_INITIAL_PASSWORD = "password"

AUTH_USER_MODEL = "users.FFAdminUser"

ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_VERIFICATION = "none"  # TODO: configure email verification

# Set up Email
EMAIL_BACKEND = env("EMAIL_BACKEND", default="sgbackend.SendGridBackend")
if EMAIL_BACKEND == "sgbackend.SendGridBackend":
    SENDGRID_API_KEY = env("SENDGRID_API_KEY", default=None)
    if not SENDGRID_API_KEY:
        logging.info(
            "`SENDGRID_API_KEY` has not been configured. You will not receive emails."
        )
elif EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend":
    EMAIL_HOST = env("EMAIL_HOST", default="localhost")
    EMAIL_HOST_USER = env("EMAIL_HOST_USER", default=None)
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default=None)
    EMAIL_PORT = env("EMAIL_PORT", default=587)
    EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)

SWAGGER_SETTINGS = {
    "SHOW_REQUEST_HEADERS": True,
    "SECURITY_DEFINITIONS": {
        "Private": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Every time you create a new Project Environment, an environment API key is automatically generated for you. This is all you need to pass in to get access to Flags etc. <br />Example value: <br />Token 884b1b4c6b4ddd112e7a0a139f09eb85e8c254ff",  # noqa
        },
        "Public": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Environment-Key",
            "description": "Things like creating new flags, environments, toggle flags or indeed anything that is possible from the administrative front end. <br />Example value: <br />FFnVjhp7xvkT5oTLq4q788",  # noqa
        },
    },
}


LOGIN_URL = "/admin/login/"
LOGOUT_URL = "/admin/logout/"

# Email associated with user that is used by front end for end to end testing purposes
FE_E2E_TEST_USER_EMAIL = "nightwatch@solidstategroup.com"

# SSL handling in Django
SECURE_PROXY_SSL_HEADER_NAME = env.str(
    "SECURE_PROXY_SSL_HEADER_NAME", "HTTP_X_FORWARDED_PROTO"
)
SECURE_PROXY_SSL_HEADER_VALUE = env.str("SECURE_PROXY_SSL_HEADER_VALUE", "https")
SECURE_PROXY_SSL_HEADER = (SECURE_PROXY_SSL_HEADER_NAME, SECURE_PROXY_SSL_HEADER_VALUE)

SECURE_REDIRECT_EXEMPT = env.list("DJANGO_SECURE_REDIRECT_EXEMPT", default=[])
SECURE_REFERRER_POLICY = env.str("DJANGO_SECURE_REFERRER_POLICY", default="same-origin")
SECURE_SSL_HOST = env.str("DJANGO_SECURE_SSL_HOST", default=None)
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=False)

# Chargebee
ENABLE_CHARGEBEE = env.bool("ENABLE_CHARGEBEE", default=False)
CHARGEBEE_API_KEY = env("CHARGEBEE_API_KEY", default=None)
CHARGEBEE_SITE = env("CHARGEBEE_SITE", default=None)

# Logging configuration
LOGGING_CONFIGURATION_FILE = env.str("LOGGING_CONFIGURATION_FILE", default=None)
if LOGGING_CONFIGURATION_FILE:
    with open(LOGGING_CONFIGURATION_FILE, "r") as f:
        LOGGING = json.loads(f.read())
else:
    LOG_LEVEL = env.str("LOG_LEVEL", default="WARNING")
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "generic": {"format": "%(name)-12s %(levelname)-8s %(message)s"},
        },
        "handlers": {
            "console": {
                "level": LOG_LEVEL,
                "class": "logging.StreamHandler",
                "formatter": "generic",
            }
        },
        "loggers": {
            "": {"level": LOG_LEVEL, "handlers": ["console"]},
            # Not sure why the following loggers are necessary, but it doesn't seem to
            # write log messages for e.g. features.workflows.core.models without adding
            # them explicitly.
            # TODO: move all apps to a parent 'apps' directory and configure the logger
            #  for that dir
            "features": {
                "level": LOG_LEVEL,
                "handlers": ["console"],
                "propagate": False,
            },
            "task_processor": {
                "level": LOG_LEVEL,
                "handlers": ["console"],
                "propagate": False,
            },
            "app_analytics": {
                "level": LOG_LEVEL,
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }

if APPLICATION_INSIGHTS_CONNECTION_STRING:
    LOGGING["handlers"]["azure"] = {
        "level": "DEBUG",
        "class": "opencensus.ext.azure.log_exporter.AzureLogHandler",
        "connection_string": APPLICATION_INSIGHTS_CONNECTION_STRING,
    }

    LOGGING["loggers"][""]["handlers"].append("azure")

ENABLE_DB_LOGGING = env.bool("DJANGO_ENABLE_DB_LOGGING", default=False)
if ENABLE_DB_LOGGING:
    LOGGING["loggers"]["django.db.backends"] = {
        "level": "DEBUG",
        "handlers": ["console"],
    }

CACHE_FLAGS_SECONDS = env.int("CACHE_FLAGS_SECONDS", default=0)
FLAGS_CACHE_LOCATION = "environment-flags"
CHARGEBEE_CACHE_LOCATION = "chargebee-objects"

ENVIRONMENT_CACHE_SECONDS = env.int("ENVIRONMENT_CACHE_SECONDS", default=60)
ENVIRONMENT_CACHE_BACKEND = env.str(
    "ENVIRONMENT_CACHE_BACKEND",
    default="django.core.cache.backends.locmem.LocMemCache",
)
ENVIRONMENT_CACHE_NAME = "environment-objects"
ENVIRONMENT_CACHE_LOCATION = env.str(
    "ENVIRONMENT_CACHE_LOCATION", default=ENVIRONMENT_CACHE_NAME
)

GET_FLAGS_ENDPOINT_CACHE_SECONDS = env.int(
    "GET_FLAGS_ENDPOINT_CACHE_SECONDS", default=0
)
GET_FLAGS_ENDPOINT_CACHE_NAME = "get_flags_endpoint_cache"
GET_FLAGS_ENDPOINT_CACHE_BACKEND = env.str(
    "GET_FLAGS_ENDPOINT_CACHE_BACKEND",
    default="django.core.cache.backends.dummy.DummyCache",
)
GET_FLAGS_ENDPOINT_CACHE_LOCATION = env.str(
    "GET_FLAGS_ENDPOINT_CACHE_LOCATION",
    default=GET_FLAGS_ENDPOINT_CACHE_NAME,
)

GET_IDENTITIES_ENDPOINT_CACHE_SECONDS = env.int(
    "GET_IDENTITIES_ENDPOINT_CACHE_SECONDS", default=0
)
GET_IDENTITIES_ENDPOINT_CACHE_NAME = "get_identities_endpoint_cache"
GET_IDENTITIES_ENDPOINT_CACHE_BACKEND = env.str(
    "GET_IDENTITIES_ENDPOINT_CACHE_BACKEND",
    default="django.core.cache.backends.dummy.DummyCache",
)
GET_IDENTITIES_ENDPOINT_CACHE_LOCATION = env.str(
    "GET_IDENTITIES_ENDPOINT_CACHE_LOCATION",
    default=GET_IDENTITIES_ENDPOINT_CACHE_NAME,
)

CACHE_PROJECT_SEGMENTS_SECONDS = env.int("CACHE_PROJECT_SEGMENTS_SECONDS", 0)
PROJECT_SEGMENTS_CACHE_LOCATION = "project-segments"

ENVIRONMENT_SEGMENTS_CACHE_NAME = "environment-segments"
ENVIRONMENT_SEGMENTS_CACHE_SECONDS = env.int("CACHE_ENVIRONMENT_SEGMENTS_SECONDS", 0)
ENVIRONMENT_SEGMENTS_CACHE_LOCATION = env(
    "ENVIRONMENT_SEGMENTS_CACHE_LOCATION", "environment-segments"
)
ENVIRONMENT_SEGMENTS_CACHE_BACKEND = env(
    "CACHE_ENVIRONMENT_SEGMENTS_BACKEND",
    "django.core.cache.backends.locmem.LocMemCache",
)

CACHE_ENVIRONMENT_DOCUMENT_SECONDS = env.int("CACHE_ENVIRONMENT_DOCUMENT_SECONDS", 0)
ENVIRONMENT_DOCUMENT_CACHE_LOCATION = "environment-documents"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    },
    ENVIRONMENT_CACHE_NAME: {
        "BACKEND": ENVIRONMENT_CACHE_BACKEND,
        "LOCATION": ENVIRONMENT_CACHE_LOCATION,
        "TIMEOUT": ENVIRONMENT_CACHE_SECONDS,
    },
    FLAGS_CACHE_LOCATION: {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": FLAGS_CACHE_LOCATION,
    },
    PROJECT_SEGMENTS_CACHE_LOCATION: {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": PROJECT_SEGMENTS_CACHE_LOCATION,
    },
    CHARGEBEE_CACHE_LOCATION: {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": CHARGEBEE_CACHE_LOCATION,
        "TIMEOUT": 12 * 60 * 60,  # 12 hours
    },
    ENVIRONMENT_DOCUMENT_CACHE_LOCATION: {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": ENVIRONMENT_DOCUMENT_CACHE_LOCATION,
        "timeout": CACHE_ENVIRONMENT_DOCUMENT_SECONDS,
    },
    GET_FLAGS_ENDPOINT_CACHE_NAME: {
        "BACKEND": GET_FLAGS_ENDPOINT_CACHE_BACKEND,
        "LOCATION": GET_FLAGS_ENDPOINT_CACHE_LOCATION,
    },
    GET_IDENTITIES_ENDPOINT_CACHE_NAME: {
        "BACKEND": GET_IDENTITIES_ENDPOINT_CACHE_BACKEND,
        "LOCATION": GET_IDENTITIES_ENDPOINT_CACHE_LOCATION,
    },
    ENVIRONMENT_SEGMENTS_CACHE_NAME: {
        "BACKEND": ENVIRONMENT_SEGMENTS_CACHE_BACKEND,
        "LOCATION": ENVIRONMENT_SEGMENTS_CACHE_LOCATION,
        "TIMEOUT": ENVIRONMENT_SEGMENTS_CACHE_SECONDS,
    },
}

TRENCH_AUTH = {
    "FROM_EMAIL": DEFAULT_FROM_EMAIL,
    "BACKUP_CODES_QUANTITY": 5,
    "BACKUP_CODES_LENGTH": 10,  # keep (quantity * length) under 200
    "BACKUP_CODES_CHARACTERS": (
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    ),
    "DEFAULT_VALIDITY_PERIOD": 30,
    "CONFIRM_BACKUP_CODES_REGENERATION_WITH_CODE": True,
    "APPLICATION_ISSUER_NAME": "app.bullet-train.io",
    "MFA_METHODS": {
        "app": {
            "VERBOSE_NAME": "TOTP App",
            "VALIDITY_PERIOD": 60 * 10,
            "USES_THIRD_PARTY_CLIENT": True,
            "HANDLER": "custom_auth.mfa.backends.application.CustomApplicationBackend",
        },
    },
}

USER_CREATE_PERMISSIONS = env.list(
    "USER_CREATE_PERMISSIONS", default=["rest_framework.permissions.AllowAny"]
)

DJOSER = {
    "PASSWORD_RESET_CONFIRM_URL": "password-reset/confirm/{uid}/{token}",
    # if True user required to click activation link in email to activate account
    "SEND_ACTIVATION_EMAIL": env.bool("ENABLE_EMAIL_ACTIVATION", default=False),
    # FE uri to redirect user to from activation email
    "ACTIVATION_URL": "activate/{uid}/{token}",
    # register or activation endpoint will send confirmation email to user
    "SEND_CONFIRMATION_EMAIL": False,
    "SERIALIZERS": {
        "token": "custom_auth.serializers.CustomTokenSerializer",
        "user_create": "custom_auth.serializers.CustomUserCreateSerializer",
        "current_user": "users.serializers.CustomCurrentUserSerializer",
    },
    "EMAIL": {
        "activation": "users.emails.ActivationEmail",
        "confirmation": "users.emails.ConfirmationEmail",
    },
    "SET_PASSWORD_RETYPE": True,
    "PASSWORD_RESET_CONFIRM_RETYPE": True,
    "HIDE_USERS": True,
    "PERMISSIONS": {
        "user": ["custom_auth.permissions.CurrentUser"],
        "user_list": ["custom_auth.permissions.CurrentUser"],
        "user_create": USER_CREATE_PERMISSIONS,
    },
}

# Github OAuth credentials
GITHUB_CLIENT_ID = env.str("GITHUB_CLIENT_ID", default="")
GITHUB_CLIENT_SECRET = env.str("GITHUB_CLIENT_SECRET", default="")

# Allow the configuration of registration via OAuth
ALLOW_REGISTRATION_WITHOUT_INVITE = env.bool(
    "ALLOW_REGISTRATION_WITHOUT_INVITE", default=True
)

# Django Axes settings
ENABLE_AXES = env.bool("ENABLE_AXES", default=True)
if ENABLE_AXES:
    # must be the first item in the auth backends
    AUTHENTICATION_BACKENDS.insert(0, "axes.backends.AxesBackend")

    # must be the last item in the middleware stack
    MIDDLEWARE.append("core.middleware.axes.AxesMiddleware")

    AXES_COOLOFF_TIME = timedelta(minutes=env.int("AXES_COOLOFF_TIME", 15))
    AXES_BLACKLISTED_URLS = [
        "/admin/login/?next=/admin",
        "/admin/",
    ]
    AXES_ONLY_USER_FAILURES = env.bool("AXES_ONLY_USER_FAILURES", True)
    AXES_FAILURE_LIMIT = env.int("AXES_FAILURE_LIMIT", 10)


# Sentry tracking
SENTRY_SDK_DSN = env("SENTRY_SDK_DSN", default=None)
DEFAULT_SENTRY_TRACE_SAMPLE_RATE = env.float("SENTRY_TRACE_SAMPLE_RATE", default=1.0)
DASHBOARD_ENDPOINTS_SENTRY_TRACE_SAMPLE_RATE = env.float(
    "DASHBOARD_ENDPOINTS_SENTRY_TRACE_SAMPLE_RATE", default=1.0
)
FORCE_SENTRY_TRACE_KEY = env("FORCE_SENTRY_TRACE_KEY", default=None)
if FORCE_SENTRY_TRACE_KEY:
    MIDDLEWARE.append("integrations.sentry.middleware.ForceSentryTraceMiddleware")

# allow users to access the admin console
ENABLE_ADMIN_ACCESS_USER_PASS = env.bool("ENABLE_ADMIN_ACCESS_USER_PASS", default=None)

# Set this flag to prevent traits being stored for all Organisations within the application
# Useful for data sensitive installations that dont want persistent traits.
DEFAULT_ORG_STORE_TRAITS_VALUE = env.bool("DEFAULT_ORG_STORE_TRAITS_VALUE", True)

# DynamoDB table name for storing environment
ENVIRONMENTS_TABLE_NAME_DYNAMO = env.str("ENVIRONMENTS_TABLE_NAME_DYNAMO", None)

# DynamoDB table name for storing identities
IDENTITIES_TABLE_NAME_DYNAMO = env.str("IDENTITIES_TABLE_NAME_DYNAMO", None)

# DynamoDB table name for storing environment api keys
ENVIRONMENTS_API_KEY_TABLE_NAME_DYNAMO = env.str(
    "ENVIRONMENTS_API_KEY_TABLE_NAME_DYNAMO", None
)

# DynamoDB table name for storing project metadata(currently only used for identity migration)
PROJECT_METADATA_TABLE_NAME_DYNAMO = env.str("PROJECT_METADATA_TABLE_NAME_DYNAMO", None)

# Front end environment variables
API_URL = env("API_URL", default="/api/v1/")
ASSET_URL = env("ASSET_URL", default="/")
MAINTENANCE_MODE = env.bool("MAINTENANCE_MODE", default=False)
PREVENT_SIGNUP = env.bool("PREVENT_SIGNUP", default=False)
PREVENT_EMAIL_PASSWORD = env.bool("PREVENT_EMAIL_PASSWORD", default=False)
DISABLE_ANALYTICS_FEATURES = env.bool("DISABLE_ANALYTICS_FEATURES", default=False)
DISABLE_INFLUXDB_FEATURES = env.bool("DISABLE_INFLUXDB_FEATURES", default=True)
FLAGSMITH_ANALYTICS = env.bool("FLAGSMITH_ANALYTICS", default=False)
FLAGSMITH_ON_FLAGSMITH_API_URL = env("FLAGSMITH_ON_FLAGSMITH_API_URL", default=None)
FLAGSMITH_ON_FLAGSMITH_API_KEY = env("FLAGSMITH_ON_FLAGSMITH_API_KEY", default=None)
GOOGLE_ANALYTICS_API_KEY = env("GOOGLE_ANALYTICS_API_KEY", default=None)
HEADWAY_API_KEY = env("HEADWAY_API_KEY", default=None)
LINKEDIN_API_KEY = env("LINKEDIN_API_KEY", default=None)
CRISP_CHAT_API_KEY = env("CRISP_CHAT_API_KEY", default=None)
MIXPANEL_API_KEY = env("MIXPANEL_API_KEY", default=None)
SENTRY_API_KEY = env("SENTRY_API_KEY", default=None)
AMPLITUDE_API_KEY = env("AMPLITUDE_API_KEY", default=None)
ENABLE_FLAGSMITH_REALTIME = env.bool("ENABLE_FLAGSMITH_REALTIME", default=False)

# Set this to enable create organisation for only superusers
RESTRICT_ORG_CREATE_TO_SUPERUSERS = env.bool("RESTRICT_ORG_CREATE_TO_SUPERUSERS", False)
# Slack Integration
SLACK_CLIENT_ID = env.str("SLACK_CLIENT_ID", default="")
SLACK_CLIENT_SECRET = env.str("SLACK_CLIENT_SECRET", default="")

# MailerLite
MAILERLITE_BASE_URL = env.str(
    "MAILERLITE_BASE_URL", default="https://api.mailerlite.com/api/v2/"
)
MAILERLITE_API_KEY = env.str("MAILERLITE_API_KEY", None)
MAILERLITE_NEW_USER_GROUP_ID = env.int("MAILERLITE_NEW_USER_GROUP_ID", None)

# Additional functionality for using SAML in Flagsmith SaaS
SAML_MODULE_PATH = env("SAML_MODULE_PATH", os.path.join(BASE_DIR, "saml"))
SAML_INSTALLED = os.path.exists(SAML_MODULE_PATH)

if SAML_INSTALLED:
    SAML_REQUESTS_CACHE_LOCATION = "saml_requests_cache"
    CACHES[SAML_REQUESTS_CACHE_LOCATION] = {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": SAML_REQUESTS_CACHE_LOCATION,
    }
    INSTALLED_APPS.append("saml")
    SAML_ACCEPTED_TIME_DIFF = env.int("SAML_ACCEPTED_TIME_DIFF", default=60)
    DJOSER["SERIALIZERS"]["current_user"] = "saml.serializers.SamlCurrentUserSerializer"


# Additional functionality needed for using workflows in Flagsmith SaaS
# python module path to the workflows logic module, e.g. "path.to.workflows"
WORKFLOWS_LOGIC_MODULE_PATH = env(
    "WORKFLOWS_LOGIC_MODULE_PATH", "features.workflows.logic"
)
WORKFLOWS_LOGIC_INSTALLED = (
    importlib.util.find_spec(WORKFLOWS_LOGIC_MODULE_PATH) is not None
)

if WORKFLOWS_LOGIC_INSTALLED:
    INSTALLED_APPS.append(WORKFLOWS_LOGIC_MODULE_PATH)

# Additional functionality for restricting authentication to a set of authentication methods in Flagsmith SaaS
AUTH_CONTROLLER_INSTALLED = importlib.util.find_spec("auth_controller") is not None
if AUTH_CONTROLLER_INSTALLED:
    INSTALLED_APPS.append("auth_controller")
    AUTHENTICATION_BACKENDS.insert(0, "auth_controller.backends.AuthControllerBackend")

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Used to keep edge identities in sync by forwarding the http requests
EDGE_API_URL = env.str("EDGE_API_URL", None)
# Used for signing forwarded request to edge
EDGE_REQUEST_SIGNING_KEY = env.str("EDGE_REQUEST_SIGNING_KEY", None)

# Aws Event bus used for sending identity migration events
IDENTITY_MIGRATION_EVENT_BUS_NAME = env.str("IDENTITY_MIGRATION_EVENT_BUS_NAME", None)

# Should be a string representing a timezone aware datetime, e.g. 2022-03-31T12:35:00Z
EDGE_RELEASE_DATETIME = env.datetime("EDGE_RELEASE_DATETIME", None)
# Note: using django.utils.timezone.now doesn't work reliably in settings so we use
# datetime.now
EDGE_ENABLED = (
    ENVIRONMENTS_TABLE_NAME_DYNAMO is not None
    and EDGE_RELEASE_DATETIME is not None
    and EDGE_RELEASE_DATETIME < datetime.now(tz=pytz.UTC)
)

DISABLE_WEBHOOKS = env.bool("DISABLE_WEBHOOKS", False)

SERVE_FE_ASSETS = os.path.exists(BASE_DIR + "/app/templates/webpack/index.html")

# Used to configure the number of application proxies that the API runs behind
NUM_PROXIES = env.int("NUM_PROXIES", 1)

SAML_USE_NAME_ID_AS_EMAIL = env.bool("SAML_USE_NAME_ID_AS_EMAIL", False)

# Used to control the size(number of identities) of the project that can be self migrated to edge
MAX_SELF_MIGRATABLE_IDENTITIES = env.int("MAX_SELF_MIGRATABLE_IDENTITIES", 100000)

# Setting to allow asynchronous tasks to be run synchronously for testing purposes
# or in a separate thread for self-hosted users
TASK_RUN_METHOD = env.enum(
    "TASK_RUN_METHOD", type=TaskRunMethod, default=TaskRunMethod.SEPARATE_THREAD.value
)
ENABLE_TASK_PROCESSOR_HEALTH_CHECK = env.bool(
    "ENABLE_TASK_PROCESSOR_HEALTH_CHECK", default=False
)

# Real time(server sent events) settings
SSE_SERVER_BASE_URL = env.str("SSE_SERVER_BASE_URL", None)
SSE_AUTHENTICATION_TOKEN = env.str("SSE_AUTHENTICATION_TOKEN", None)

DISABLE_INVITE_LINKS = env.bool("DISABLE_INVITE_LINKS", False)

# use a separate boolean setting so that we add it to the API containers in environments
# where we're running the task processor, so we avoid creating unnecessary tasks
ENABLE_PIPEDRIVE_LEAD_TRACKING = env.bool("ENABLE_PIPEDRIVE_LEAD_TRACKING", False)
PIPEDRIVE_API_TOKEN = env.str("PIPEDRIVE_API_TOKEN", None)
PIPEDRIVE_BASE_API_URL = env.str(
    "PIPEDRIVE_BASE_API_URL", "https://flagsmith.pipedrive.com/api/v1"
)
PIPEDRIVE_DOMAIN_ORGANIZATION_FIELD_KEY = env.str(
    "PIPEDRIVE_DOMAIN_ORGANIZATION_FIELD_KEY", None
)
PIPEDRIVE_SIGN_UP_TYPE_DEAL_FIELD_KEY = env.str(
    "PIPEDRIVE_SIGN_UP_TYPE_DEAL_FIELD_KEY", None
)
PIPEDRIVE_API_LEAD_SOURCE_DEAL_FIELD_KEY = env.str(
    "PIPEDRIVE_API_LEAD_SOURCE_DEAL_FIELD_KEY", None
)
PIPEDRIVE_API_LEAD_SOURCE_VALUE = env.str(
    "PIPEDRIVE_API_LEAD_SOURCE_VALUE", "App Sign-up"
)
PIPEDRIVE_IGNORE_DOMAINS = env.list("PIPEDRIVE_IGNORE_DOMAINS", [])
PIPEDRIVE_IGNORE_DOMAINS_REGEX = env("PIPEDRIVE_IGNORE_DOMAINS_REGEX", "")

# List of plan ids that support seat upgrades
AUTO_SEAT_UPGRADE_PLANS = env.list("AUTO_SEAT_UPGRADE_PLANS", default=[])


SKIP_MIGRATION_TESTS = env.bool("SKIP_MIGRATION_TESTS", False)

# prevent django-softdelete from performing whole table deletes!
SOFTDELETE_CASCADE_ALLOW_DELETE_ALL = False

# Used for serializing and deserializing GenericForeignKey(used in metadata) using the natural key of the object
SERIALIZATION_MODULES = {"json": "import_export.json_serializers_with_metadata_support"}

# Controls the app domain used in emails (currently invites and change requests).
# If set, domain stored with `django.contrib.sites` is disregarded.
DOMAIN_OVERRIDE = env.str("FLAGSMITH_DOMAIN", "")
# Used when no Django site is specified.
DEFAULT_DOMAIN = "app.flagsmith.com"
