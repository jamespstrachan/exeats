"""
Django settings for exeatsproject project.

Generated by 'django-admin startproject' using Django 2.0.5.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""

import os
import credentials

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = getattr(credentials, 'SECRET_KEY', 'xa4a3Pq#tKu*yAgH8X1xn&FT3NepT7Y9$tp%')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = getattr(credentials, 'DEBUG', False)

ALLOWED_HOSTS = getattr(credentials, 'ALLOWED_HOSTS', [])
BASE_URL =  getattr(credentials, 'BASE_URL', 'http://www.exeats.com')

# Application definition

INSTALLED_APPS = [
#    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
#    'django.contrib.messages',
#    'django.contrib.staticfiles',
    'exeatsapp',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
#    'django.contrib.auth.middleware.AuthenticationMiddleware',
#    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'exeatsproject.urls'

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

WSGI_APPLICATION = 'exeatsproject.wsgi.application'

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_HTTPONLY = True

# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases

if getattr(credentials, 'DB_USERNAME', False):
    DATABASES = {
        'default': {
            'ENGINE':  'django.db.backends.postgresql_psycopg2',
            'NAME':     credentials.DB_NAME,
            'USER':     credentials.DB_USERNAME,
            'PASSWORD': credentials.DB_PASSWORD,
            'HOST':     credentials.DB_HOST,
            'PORT':     credentials.DB_PORT,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }


# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/2.0/topics/i18n/
LANGUAGE_CODE = 'en-gb'
TIME_ZONE = 'Europe/London'
USE_TZ = True
USE_I18N = False
USE_L10N = False

DATE_FORMAT           = "D jS M Y"
DATETIME_FORMAT       = "H:i:s \o\\n D jS M Y"
SHORT_DATE_FORMAT     = "j M Y"
SHORT_DATETIME_FORMAT = "H:i D j M Y"


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

STATIC_URL = '/static/'

# todo - consider re-implementing Tutor as base auth model
#AUTH_USER_MODEL = 'exeatsapp.Tutor'

# Email via gmail smtp, cf: https://stackoverflow.com/a/23402208
EMAIL_HOST          = 'smtp.gmail.com'
EMAIL_HOST_USER     = credentials.EMAIL_HOST_USER
EMAIL_HOST_PASSWORD = credentials.EMAIL_HOST_PASSWORD
EMAIL_PORT          = 587
EMAIL_USE_TLS       = True

SYSTEM_FROM_EMAIL = 'exeatsystem@gmail.com'
SYSTEM_FROM_NAME  = 'Exeat System'
