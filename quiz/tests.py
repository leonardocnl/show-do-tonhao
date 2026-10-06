import random

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import IntegrityError  # noqa: F401  (mantido para extensões futuras)
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from contas.perfis import EDITORES, JOGADORES

from . import regras, services
from .models import Alternativa, Categoria, Partida, Pergunta, Rodada

Usuario = get_user_model()


class RegrasTests(SimpleTestCase):
    def test_valores_do_nivel_7(self):
        self.assertEqual(regras.valor_acertar(7), 20_000)
        self.assertEqual(regras.valor_parar(7), 10_000)
        self.assertEqual(regras.valor_errar(7), 5_000)

    def test_primeiro_nivel_nao_tem_o_que_perder(self):
        self.assertEqual(regras.valor_parar(1), 0)
        self.assertEqual(regras.valor_errar(1), 0)

    def test_paradas_garantidas(self):
        self.assertEqual(regras.valor_errar(5), 0)
        self.assertEqual(regras.valor_errar(6), 5_000)
        self.assertEqual(regras.valor_errar(11), 50_000)
        self.assertEqual(regras.valor_errar(16), 500_000)

    def test_formatar_reais(self):
        self.assertEqual(regras.formatar_reais(1_000_000), "R$ 1.000.000")
        self.assertEqual(regras.formatar_reais(0), "R$ 0")

    def test_escada(self):
        escada = regras.escada(7)
        self.assertEqual(len(escada), 16)
        self.assertEqual(escada[0]["nivel"], 16)
        self.assertEqual({d["nivel"] for d in escada if d["parada"]}, {5, 10, 15})
        self.assertEqual(next(d for d in escada if d["nivel"] == 7)["estado"], "atual")

    def test_votos_das_placas_somam_100(self):
        rng = random.Random(3)
        for nivel in (1, 8, 16):
            votos = regras.votos_placas([1, 2, 3, 4], 1, nivel, rng)
            self.assertEqual(sum(votos.values()), 100)


class JogoBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_quiz", verbosity=0)
        cls.jogador = Usuario.objects.create_user("jogador", password="senha-forte-9876")
        cls.jogador.groups.add(*cls.jogador.groups.model.objects.filter(name=JOGADORES))

    def setUp(self):
        self.client.force_login(self.jogador)

    def alternativa(self, rodada, correta):
        return rodada.pergunta.alternativas.filter(correta=correta).first()


class PartidaServicoTests(JogoBase):
    def test_iniciar_cria_16_rodadas_com_dificuldade_crescente(self):
        partida = services.iniciar_partida(self.jogador)
        rodadas = list(partida.rodadas.select_related("pergunta"))
        self.assertEqual(len(rodadas), 16)
        faixas = [r.pergunta.dificuldade for r in rodadas]
        self.assertEqual(faixas, sorted(faixas))
        self.assertEqual(len({r.pergunta_id for r in rodadas}), 16)

    def test_tema_especifico_so_usa_a_categoria(self):
        categoria = Categoria.objects.get(slug="historia")
        partida = services.iniciar_partida(self.jogador, categoria)
        self.assertTrue(all(r.pergunta.categoria_id == categoria.id for r in partida.rodadas.all()))

    def test_acertar_avanca_de_nivel(self):
        partida = services.iniciar_partida(self.jogador)
        rodada = services.obter_rodada_atual(partida)
        services.responder(partida, self.alternativa(rodada, True).pk)
        partida.refresh_from_db()
        self.assertEqual(partida.nivel_atual, 2)
        self.assertEqual(partida.status, Partida.Status.ANDAMENTO)

    def test_errar_no_nivel_7_leva_o_patamar_garantido(self):
        partida = services.iniciar_partida(self.jogador)
        Partida.objects.filter(pk=partida.pk).update(nivel_atual=7)
        partida.refresh_from_db()
        rodada = services.obter_rodada_atual(partida)
        services.responder(partida, self.alternativa(rodada, False).pk)
        partida.refresh_from_db()
        self.assertEqual(partida.status, Partida.Status.ERROU)
        self.assertEqual(partida.premio_final, 5_000)
        self.assertIsNotNone(partida.finalizada_em)

    def test_parar_no_nivel_7_leva_o_valor_anterior(self):
        partida = services.iniciar_partida(self.jogador)
        Partida.objects.filter(pk=partida.pk).update(nivel_atual=7)
        partida.refresh_from_db()
        services.parar(partida)
        partida.refresh_from_db()
        self.assertEqual(partida.status, Partida.Status.PAROU)
        self.assertEqual(partida.premio_final, 10_000)

    def test_acertar_o_nivel_16_vence(self):
        partida = services.iniciar_partida(self.jogador)
        Partida.objects.filter(pk=partida.pk).update(nivel_atual=16)
        partida.refresh_from_db()
        rodada = services.obter_rodada_atual(partida)
        services.responder(partida, self.alternativa(rodada, True).pk)
        partida.refresh_from_db()
        self.assertEqual(partida.status, Partida.Status.VENCEU)
        self.assertEqual(partida.premio_final, 1_000_000)

    def test_partida_encerrada_nao_aceita_nova_resposta(self):
        partida = services.iniciar_partida(self.jogador)
        services.parar(partida)
        partida.refresh_from_db()
        with self.assertRaises(services.PartidaEncerrada):
            services.parar(partida)

    def test_cartas_eliminam_so_alternativas_erradas_e_gastam_a_ajuda(self):
        partida = services.iniciar_partida(self.jogador)
        services.usar_cartas(partida)
        partida.refresh_from_db()
        rodada = services.obter_rodada_atual(partida)
        self.assertGreaterEqual(len(rodada.eliminadas), 1)
        self.assertNotIn(self.alternativa(rodada, True).pk, rodada.eliminadas)
        self.assertEqual(partida.cartas, 0)
        with self.assertRaises(services.AjudaIndisponivel):
            services.usar_cartas(partida)

    def test_placas_somam_100(self):
        partida = services.iniciar_partida(self.jogador)
        services.usar_placas(partida)
        rodada = services.obter_rodada_atual(partida)
        self.assertEqual(sum(rodada.votos_placas.values()), 100)

    def test_pular_troca_a_pergunta_por_outra_ainda_nao_usada(self):
        partida = services.iniciar_partida(self.jogador)
        antes = services.obter_rodada_atual(partida).pergunta_id
        services.pular(partida)
        partida.refresh_from_db()
        depois = services.obter_rodada_atual(partida).pergunta_id
        self.assertNotEqual(antes, depois)
        self.assertEqual(partida.pulos, 2)
        self.assertEqual(partida.rodadas.values("pergunta_id").distinct().count(), 16)


