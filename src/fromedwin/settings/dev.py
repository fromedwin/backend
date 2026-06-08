"""
Development settings for fromedwin project.
"""

from .base import *
from .timings import DEV;

# Override debug mode for development
DEBUG = True

# Allow local development without a .env file
if not SECRET_KEY:
    SECRET_KEY = 'django-insecure-local-dev-only'

# Development-specific allowed hosts
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', 'host.docker.internal']

# Development database (if not using environment variable)
if not DATABASE_URL:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR.parent.parent / 'data' / 'db.sqlite3',
        }
    }

# Development-specific email backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Development-specific static files
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Development-specific middleware (keep django_browser_reload for dev)
# This is already in base.py but we can override if needed

# Development-specific logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}

TIMINGS = DEV;

# Development-specific settings for faster development
CELERY_TASK_ALWAYS_EAGER = False  # Execute tasks synchronously in development
CELERY_TASK_EAGER_PROPAGATES = False 