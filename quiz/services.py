"""Regras de negócio do jogo que dependem do banco de dados."""
import random

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from . import regras
from .models import Partida, Pergunta, Rodada

TEXTO_DICA_PADRAO = "Hmm... essa eu não lembro. Confie no seu instinto!"


class ErroDeJogo(Exception):
    """Erro de regra do jogo, com mensagem própria para o jogador."""


class PerguntasInsuficientes(ErroDeJogo):
    pass


class PartidaEncerrada(ErroDeJogo):
    pass


class AjudaIndisponivel(ErroDeJogo):
    pass


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------
def partida_em_andamento(usuario):
    return (
        Partida.objects.filter(jogador=usuario, status=Partida.Status.ANDAMENTO)
        .select_related("categoria")
        .first()
    )


def _perguntas_validas(categoria=None):
    """Perguntas ativas com exatamente 4 alternativas e 1 correta."""
    consulta = (
        Pergunta.objects.filter(ativa=True)
        .annotate(
            total_alternativas=Count("alternativas"),
            total_corretas=Count("alternativas", filter=Q(alternativas__correta=True)),
        )
        .filter(total_alternativas=4, total_corretas=1)
    )
    if categoria is not None:
        consulta = consulta.filter(categoria=categoria)
    return consulta


def obter_rodada_atual(partida):
    return (
        partida.rodadas.select_related("pergunta__categoria")
        .prefetch_related("pergunta__alternativas")
        .get(nivel=partida.nivel_atual)
    )


# ---------------------------------------------------------------------------
# Início da partida
# ---------------------------------------------------------------------------
def sortear_perguntas(categoria=None, rng=random):
    """Sorteia 16 perguntas, uma por nível, respeitando a dificuldade crescente."""
    disponiveis = list(_perguntas_validas(categoria))
    if len(disponiveis) < regras.NIVEIS:
        tema = categoria.nome if categoria else "Geral"
        raise PerguntasInsuficientes(
            f"O tema {tema} ainda não tem as {regras.NIVEIS} perguntas necessárias."
        )

    escolhidas = []
    for nivel in range(1, regras.NIVEIS + 1):
        faixa = regras.dificuldade_do_nivel(nivel)
        candidatas = [p for p in disponiveis if p.dificuldade == faixa]
        if not candidatas:
            # Sem perguntas na faixa: usa a faixa mais próxima.
            candidatas = sorted(disponiveis, key=lambda p: abs(p.dificuldade - faixa))
            menor = abs(candidatas[0].dificuldade - faixa)
            candidatas = [p for p in candidatas if abs(p.dificuldade - faixa) == menor]
        pergunta = rng.choice(candidatas)
        disponiveis.remove(pergunta)
        escolhidas.append(pergunta)
    return escolhidas


@transaction.atomic
def iniciar_partida(jogador, categoria=None, rng=random):
    perguntas = sortear_perguntas(categoria, rng)
    partida = Partida.objects.create(jogador=jogador, categoria=categoria)
    Rodada.objects.bulk_create(
        [
            Rodada(partida=partida, nivel=nivel, pergunta=pergunta)
            for nivel, pergunta in enumerate(perguntas, start=1)
        ]
    )
    return partida


# ---------------------------------------------------------------------------
# Andamento
# ---------------------------------------------------------------------------
def _exigir_em_andamento(partida):
    if partida.status != Partida.Status.ANDAMENTO:
        raise PartidaEncerrada("Esta partida já terminou.")


def _finalizar(partida, status, premio):
    partida.status = status
    partida.premio_final = premio
    partida.finalizada_em = timezone.now()
    partida.save(update_fields=["status", "premio_final", "finalizada_em", "nivel_atual"])


@transaction.atomic
def responder(partida, alternativa_id):
    """Registra a resposta, avança de nível ou encerra a partida."""
    _exigir_em_andamento(partida)
    rodada = obter_rodada_atual(partida)
    alternativa = next(
        (a for a in rodada.pergunta.alternativas.all() if a.pk == alternativa_id), None
    )
    if alternativa is None or alternativa.pk in rodada.eliminadas:
        raise ErroDeJogo("Escolha uma das alternativas disponíveis.")

    rodada.escolhida = alternativa
    rodada.acertou = alternativa.correta
    rodada.save(update_fields=["escolhida", "acertou"])

    if alternativa.correta:
        if partida.nivel_atual >= regras.NIVEIS:
            _finalizar(partida, Partida.Status.VENCEU, regras.PREMIOS[-1])
        else:
            partida.nivel_atual += 1
            partida.save(update_fields=["nivel_atual"])
    else:
        _finalizar(partida, Partida.Status.ERROU, regras.valor_errar(partida.nivel_atual))
    return rodada


@transaction.atomic
def parar(partida):
    _exigir_em_andamento(partida)
    _finalizar(partida, Partida.Status.PAROU, regras.valor_parar(partida.nivel_atual))


@transaction.atomic
def abandonar(partida):
    _exigir_em_andamento(partida)
    _finalizar(partida, Partida.Status.ABANDONADA, 0)


