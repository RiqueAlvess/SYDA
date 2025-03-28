import os
from pathlib import Path
from datetime import timedelta
import environ

# Inicialização do django-environ
env = environ.Env(
    # Valores padrão
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    SECRET_KEY=(str, None),
    SECURE_SSL_REDIRECT=(bool, True),
    SESSION_COOKIE_SECURE=(bool, True),
    CSRF_COOKIE_SECURE=(bool, True),
    SECURE_HSTS_SECONDS=(int, 31536000),
    SECURE_HSTS_INCLUDE_SUBDOMAINS=(bool, True),
    SECURE_HSTS_PRELOAD=(bool, True),
    CONN_MAX_AGE=(int, 60),
    CELERY_WORKER_CONCURRENCY=(int, 4),
)

# Ler arquivo .env (se existir)
environ.Env.read_env()

# =========================================================================
# CONFIGURAÇÕES DE BASE
# =========================================================================

# Caminhos
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"

# Aplicação
SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')
ROOT_URLCONF = "data_saas.urls"
WSGI_APPLICATION = "data_saas.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Aplicativos instalados
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
    "corsheaders",  # Novo: Gerenciamento de CORS
    "django_filters",  # Novo: Filtros para DRF
    "compressor",  # Novo: Compressão de assets
    
    # Apps internos
    "accounts",
    "clients",
    "api_config",
    "employees",
]

# Middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Novo: Para servir arquivos estáticos
    "corsheaders.middleware.CorsMiddleware",  # Novo: Gerenciamento de CORS
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",  # Novo: Suporte para internacionalização
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",  # Novo: Content Security Policy
]

# =========================================================================
# SEGURANÇA
# =========================================================================

# HTTPS e cookies seguros
SECURE_SSL_REDIRECT = env('SECURE_SSL_REDIRECT')
SESSION_COOKIE_SECURE = env('SESSION_COOKIE_SECURE')
CSRF_COOKIE_SECURE = env('CSRF_COOKIE_SECURE')
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "SAMEORIGIN"

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = env('SECURE_HSTS_SECONDS')
SECURE_HSTS_INCLUDE_SUBDOMAINS = env('SECURE_HSTS_INCLUDE_SUBDOMAINS')
SECURE_HSTS_PRELOAD = env('SECURE_HSTS_PRELOAD')

# Content Security Policy
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = (
    "'self'", 
    "https://cdn.jsdelivr.net", 
    "https://cdnjs.cloudflare.com",
    "https://cdn.plot.ly"
)
CSP_STYLE_SRC = (
    "'self'", 
    "https://cdn.jsdelivr.net", 
    "https://cdnjs.cloudflare.com", 
    "'unsafe-inline'"
)
CSP_FONT_SRC = ("'self'", "https://cdnjs.cloudflare.com")
CSP_IMG_SRC = ("'self'", "data:", "https://cdn.jsdelivr.net")

# CORS (Cross-Origin Resource Sharing)
CORS_ALLOWED_ORIGINS = [
    "https://yourdomain.com",
    # Adicione outros domínios permitidos conforme necessário
]
CORS_ALLOW_CREDENTIALS = True

# =========================================================================
# BASES DE DADOS E CACHE
# =========================================================================

# Configuração de Banco de Dados
DATABASES = {
    "default": {
        "ENGINE": env('DB_ENGINE'),
        "NAME": env('DB_NAME'),
        "USER": env('DB_USER'),
        "PASSWORD": env('DB_PASSWORD'),
        "HOST": env('DB_HOST'),
        "PORT": env('DB_PORT'),
        "CONN_MAX_AGE": env('CONN_MAX_AGE'),
        "OPTIONS": {
            "sslmode": "require",
            "connect_timeout": 10,
        },
        "ATOMIC_REQUESTS": True,  # Todas as requisições em uma transação
    }
}

