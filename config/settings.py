"""Configurações do projeto Show do Tonhão."""
import os
from pathlib import Path

from django.contrib.messages import constants as mensagens

BASE_DIR = Path(__file__).resolve().parent.parent

# Em produção, defina DJANGO_SECRET_KEY e DJANGO_DEBUG=0 no ambiente.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-key-troque-em-producao")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "jazzmin",  # precisa vir antes de django.contrib.admin
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # apps do projeto
    "contas",
    "quiz",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Banco relacional (SQLite no desenvolvimento).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_USER_MODEL = "contas.Usuario"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "contas:login"
LOGIN_REDIRECT_URL = "quiz:inicio"
LOGOUT_REDIRECT_URL = "quiz:inicio"

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# As mensagens do Django usam as classes de alerta definidas em static/src/tailwind.css.
MESSAGE_TAGS = {mensagens.ERROR: "danger"}

# ---------------------------------------------------------------------------
# Admin com tema Jazzmin (o template padrão do Django Admin não é aceito).
# ---------------------------------------------------------------------------
JAZZMIN_SETTINGS = {
    "site_title": "Show do Tonhão",
    "site_header": "Show do Tonhão",
    "site_brand": "tonhão",
    "welcome_sign": "Painel administrativo do Show do Tonhão",
    "copyright": "Show do Tonhão",
    "search_model": ["quiz.Pergunta", "contas.Usuario"],
    "topmenu_links": [
        {"name": "Painel", "url": "admin:index"},
        {"name": "Ver o jogo", "url": "quiz:inicio"},
        {"model": "quiz.Pergunta"},
    ],
    "usermenu_links": [{"name": "Ver o jogo", "url": "quiz:inicio"}],
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.Group": "fas fa-users",
        "contas.Usuario": "fas fa-user",
        "quiz.Categoria": "fas fa-tags",
        "quiz.Pergunta": "fas fa-question-circle",
        "quiz.Alternativa": "fas fa-list-ul",
        "quiz.Partida": "fas fa-gamepad",
        "quiz.Rodada": "fas fa-layer-group",
    },
    "order_with_respect_to": ["quiz", "contas", "auth"],
    "custom_css": "css/admin-tonhao.css",
    "show_ui_builder": False,
    "changeform_format": "horizontal_tabs",
    "related_modal_active": True,
}

JAZZMIN_UI_TWEAKS = {
    "theme": "flatly",
    "dark_mode_theme": "darkly",
    "navbar": "navbar-dark",
    "no_navbar_border": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_flat_style": True,
}
