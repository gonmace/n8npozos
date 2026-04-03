from pathlib import Path
from decouple import config
import mimetypes

mimetypes.add_type("text/css", ".css", True)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('DJANGO_SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dashboard',
    'audit',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database

if config('DJANGO_DB', default='') != '':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DJANGO_DB'),
            'USER': config('POSTGRES_USER', default='postgres'),
            'PASSWORD': config('POSTGRES_PASSWORD', default='postgres'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


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


# Internationalization

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/La_Paz'

USE_I18N = True

USE_TZ = True


# Static files

STATIC_URL = '/dashboard/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

if DEBUG:
    # Sin manifest ni hashing — whitenoise pasa el request a Django staticfiles
    # que lee directamente de STATICFILES_DIRS (dj/static/). Permite hot-reload de CSS.
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
else:
    # Producción: CSS minificado con hash para cache-busting permanente
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Sub-path: Django está detrás de nginx en /dashboard/
# En desarrollo local (DEBUG=True) se omite para no requerir nginx
if not DEBUG:
    FORCE_SCRIPT_NAME = '/dashboard'
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='https://n8npozos.magoreal.com').split(',')

# N8n Configuration
N8N_API_KEY = config('N8N_API_KEY', default='')
N8N_URL = config('N8N_URL', default='https://n8npozos.magoreal.com')
# Webhook alternativo para actualizar prompt_ajuste si la API REST no tiene acceso
N8N_WEBHOOK_UPDATE_AUDIT_PROMPT = config('N8N_WEBHOOK_UPDATE_AUDIT_PROMPT', default='')
# Workflow y nodo para actualizar el system prompt (Actualizar n8n)
N8N_WORKFLOW_PROMPT_ID = config('N8N_WORKFLOW_PROMPT_ID', default='wY2zlf23Ju6Yiiib')
N8N_NODE_NAME_PROMPT = config('N8N_NODE_NAME_PROMPT', default='')
# Webhook alternativo para actualizar el nodo si la API no tiene acceso
N8N_WEBHOOK_UPDATE_PROMPT_NODE = config('N8N_WEBHOOK_UPDATE_PROMPT_NODE', default='')