# Cache
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env('REDIS_URL', default="redis://127.0.0.1:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "PARSER_CLASS": "redis.connection.HiredisParser",
        }
    }
}

# Sessões em cache e redis
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = 86400  # 24 horas
SESSION_COOKIE_NAME = "syda_sessionid"

# =========================================================================
# TEMPLATES E ARQUIVOS ESTÁTICOS
# =========================================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": False,  # Alterado para False para usar o loader cacheado
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            "loaders": [
                ("django.template.loaders.cached.Loader", [
                    "django.template.loaders.filesystem.Loader",
                    "django.template.loaders.app_directories.Loader",
                ]),
            ],
        },
    },
]

# Configuração para compressão de arquivos estáticos
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "compressor.finders.CompressorFinder",
]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

COMPRESS_ENABLED = True
COMPRESS_CSS_FILTERS = [
    "compressor.filters.css_default.CssAbsoluteFilter",
    "compressor.filters.cssmin.rCSSMinFilter",
]
COMPRESS_JS_FILTERS = ["compressor.filters.jsmin.JSMinFilter"]
COMPRESS_OFFLINE = True

# =========================================================================
# AUTENTICAÇÃO E PERMISSÕES
# =========================================================================

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "1000/minute",
    },
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

# JWT Settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
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

# Algoritmos de hash para senhas
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

# Validadores de senhas
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},  # Aumentado de 8 para 10
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "accounts.validators.SpecialCharacterValidator"},
]

# =========================================================================
# INTERNACIONALIZAÇÃO
# =========================================================================

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ("pt-br", "Português"),
    ("en", "English"),
]

LOCALE_PATHS = [os.path.join(BASE_DIR, "locale")]

# =========================================================================
# CELERY E TAREFAS ASSÍNCRONAS
# =========================================================================

CELERY_BROKER_URL = env('CELERY_BROKER_URL', default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "django-cache"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "America/Sao_Paulo"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutos
CELERY_WORKER_CONCURRENCY = env('CELERY_WORKER_CONCURRENCY')
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
CELERY_BROKER_CONNECTION_TIMEOUT = 10
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutos
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'visibility_timeout': 36000,  # 10 horas
    'max_retries': 3,
}

# =========================================================================
# LOGGING
# =========================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/syda.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'employees': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'api_config': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'accounts': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'clients': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# =========================================================================
# EMAIL
# =========================================================================

EMAIL_BACKEND = env('EMAIL_BACKEND', default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env('EMAIL_HOST', default="smtp.gmail.com")
EMAIL_PORT = env('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default="")
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default="")
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default="no-reply@syda.com.br")
SERVER_EMAIL = env('SERVER_EMAIL', default="server@syda.com.br")
ADMINS = [tuple(admins.split(':')) for admins in env.list('ADMINS', default=[])]

# =========================================================================
# CONFIGURAÇÕES ESPECÍFICAS DO SYDA
# =========================================================================

# Parâmetros de tempo máximo para API Sync
API_SYNC_TIMEOUT = env('API_SYNC_TIMEOUT', default=60)  # 60 segundos

# Constantes financeiras
MIN_WAGE_BRAZIL = env('MIN_WAGE_BRAZIL', default=1412.00)  # Salário mínimo 2024
AVG_WORK_HOURS_PER_MONTH = env('AVG_WORK_HOURS_PER_MONTH', default=176)  # 8 horas x 22 dias

# =========================================================================
# Verificação final
# =========================================================================

# Garantir que pasta de logs existe
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)

# Garantir chave secreta
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY não definida. Configure-a no ambiente ou no arquivo .env")

# Verificar configurações de ambiente
if DEBUG:
    # Aviso para depuração em produção
    import warnings
    warnings.warn(
        "\nAVISO: O Django está rodando em modo DEBUG em um ambiente de produção.\n"
        "Isso é perigoso! Defina DEBUG=False no ambiente de produção.",
        RuntimeWarning
    )