# ---------------------------------------------------------------------------
# Ajudas
# ---------------------------------------------------------------------------
@transaction.atomic
def usar_cartas(partida, rng=random):
    _exigir_em_andamento(partida)
    if partida.cartas <= 0:
        raise AjudaIndisponivel("Você já usou as cartas.")
    rodada = obter_rodada_atual(partida)
    if rodada.eliminadas:
        raise AjudaIndisponivel("As cartas já foram usadas nesta pergunta.")

    erradas = [a.pk for a in rodada.pergunta.alternativas.all() if not a.correta]
    rodada.eliminadas = regras.sortear_cartas(erradas, rng)
    rodada.save(update_fields=["eliminadas"])
    partida.cartas -= 1
    partida.save(update_fields=["cartas"])


@transaction.atomic
def usar_placas(partida, rng=random):
    _exigir_em_andamento(partida)
    if partida.placas <= 0:
        raise AjudaIndisponivel("Você já usou as placas.")
    rodada = obter_rodada_atual(partida)
    if rodada.votos_placas:
        raise AjudaIndisponivel("As placas já foram usadas nesta pergunta.")

    alternativas = rodada.pergunta.alternativas.all()
    disponiveis = [a.pk for a in alternativas if a.pk not in rodada.eliminadas]
    correta = next(a.pk for a in alternativas if a.correta)
    votos = regras.votos_placas(disponiveis, correta, partida.nivel_atual, rng)
    rodada.votos_placas = {str(pk): pct for pk, pct in votos.items()}
    rodada.save(update_fields=["votos_placas"])
    partida.placas -= 1
    partida.save(update_fields=["placas"])


@transaction.atomic
def usar_tonhao(partida):
    _exigir_em_andamento(partida)
    if partida.tonhao <= 0:
        raise AjudaIndisponivel("Você já pediu ajuda ao Tonhão.")
    rodada = obter_rodada_atual(partida)
    if rodada.dica_usada:
        raise AjudaIndisponivel("O Tonhão já deu a dica desta pergunta.")
    rodada.dica_usada = True
    rodada.save(update_fields=["dica_usada"])
    partida.tonhao -= 1
    partida.save(update_fields=["tonhao"])


@transaction.atomic
def pular(partida, rng=random):
    _exigir_em_andamento(partida)
    if partida.pulos <= 0:
        raise AjudaIndisponivel("Você não tem mais pulos.")
    rodada = obter_rodada_atual(partida)

    usadas = partida.rodadas.values_list("pergunta_id", flat=True)
    candidatas = list(_perguntas_validas(partida.categoria).exclude(pk__in=usadas))
    if not candidatas:
        raise PerguntasInsuficientes("Não há outra pergunta disponível para trocar.")

    faixa = rodada.pergunta.dificuldade
    mais_proximas = min(abs(p.dificuldade - faixa) for p in candidatas)
    nova = rng.choice([p for p in candidatas if abs(p.dificuldade - faixa) == mais_proximas])

    rodada.pergunta = nova
    rodada.eliminadas = []
    rodada.votos_placas = {}
    rodada.dica_usada = False
    rodada.save(update_fields=["pergunta", "eliminadas", "votos_placas", "dica_usada"])
    partida.pulos -= 1
    partida.save(update_fields=["pulos"])


AJUDAS = {
    "cartas": usar_cartas,
    "placas": usar_placas,
    "tonhao": usar_tonhao,
    "pular": pular,
}


# ---------------------------------------------------------------------------
# Contexto das telas
# ---------------------------------------------------------------------------
def contexto_jogo(partida):
    rodada = obter_rodada_atual(partida)
    pergunta = rodada.pergunta
    eliminadas = set(rodada.eliminadas)
    votos = {int(pk): pct for pk, pct in rodada.votos_placas.items()}

    alternativas = [
        {
            "letra": letra,
            "obj": alternativa,
            "eliminada": alternativa.pk in eliminadas,
            "percentual": votos.get(alternativa.pk),
        }
        for letra, alternativa in zip("ABCD", pergunta.alternativas.all())
    ]

    dica = None
    if rodada.dica_usada:
        dica = pergunta.dica or TEXTO_DICA_PADRAO

    ajudas = [
        {
            "slug": "cartas",
            "nome": "Cartas",
            "qtd": partida.cartas,
            "disponivel": partida.cartas > 0 and not rodada.eliminadas,
        },
        {
            "slug": "placas",
            "nome": "Placas",
            "qtd": partida.placas,
            "disponivel": partida.placas > 0 and not rodada.votos_placas,
        },
        {
            "slug": "tonhao",
            "nome": "Tonhão",
            "qtd": partida.tonhao,
            "disponivel": partida.tonhao > 0 and not rodada.dica_usada,
        },
        {
            "slug": "pular",
            "nome": "Pular",
            "qtd": partida.pulos,
            "disponivel": partida.pulos > 0,
        },
    ]

    nivel = partida.nivel_atual
    return {
        "partida": partida,
        "rodada": rodada,
        "pergunta": pergunta,
        "alternativas": alternativas,
        "dica": dica,
        "ajudas": ajudas,
        "escada": regras.escada(nivel),
        "total_niveis": regras.NIVEIS,
        "acertar": regras.valor_acertar(nivel),
        "parar": regras.valor_parar(nivel),
        "errar": regras.valor_errar(nivel),
    }
