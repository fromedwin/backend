"""
Base Django settings for fromedwin project.
Common settings shared across all environments.
"""
import os
from pathlib import Path
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Sentry configuration
if os.environ.get('SENTRY_DSN'):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_DSN'),
        environment=os.getenv('SENTRY_ENVIRONMENT', 'undefined'),
        integrations=[
            DjangoIntegration(),
        ],
    )

# Application version
VERSION = [0, 11, 0]

# SaaS mode
SAAS = os.environ.get('SAAS', '0') == '1'

# Security settings
SECRET_KEY = os.environ.get('SECRET_KEY')
FORCE_HTTPS = False
if os.environ.get('FORCE_HTTPS') == '1' or os.environ.get('FORCE_HTTPS', '').lower() == 'true':
    FORCE_HTTPS = True

# Debug mode
DEBUG = True if os.environ.get('DEBUG') == '1' else False

# Allowed hosts
ALLOWED_HOSTS = ['*']

# CSRF trusted origins
CSRF_TRUSTED_ORIGINS = [
    f'https://{os.environ.get("DOMAIN")}',
    f'https://*.{os.environ.get("DOMAIN")}',
    f'https://core.com',
    f'https://*.core.com',
]

# Domain and URL configuration
DOMAIN = os.environ.get('DOMAIN', 'localhost')
PORT = os.environ.get('PORT', 8000)
BACKEND_URL = os.environ.get('BACKEND_URL', f'http://{DOMAIN}:{PORT}')
WEBAUTH_USERNAME = os.environ.get('WEBAUTH_USERNAME')
WEBAUTH_PASSWORD = os.environ.get('WEBAUTH_PASSWORD')

# Service monitoring configuration
IS_SERVICE_DOWN_SCRAPE_INTERVAL_SECONDS = 60
IS_SERVICE_DOWN_TRIGGER_OUTRAGE_MINUTES = 5
IS_SERVICE_DOWN_TRIGGER_WARNING_MINUTES = 2

# Media files
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Upload size limit
DATA_UPLOAD_MAX_MEMORY_SIZE = 10*1024*1024  # 10MB instead of default 2.5MB

# S3 Storage configuration
if os.environ.get('STORAGE') == 'S3':
    AWS_S3_ENDPOINT_URL = os.getenv('AWS_S3_ENDPOINT_URL')
    S3_USE_SIGV4 = False
    AWS_S3_SIGNATURE_VERSION = "s3"
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
    AWS_DEFAULT_ACL = 'public-read'
    AWS_S3_CUSTOM_DOMAIN = os.getenv('AWS_S3_CUSTOM_DOMAIN')
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=3600'}
    AWS_S3_FILE_OVERWRITE = True
    STATIC_ROOT = os.path.join(BASE_DIR, 'collectstatic')
    STATICFILES_STORAGE = 'fromedwin.storage_backends.StaticStorage'
    STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
    DEFAULT_FILE_STORAGE = 'fromedwin.storage_backends.MediaStorage'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'

    if not AWS_S3_CUSTOM_DOMAIN:
        raise ValueError("AWS_S3_CUSTOM_DOMAIN must be set when using S3 storage")

# Django settings
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
USE_X_FORWARDED_HOST = True

# Tailwind settings
TAILWIND_APP_NAME = 'theme'
INTERNAL_IPS = [
    "127.0.0.1",
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.sitemaps',
    'rest_framework',
    'rest_framework.authtoken',
    'drf_spectacular',
    'api',
    'storages',
    'django_celery_beat',
    'django_cotton',
    # Tailwind
    'theme',
    'tailwind',
    'django_browser_reload',
    # App
    'availability',
    'incidents',
    'lighthouse',
    'logs',
    'favicons',
    'fromedwin',
    'notifications',
    'profile',
    'projects',
    'reports',
    'website',
    'status',
    'workers',
    # Statistics
    'django_prometheus',
    # Authentication
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.github',
    # Django cleanup needs to be last!
    'django_cleanup.apps.CleanupConfig',
]

MIDDLEWARE = (
    'allauth.account.middleware.AccountMiddleware',
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
    'profile.middleware.set_timezone',
    'django_browser_reload.middleware.BrowserReloadMiddleware',
)

ROOT_URLCONF = 'fromedwin.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'fromedwin.wsgi.application'

