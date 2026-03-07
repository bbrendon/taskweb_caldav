import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-taskweb2-caldav-personal-tool-key-change-in-prod')

DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'django.contrib.sessions',
    'rest_framework',
    'corsheaders',
    'tasks',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'tasks.auth_middleware.RequireAuthMiddleware',
]

# Signed-cookie sessions — no database needed
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30  # 30 days

# Single-user app password
APP_PASSWORD = os.environ.get('APP_PASSWORD', 'changeme')

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {}

STATIC_URL = '/assets/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Whitenoise: serve the Vue SPA from the root URL (dist/ copied to spa/ at build time)
WHITENOISE_ROOT = BASE_DIR / 'spa'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS — allow Vue dev server
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]

CORS_ALLOW_ALL_ORIGINS = True  # personal tool, no auth needed

# DRF — no auth for personal tool
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# CalDAV server config
CALDAV_URL      = os.environ.get('CALDAV_URL',      'https://radicale.domain.com')
CALDAV_USERNAME = os.environ.get('CALDAV_USERNAME', 'theuser')
CALDAV_PASSWORD = os.environ.get('CALDAV_PASSWORD', 'whatpassword')
CALDAV_CALENDAR = os.environ.get('CALDAV_CALENDAR', 'Tasks')