class FluxoDeTelasTests(JogoBase):
    def test_inicio_e_publico(self):
        self.client.logout()
        resposta = self.client.get(reverse("quiz:inicio"))
        self.assertContains(resposta, "Você tem o que")
        self.assertContains(resposta, "Entrar para jogar")

    def test_jogar_cria_partida_e_mostra_a_pergunta(self):
        resposta = self.client.post(reverse("quiz:iniciar"), {"tema": "geral"})
        self.assertRedirects(resposta, reverse("quiz:jogo"))
        resposta = self.client.get(reverse("quiz:jogo"))
        self.assertContains(resposta, "Prêmios")
        self.assertContains(resposta, "R$ 1.000.000")
        self.assertContains(resposta, "Confirmar")

    def test_resposta_errada_leva_ao_resultado(self):
        self.client.post(reverse("quiz:iniciar"), {"tema": "geral"})
        partida = Partida.objects.get(jogador=self.jogador)
        rodada = services.obter_rodada_atual(partida)
        resposta = self.client.post(
            reverse("quiz:responder"), {"alternativa": self.alternativa(rodada, False).pk}
        )
        self.assertRedirects(resposta, reverse("quiz:resultado", args=[partida.pk]))
        resposta = self.client.get(reverse("quiz:resultado", args=[partida.pk]))
        self.assertContains(resposta, "Não foi dessa vez")
        self.assertContains(resposta, self.alternativa(rodada, True).texto)

    def test_ranking_ordena_por_premio(self):
        outro = Usuario.objects.create_user("outro", password="senha-forte-9876", apelido="Outro")
        Partida.objects.create(
            jogador=self.jogador, status=Partida.Status.PAROU, premio_final=10_000,
            finalizada_em=self.jogador.date_joined,
        )
        Partida.objects.create(
            jogador=outro, status=Partida.Status.VENCEU, premio_final=1_000_000,
            finalizada_em=self.jogador.date_joined,
        )
        resposta = self.client.get(reverse("quiz:ranking"))
        partidas = list(resposta.context["partidas"])
        self.assertEqual([p.premio_final for p in partidas], [1_000_000, 10_000])

    def test_historico_lista_apenas_partidas_do_usuario(self):
        outro = Usuario.objects.create_user("outro2", password="senha-forte-9876")
        Partida.objects.create(jogador=outro)
        Partida.objects.create(jogador=self.jogador)
        resposta = self.client.get(reverse("quiz:historico"))
        self.assertEqual(len(resposta.context["pagina"].object_list), 1)

    def test_posicao_ranking_na_tela_de_resultado(self):
        from django.utils import timezone
        outro = Usuario.objects.create_user("outro3", password="senha", apelido="Outro")
        agora = timezone.now()
        # Create 2 better games
        Partida.objects.create(jogador=outro, status=Partida.Status.VENCEU, premio_final=1_000_000, finalizada_em=agora)
        Partida.objects.create(jogador=outro, status=Partida.Status.PAROU, premio_final=500_000, finalizada_em=agora)
        # Create 1 worse game
        Partida.objects.create(jogador=outro, status=Partida.Status.ERROU, premio_final=50_000, finalizada_em=agora)
        
        partida = services.iniciar_partida(self.jogador)
        Partida.objects.filter(pk=partida.pk).update(status=Partida.Status.PAROU, premio_final=100_000, finalizada_em=agora)
        partida.refresh_from_db()
        resposta = self.client.get(reverse("quiz:resultado", args=[partida.pk]))
        self.assertEqual(resposta.context["posicao_ranking"], 3)
        self.assertContains(resposta, "Você ficou em 3º no ranking!")


