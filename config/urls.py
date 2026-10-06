"""Rotas principais do projeto."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("painel/", admin.site.urls),
    path("contas/", include("contas.urls")),
    path("", include("quiz.urls")),
]