# Database configuration using environment variable DATABASES_URL
DATABASE_URL = os.environ.get('DATABASE_URL')
DATABASES = {}
if DATABASE_URL:
    DATABASES['default'] = dj_database_url.parse(DATABASE_URL, conn_max_age=600)
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django_prometheus.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Authentication backends
AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)

# Authentication settings
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'
ACCOUNT_EMAIL_VERIFICATION = 'none'

# Social account settings
SOCIALACCOUNT_AUTO_SIGNUP = True  # Auto-create user account without signup form
SOCIALACCOUNT_EMAIL_REQUIRED = False  # Don't require email from provider
SOCIALACCOUNT_QUERY_EMAIL = True  # Try to get email from provider if available

# Email settings
CONTACT_NAME = os.environ.get('CONTACT_NAME', 'FromEdwin')
CONTACT_EMAIL = os.environ.get('CONTACT_EMAIL', 'no-reply@core.com')
DEFAULT_FROM_EMAIL = CONTACT_EMAIL
EMAIL_HOST = os.environ.get('EMAIL_HOST')
EMAIL_PORT = os.environ.get('EMAIL_PORT')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS')

if os.environ.get('EMAIL_BACKEND_CONSOLE') == 'True' or not EMAIL_HOST:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Social authentication providers
SOCIALACCOUNT_PROVIDERS = {
    'github': {
        "APP": {
            "client_id": os.getenv("GITHUB_OAUTH_CLIENT_ID"),
            "secret": os.getenv("GITHUB_OAUTH_CLIENT_SECRET"),
            "key": ""
        },
        'SCOPE': [
            'user',
        ],
    }
}

# Heartbeat configuration
HEARTBEAT_INTERVAL = 10  # client will call server every HEARTBEAT_INTERVAL seconds

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True
SITE_ID = 1

# Freemium limits
FREEMIUM_PROJECTS = 3
FREEMIUM_AVAILABILITY = 1
FREEMIUM_PERFORMANCE = 3

# Celery settings
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'amqp://admin:admin@localhost')
CELERY_BROKER_UI_URL = os.getenv('CELERY_BROKER_UI_URL', 'http://localhost:15672')
CELERY_RESULT_BACKEND = 'rpc://'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Celery queues
CELERY_QUEUE = 'fromedwin_queue'
CELERY_QUEUE_LIGHTHOUSE = 'fromedwin_lighthouse_queue'

# InfluxDB settings
INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
INFLUXDB_UI_URL = os.getenv('INFLUXDB_UI_URL', 'http://localhost:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', 'fromedwin')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET', 'fromedwin')

INFLUXDB_URL_PROMETHEUS = INFLUXDB_URL
# If starts with http://localhost we replace with docker host
if INFLUXDB_URL_PROMETHEUS.startswith('http://localhost'):
    INFLUXDB_URL_PROMETHEUS = INFLUXDB_URL_PROMETHEUS.replace('http://localhost', 'http://host.docker.internal')

PROMETHEUS_UI_URL = os.getenv('PROMETHEUS_UI_URL', 'http://localhost:9090')
ALERTMANAGER_UI_URL = os.getenv('ALERTMANAGER_UI_URL', 'http://localhost:9093')
ALERTMANAGER_WEBHOOK_URL =os.getenv('ALERTMANAGER_WEBHOOK_URL', '')
if not ALERTMANAGER_WEBHOOK_URL:
    # Generate webhook URL used by alert manager yml file
    ALERTMANAGER_WEBHOOK_URL = ''
    if FORCE_HTTPS:
        ALERTMANAGER_WEBHOOK_URL += 'https://'
    else:
        ALERTMANAGER_WEBHOOK_URL += 'http://'

    if DOMAIN == 'localhost' or DOMAIN == None:
        ALERTMANAGER_WEBHOOK_URL += 'host.docker.internal'
    else:
        ALERTMANAGER_WEBHOOK_URL += DOMAIN

    if PORT and PORT != '80' and PORT != '443':
        ALERTMANAGER_WEBHOOK_URL += f':{PORT}'

ALERTMANAGER_WEBHOOK_URL += f'/alert/{SECRET_KEY}/'


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'api.permissions.IsApprovedUser',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'ALLOWED_VERSIONS': ['v1'],
    'DEFAULT_VERSION': 'v1',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'FromEdwin Monitor API',
    'DESCRIPTION': 'REST API for managing monitoring projects, availability, pages, incidents, and reports.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/v1/',
    'SERVE_PERMISSIONS': ['api.permissions.IsApprovedUser'],
    'SERVE_AUTHENTICATION': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
}