class PerfisEPermissoesTests(JogoBase):
    def setUp(self):
        super().setUp()
        self.editor = Usuario.objects.create_user("editor", password="senha-forte-9876")
        self.editor.groups.add(*self.jogador.groups.model.objects.filter(name=EDITORES))

    def dados_pergunta(self, categoria):
        return {
            "categoria": categoria.pk,
            "dificuldade": 1,
            "enunciado": "Quanto é 2 + 2?",
            "dica": "Conte nos dedos.",
            "ativa": "on",
            "alternativas-TOTAL_FORMS": 4,
            "alternativas-INITIAL_FORMS": 0,
            "alternativas-MIN_NUM_FORMS": 4,
            "alternativas-MAX_NUM_FORMS": 4,
            "alternativas-0-texto": "3",
            "alternativas-1-texto": "4",
            "alternativas-1-correta": "on",
            "alternativas-2-texto": "5",
            "alternativas-3-texto": "22",
        }

    def test_jogador_nao_acessa_a_area_do_editor(self):
        resposta = self.client.get(reverse("quiz:perguntas"))
        self.assertEqual(resposta.status_code, 403)

    def test_anonimo_e_redirecionado_ao_login(self):
        self.client.logout()
        resposta = self.client.get(reverse("quiz:perguntas"))
        self.assertEqual(resposta.status_code, 302)

    def test_editor_cria_pergunta_com_4_alternativas(self):
        self.client.force_login(self.editor)
        categoria = Categoria.objects.first()
        resposta = self.client.post(reverse("quiz:pergunta_nova"), self.dados_pergunta(categoria))
        self.assertRedirects(resposta, reverse("quiz:perguntas"))
        pergunta = Pergunta.objects.get(enunciado="Quanto é 2 + 2?")
        self.assertEqual(pergunta.criada_por, self.editor)
        self.assertEqual(pergunta.alternativas.count(), 4)
        self.assertEqual(pergunta.alternativas.filter(correta=True).get().texto, "4")

    def test_pergunta_sem_alternativa_correta_e_rejeitada(self):
        self.client.force_login(self.editor)
        dados = self.dados_pergunta(Categoria.objects.first())
        del dados["alternativas-1-correta"]
        resposta = self.client.post(reverse("quiz:pergunta_nova"), dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(Pergunta.objects.filter(enunciado="Quanto é 2 + 2?").exists())

    def test_editor_exclui_pergunta_nao_usada(self):
        self.client.force_login(self.editor)
        pergunta = Pergunta.objects.create(
            categoria=Categoria.objects.first(), enunciado="Pergunta descartável"
        )
        resposta = self.client.post(reverse("quiz:pergunta_excluir", args=[pergunta.pk]))
        self.assertRedirects(resposta, reverse("quiz:perguntas"))
        self.assertFalse(Pergunta.objects.filter(pk=pergunta.pk).exists())

    def test_pergunta_ja_usada_em_partida_nao_e_excluida(self):
        self.client.force_login(self.editor)
        partida = services.iniciar_partida(self.jogador)
        usada = partida.rodadas.first().pergunta
        self.client.post(reverse("quiz:pergunta_excluir", args=[usada.pk]))
        self.assertTrue(Pergunta.objects.filter(pk=usada.pk).exists())

    def test_filtros_da_lista_de_perguntas(self):
        self.client.force_login(self.editor)
        resposta = self.client.get(reverse("quiz:perguntas"), {"categoria": Categoria.objects.get(slug="ciencias").pk})
        self.assertTrue(all(p.categoria.slug == "ciencias" for p in resposta.context["perguntas"]))
        self.assertTrue(len(resposta.context["perguntas"]) > 0)

    def test_grupos_foram_criados_com_as_permissoes(self):
        grupo = self.editor.groups.get(name=EDITORES)
        codigos = set(grupo.permissions.values_list("codename", flat=True))
        self.assertIn("add_pergunta", codigos)
        self.assertIn("delete_pergunta", codigos)
        self.assertEqual(self.jogador.groups.get(name=JOGADORES).permissions.count(), 0)

    def test_seed_e_idempotente(self):
        total = Pergunta.objects.count()
        call_command("seed_quiz", verbosity=0)
        self.assertEqual(Pergunta.objects.count(), total)
        self.assertEqual(Alternativa.objects.count(), total * 4)
        self.assertEqual(Rodada.objects.count(), 0)
