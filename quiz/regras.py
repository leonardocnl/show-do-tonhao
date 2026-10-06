"""Regras puras do jogo (sem Django), fáceis de testar.

Escada de prêmios, valores de acertar/parar/errar e sorteio das ajudas.
"""
import random

PREMIOS = (
    1_000, 2_000, 3_000, 4_000, 5_000,
    10_000, 20_000, 30_000, 40_000, 50_000,
    100_000, 200_000, 300_000, 400_000, 500_000,
    1_000_000,
)
NIVEIS = len(PREMIOS)
PARADAS = (5, 10, 15)  # níveis cujo prêmio fica garantido mesmo errando
PERGUNTAS_POR_FAIXA = 4  # 4 perguntas por nível de dificuldade (4 faixas)


def valor_acertar(nivel):
    """Quanto o jogador ganha se acertar a pergunta do nível."""
    return PREMIOS[nivel - 1]


def valor_parar(nivel):
    """Quanto o jogador leva se parar antes de responder ao nível."""
    return PREMIOS[nivel - 2] if nivel > 1 else 0


def valor_errar(nivel):
    """Quanto o jogador leva se errar: o último patamar garantido já passado."""
    garantidos = [parada for parada in PARADAS if parada < nivel]
    return PREMIOS[max(garantidos) - 1] if garantidos else 0


def dificuldade_do_nivel(nivel):
    """Níveis 1-4 = fácil (1), 5-8 = média (2), 9-12 = difícil (3), 13-16 = muito difícil (4)."""
    return (nivel - 1) // PERGUNTAS_POR_FAIXA + 1


def formatar_reais(valor):
    """1000000 -> 'R$ 1.000.000'."""
    return "R$ " + f"{int(valor):,}".replace(",", ".")


def largura_degrau(nivel):
    """Largura (em %) do degrau: 55% no nível 1 até 100% no nível 16."""
    return round(55 + (nivel - 1) * 45 / (NIVEIS - 1))


def escada(nivel_atual):
    """Lista de degraus, do maior para o menor, pronta para o template."""
    degraus = []
    for nivel in range(NIVEIS, 0, -1):
        if nivel < nivel_atual:
            estado = "passado"
        elif nivel == nivel_atual:
            estado = "atual"
        else:
            estado = "futuro"

        if nivel == NIVEIS:
            rotulo = "Milhão"
        elif nivel in PARADAS:
            rotulo = "Garantido"
        else:
            rotulo = ""

        degraus.append(
            {
                "nivel": nivel,
                "valor": PREMIOS[nivel - 1],
                "largura": largura_degrau(nivel),
                "estado": estado,
                "parada": nivel in PARADAS,
                "topo": nivel == NIVEIS,
                "rotulo": rotulo,
            }
        )
    return degraus


# ---------------------------------------------------------------------------
# Ajudas
# ---------------------------------------------------------------------------
def sortear_cartas(ids_erradas, rng=random):
    """Cartas: elimina de 1 a 3 alternativas erradas."""
    if not ids_erradas:
        return []
    quantidade = rng.randint(1, min(3, len(ids_erradas)))
    return rng.sample(list(ids_erradas), quantidade)


def votos_placas(ids_disponiveis, id_correta, nivel, rng=random):
    """Placas: percentual de votos da plateia por alternativa (soma 100).

    A plateia acerta menos à medida que o nível sobe.
    """
    ids = list(ids_disponiveis)
    if id_correta not in ids:
        raise ValueError("A alternativa correta precisa estar entre as disponíveis.")

    outros = [i for i in ids if i != id_correta]
    if not outros:
        return {id_correta: 100}

    teto = max(40, 88 - nivel * 2)
    certa = rng.randint(max(30, teto - 12), teto)

    pesos = [rng.random() + 0.15 for _ in outros]
    total = sum(pesos)
    resto = 100 - certa
    parcelas = [int(resto * peso / total) for peso in pesos]
    parcelas[0] += resto - sum(parcelas)

    votos = {id_correta: certa}
    votos.update(dict(zip(outros, parcelas)))
    return votos
