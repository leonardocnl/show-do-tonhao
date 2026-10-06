from django.apps import AppConfig
from django.db.models.signals import post_migrate


def criar_perfis(sender, **kwargs):
    """Garante os grupos Jogadores e Editores e as permissões do grupo Editores."""
    from django.contrib.auth.models import Group, Permission

    from contas.perfis import EDITORES, JOGADORES

    Group.objects.get_or_create(name=JOGADORES)
    editores, _ = Group.objects.get_or_create(name=EDITORES)
    permissoes = Permission.objects.filter(
        content_type__app_label="quiz",
        content_type__model__in=["categoria", "pergunta", "alternativa"],
    )
    editores.permissions.add(*permissoes)


class QuizConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "quiz"
    verbose_name = "Quiz"

    def ready(self):
        post_migrate.connect(criar_perfis, sender=self)
