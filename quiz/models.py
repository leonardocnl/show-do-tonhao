from django.conf import settings
from django.db import models
from django.utils import timezone

from . import regras


class Categoria(models.Model):
    nome = models.CharField("nome", max_length=40, unique=True)
    slug = models.SlugField("slug", unique=True)
    descricao = models.CharField("descrição", max_length=200, blank=True)
    ordem = models.PositiveSmallIntegerField("ordem", default=0)
    ativa = models.BooleanField("ativa", default=True)

    class Meta:
        ordering = ["ordem", "nome"]
        verbose_name = "categoria"
        verbose_name_plural = "categorias"

    def __str__(self):
        return self.nome


class Pergunta(models.Model):
    class Dificuldade(models.IntegerChoices):
        FACIL = 1, "Fácil"
        MEDIA = 2, "Média"
        DIFICIL = 3, "Difícil"
        MUITO_DIFICIL = 4, "Muito difícil"

    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, related_name="perguntas", verbose_name="categoria"
    )
    enunciado = models.TextField("enunciado")
    dificuldade = models.PositiveSmallIntegerField(
        "dificuldade", choices=Dificuldade.choices, default=Dificuldade.FACIL
    )
    dica = models.CharField(
        "dica do Tonhão",
        max_length=300,
        blank=True,
        help_text="Aparece quando o jogador usa a ajuda 'Pergunte ao Tonhão'.",
    )
    ativa = models.BooleanField("ativa", default=True)
    criada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="perguntas_criadas",
        verbose_name="criada por",
    )
    criada_em = models.DateTimeField("criada em", auto_now_add=True)
    atualizada_em = models.DateTimeField("atualizada em", auto_now=True)

    class Meta:
        ordering = ["categoria__ordem", "dificuldade", "id"]
        verbose_name = "pergunta"
        verbose_name_plural = "perguntas"

    def __str__(self):
        return self.enunciado[:70]

    @property
    def enunciado_curto(self):
        return self.enunciado if len(self.enunciado) <= 80 else self.enunciado[:77] + "..."


class Alternativa(models.Model):
    pergunta = models.ForeignKey(
        Pergunta, on_delete=models.CASCADE, related_name="alternativas", verbose_name="pergunta"
    )
    texto = models.CharField("texto", max_length=200)
    correta = models.BooleanField("correta", default=False)
    ordem = models.PositiveSmallIntegerField("ordem", default=0)

    class Meta:
        ordering = ["ordem", "id"]
        verbose_name = "alternativa"
        verbose_name_plural = "alternativas"

    def __str__(self):
        return self.texto


class Partida(models.Model):
    class Status(models.TextChoices):
        ANDAMENTO = "andamento", "Em andamento"
        PAROU = "parou", "Parou"
        ERROU = "errou", "Errou"
        VENCEU = "venceu", "Venceu"
        ABANDONADA = "abandonada", "Abandonada"

    jogador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="partidas",
        verbose_name="jogador",
    )
    categoria = models.ForeignKey(
        Categoria,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="partidas",
        verbose_name="categoria",
        help_text="Vazio significa tema Geral (todas as categorias).",
    )
    status = models.CharField(
        "situação", max_length=12, choices=Status.choices, default=Status.ANDAMENTO, db_index=True
    )
    nivel_atual = models.PositiveSmallIntegerField("nível atual", default=1)
    premio_final = models.PositiveIntegerField("prêmio final", default=0)

    cartas = models.PositiveSmallIntegerField("cartas restantes", default=1)
    placas = models.PositiveSmallIntegerField("placas restantes", default=1)
    tonhao = models.PositiveSmallIntegerField("pergunte ao Tonhão restantes", default=1)
    pulos = models.PositiveSmallIntegerField("pulos restantes", default=3)

    iniciada_em = models.DateTimeField("iniciada em", auto_now_add=True)
    finalizada_em = models.DateTimeField("finalizada em", null=True, blank=True)

    class Meta:
        ordering = ["-iniciada_em"]
        verbose_name = "partida"
        verbose_name_plural = "partidas"

    def __str__(self):
        return f"Partida {self.pk} de {self.jogador}"

    @property
    def tema(self):
        return self.categoria.nome if self.categoria_id else "Geral"

    @property
    def tema_slug(self):
        return self.categoria.slug if self.categoria_id else "geral"

    @property
    def em_andamento(self):
        return self.status == self.Status.ANDAMENTO

    @property
    def duracao(self):
        return (self.finalizada_em or timezone.now()) - self.iniciada_em

    @property
    def premio_formatado(self):
        return regras.formatar_reais(self.premio_final)


class Rodada(models.Model):
    """Uma pergunta dentro de uma partida (uma por nível, 1 a 16)."""

    partida = models.ForeignKey(
        Partida, on_delete=models.CASCADE, related_name="rodadas", verbose_name="partida"
    )
    nivel = models.PositiveSmallIntegerField("nível")
    pergunta = models.ForeignKey(
        Pergunta, on_delete=models.PROTECT, related_name="rodadas", verbose_name="pergunta"
    )
    escolhida = models.ForeignKey(
        Alternativa,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="alternativa escolhida",
    )
    acertou = models.BooleanField("acertou", null=True, blank=True)
    eliminadas = models.JSONField("alternativas eliminadas (cartas)", default=list, blank=True)
    votos_placas = models.JSONField("votos das placas", default=dict, blank=True)
    dica_usada = models.BooleanField("dica do Tonhão usada", default=False)

    class Meta:
        ordering = ["partida_id", "nivel"]
        verbose_name = "rodada"
        verbose_name_plural = "rodadas"
        constraints = [
            models.UniqueConstraint(fields=["partida", "nivel"], name="uma_rodada_por_nivel"),
        ]

    def __str__(self):
        return f"Nível {self.nivel} da partida {self.partida_id}"
