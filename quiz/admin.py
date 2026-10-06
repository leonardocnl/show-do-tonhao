from django.contrib import admin
from django.db.models import Count

from . import regras
from .forms import BaseAlternativaFormSet
from .models import Alternativa, Categoria, Partida, Pergunta, Rodada


class AlternativaInline(admin.TabularInline):
    model = Alternativa
    formset = BaseAlternativaFormSet
    fields = ("texto", "correta")
    extra = 0
    min_num = 4
    max_num = 4
    can_delete = False


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nome", "slug", "ordem", "ativa", "total_perguntas")
    list_editable = ("ordem", "ativa")
    list_filter = ("ativa",)
    search_fields = ("nome", "slug", "descricao")
    prepopulated_fields = {"slug": ("nome",)}

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_total=Count("perguntas"))

    @admin.display(description="perguntas", ordering="_total")
    def total_perguntas(self, obj):
        return obj._total


@admin.register(Pergunta)
class PerguntaAdmin(admin.ModelAdmin):
    list_display = ("enunciado_curto", "categoria", "dificuldade", "ativa", "criada_por", "criada_em")
    list_filter = (
        "categoria",
        "dificuldade",
        "ativa",
        ("criada_em", admin.DateFieldListFilter),
        "criada_por",
    )
    search_fields = ("enunciado", "dica", "alternativas__texto")
    list_select_related = ("categoria", "criada_por")
    readonly_fields = ("criada_por", "criada_em", "atualizada_em")
    inlines = [AlternativaInline]
    fieldsets = (
        (None, {"fields": ("categoria", "dificuldade", "enunciado", "dica", "ativa")}),
        ("Registro", {"fields": ("criada_por", "criada_em", "atualizada_em")}),
    )

    @admin.display(description="enunciado", ordering="enunciado")
    def enunciado_curto(self, obj):
        return obj.enunciado_curto

    def save_model(self, request, obj, form, change):
        if not change:
            obj.criada_por = request.user
        super().save_model(request, obj, form, change)


class RodadaInline(admin.TabularInline):
    model = Rodada
    fields = ("nivel", "pergunta", "escolhida", "acertou")
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Partida)
class PartidaAdmin(admin.ModelAdmin):
    list_display = ("id", "jogador", "tema", "status", "nivel_atual", "premio", "iniciada_em")
    list_filter = (
        "status",
        "categoria",
        ("iniciada_em", admin.DateFieldListFilter),
    )
    search_fields = ("jogador__username", "jogador__apelido")
    list_select_related = ("jogador", "categoria")
    date_hierarchy = "iniciada_em"
    readonly_fields = ("iniciada_em", "finalizada_em")
    inlines = [RodadaInline]

    @admin.display(description="tema", ordering="categoria__nome")
    def tema(self, obj):
        return obj.tema

    @admin.display(description="prêmio", ordering="premio_final")
    def premio(self, obj):
        return regras.formatar_reais(obj.premio_final)

    def has_add_permission(self, request):
        return False
