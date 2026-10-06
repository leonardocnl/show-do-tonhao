"""Carrega categorias e perguntas de exemplo.

Uso:
    python manage.py seed_quiz            # categorias, perguntas e perfis
    python manage.py seed_quiz --demo     # também cria usuários de demonstração (só para desenvolvimento)
"""
import random

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from contas.perfis import EDITORES, JOGADORES
from quiz.apps import criar_perfis
from quiz.models import Alternativa, Categoria, Pergunta
from quiz.seed_data import CATEGORIAS, PERGUNTAS

SENHA_DEMO = "tonhao-demo-123"


class Command(BaseCommand):
    help = "Cria categorias e perguntas de exemplo (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--demo",
            action="store_true",
            help="Cria os usuários jogador_demo e editor_demo (apenas para desenvolvimento).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        criar_perfis(sender=None)

        categorias = {}
        for nome, slug, descricao, ordem in CATEGORIAS:
            categoria, _ = Categoria.objects.get_or_create(
                slug=slug, defaults={"nome": nome, "descricao": descricao, "ordem": ordem}
            )
            categorias[slug] = categoria

        criadas = 0
        for slug, perguntas in PERGUNTAS.items():
            for dificuldade, enunciado, correta, erradas, dica in perguntas:
                pergunta, nova = Pergunta.objects.get_or_create(
                    enunciado=enunciado,
                    defaults={
                        "categoria": categorias[slug],
                        "dificuldade": dificuldade,
                        "dica": dica,
                    },
                )
                if not nova:
                    continue
                criadas += 1
                opcoes = [(correta, True)] + [(texto, False) for texto in erradas]
                random.Random(enunciado).shuffle(opcoes)  # mesma ordem em qualquer máquina
                Alternativa.objects.bulk_create(
                    [
                        Alternativa(pergunta=pergunta, texto=texto, correta=certa, ordem=posicao)
                        for posicao, (texto, certa) in enumerate(opcoes)
                    ]
                )

        self.stdout.write(self.style.SUCCESS(f"{criadas} perguntas novas, {Pergunta.objects.count()} no total."))

        if options["demo"]:
            self._criar_usuarios_demo()

    def _criar_usuarios_demo(self):
        Usuario = get_user_model()
        for username, apelido, grupo in (
            ("jogador_demo", "Jogador Demo", JOGADORES),
            ("editor_demo", "Editor Demo", EDITORES),
        ):
            usuario, nova = Usuario.objects.get_or_create(username=username, defaults={"apelido": apelido})
            if nova:
                usuario.set_password(SENHA_DEMO)
                usuario.save()
            usuario.groups.add(Group.objects.get(name=grupo))
        self.stdout.write(
            self.style.WARNING(
                f"Usuários demo: jogador_demo e editor_demo (senha {SENHA_DEMO}). Não use em produção."
            )
        )
