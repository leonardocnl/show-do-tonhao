from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import UsuarioAlteracaoAdminForm, UsuarioCriacaoAdminForm
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    form = UsuarioAlteracaoAdminForm
    add_form = UsuarioCriacaoAdminForm

    list_display = ("username", "apelido", "email", "perfis", "is_staff", "is_active", "date_joined")
    list_filter = (
        "groups",
        "is_staff",
        "is_superuser",
        "is_active",
        ("date_joined", admin.DateFieldListFilter),
    )
    search_fields = ("username", "apelido", "email", "first_name", "last_name")
    ordering = ("-date_joined",)

    fieldsets = UserAdmin.fieldsets + (("Show do Tonhão", {"fields": ("apelido",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {"classes": ("wide",), "fields": ("apelido", "email")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("groups")

    @admin.display(description="perfis")
    def perfis(self, obj):
        nomes = [grupo.name for grupo in obj.groups.all()]
        if obj.is_superuser:
            nomes.insert(0, "Administrador")
        return ", ".join(nomes) or "—"
