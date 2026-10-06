from django import forms
from django.contrib.auth.forms import (
    AdminUserCreationForm,
    AuthenticationForm,
    UserChangeForm,
    UserCreationForm,
)
from django.contrib.auth.models import Group

from .models import Usuario
from .perfis import JOGADORES


class EstiloTailwindMixin:
    """Aplica as classes de componente (static/src/tailwind.css) aos widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            widget = campo.widget
            classe = "campo-check" if isinstance(widget, forms.CheckboxInput) else "campo"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {classe}".strip()


class LoginForm(EstiloTailwindMixin, AuthenticationForm):
    pass


class CadastroForm(EstiloTailwindMixin, UserCreationForm):
    """Cadastro público: todo novo usuário entra no grupo Jogadores."""

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ("username", "apelido", "email")

    def save(self, commit=True):
        usuario = super().save(commit=commit)
        if commit:
            grupo, _ = Group.objects.get_or_create(name=JOGADORES)
            usuario.groups.add(grupo)
        return usuario


# Formulários do admin: o modelo de usuário é customizado, então os formulários
# padrão (que apontam para auth.User) precisam ser redefinidos.
class UsuarioCriacaoAdminForm(AdminUserCreationForm):
    class Meta(AdminUserCreationForm.Meta):
        model = Usuario
        fields = ("username", "apelido", "email")


class UsuarioAlteracaoAdminForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = Usuario
