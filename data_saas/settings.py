"""
settings.py - Configurações gerais do projeto Django (data_saas)
Refatorado para funcionar tanto localmente quanto no Render
"""

import os
from pathlib import Path
from datetime import timedelta
from decouple import config
import dj_database_url

# --------------------------------------------------------------
# Caminhos Básicos
# --------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------
# Segurança / Básico
# --------------------------------------------------------------
# Tenta buscar do .env primeiro, caso contrário busca das variáveis de ambiente
SECRET_KEY = config("SECRET_KEY", default=os.environ.get("SECRET_KEY"))

# Debug: False em produção, True em desenvolvimento
DEBUG = config("DEBUG", default=False, cast=bool)
if os.environ.get("RENDER"):
    DEBUG = False  # Sempre False no Render

# Hosts permitidos: local + Render
ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1,.onrender.com,*.render.com",
    cast=lambda v: [s.strip() for s in v.split(",") if s.strip()]
)

if os.environ.get("RENDER_EXTERNAL_HOSTNAME"):
    ALLOWED_HOSTS.append(os.environ.get("RENDER_EXTERNAL_HOSTNAME"))

# --------------------------------------------------------------
# Aplicativos Instalados
# --------------------------------------------------------------
INSTALLED_APPS = [
    # Apps Django nativos
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Apps de terceiros
    "rest_framework",
    "rest_framework_simplejwt",
    "django_celery_results",
    "corsheaders",
    "whitenoise.runserver_nostatic",  # Para servir estáticos no Render

    # Apps internos (locais)
    "accounts",
    "clients",
    "api_config",
    "employees",
]

# --------------------------------------------------------------
# Middleware
# --------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Adicionado para Render - DEVE estar logo após o SecurityMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # Para CORS
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "clients.middleware.ClientMiddleware",
]

# --------------------------------------------------------------
# URL Configuration
# --------------------------------------------------------------
ROOT_URLCONF = "data_saas.urls"

# --------------------------------------------------------------
# Templates
# --------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
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

# --------------------------------------------------------------
# WSGI
# --------------------------------------------------------------
WSGI_APPLICATION = "data_saas.wsgi.application"

# --------------------------------------------------------------
# Banco de Dados
# --------------------------------------------------------------
# Configuração para usar tanto .env local quanto DATABASE_URL no Render
DATABASES = {
    "default": {
        "ENGINE": config("DB_ENGINE", default="django.db.backends.postgresql"),
        "NAME": config("DB_NAME", default=""),
        "USER": config("DB_USER", default=""),
        "PASSWORD": config("DB_PASSWORD", default=""),
        "HOST": config("DB_HOST", default=""),
        "PORT": config("DB_PORT", default=""),
    }
}

# Se DATABASE_URL está disponível (como no Render), substitui a configuração acima
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES['default'] = dj_database_url.config(default=DATABASE_URL, conn_max_age=600)

# --------------------------------------------------------------
# Validação de Senha
# --------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "accounts.validators.SpecialCharacterValidator"},
]

# --------------------------------------------------------------
# Algoritmos de Hash para Senhas
# --------------------------------------------------------------
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

# --------------------------------------------------------------
# Internacionalização
# --------------------------------------------------------------
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------
# Arquivos Estáticos
# --------------------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# --------------------------------------------------------------
# Primary Key Field Type
# --------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------------
# Autenticação
# --------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# --------------------------------------------------------------
# Django REST Framework
# --------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

# --------------------------------------------------------------
# Simple JWT
# --------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
}

# --------------------------------------------------------------
# Configurações de Segurança
# --------------------------------------------------------------
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "SAMEORIGIN"

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 ano
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# --------------------------------------------------------------
# CORS Configuration
# --------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Em desenvolvimento permite todas as origens
if not DEBUG:  # Em produção especificar origens permitidas
    CORS_ALLOWED_ORIGINS = [
        "https://syda.onrender.com",  # Substitua pelo seu domínio
    ]
    if os.environ.get("RENDER_EXTERNAL_URL"):
        CORS_ALLOWED_ORIGINS.append(os.environ.get("RENDER_EXTERNAL_URL"))

# --------------------------------------------------------------
# Celery
# --------------------------------------------------------------
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")
# Usar o Redis do Render se disponível
if os.environ.get("REDIS_URL"):
    CELERY_BROKER_URL = os.environ.get("REDIS_URL")

CELERY_RESULT_BACKEND = "django-db"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "America/Sao_Paulo"

# --------------------------------------------------------------
# Logging
# --------------------------------------------------------------
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
         'level': 'INFO',  # Alterado para INFO em produção
    },
}
