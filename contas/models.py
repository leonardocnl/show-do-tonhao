from django.contrib.auth.models import AbstractUser
from django.db import models

from .perfis import EDITORES


class Usuario(AbstractUser):
    """Usuário do sistema. O perfil (Jogador, Editor, Administrador) vem dos grupos."""

    apelido = models.CharField(
        "apelido",
        max_length=30,
        blank=True,
        help_text="Nome exibido no ranking. Se vazio, usamos o nome de usuário.",
    )

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"

    @property
    def nome_exibicao(self):
        return self.apelido or self.get_full_name() or self.username

    @property
    def eh_editor(self):
        return self.is_superuser or self.groups.filter(name=EDITORES).exists()

    def __str__(self):
        return self.nome_exibicao
