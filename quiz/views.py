from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import DurationField, ExpressionWrapper, F, ProtectedError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from . import regras, services
from .forms import AlternativaFormSet, FiltroPerguntasForm, PerguntaForm
from .models import Categoria, Partida, Pergunta


# ---------------------------------------------------------------------------
# Início, jogo e resultado (área do jogador, protegida por login)
# ---------------------------------------------------------------------------
def inicio(request):
    partida = None
    if request.user.is_authenticated:
        partida = services.partida_em_andamento(request.user)
    contexto = {
        "categorias": Categoria.objects.filter(ativa=True),
        "partida_em_andamento": partida,
        "blocos": range(1, regras.NIVEIS + 1),
    }
    return render(request, "quiz/inicio.html", contexto)


@login_required
@require_POST
def iniciar(request):
    if services.partida_em_andamento(request.user):
        messages.info(request, "Você já tem uma partida em andamento. Continue de onde parou.")
        return redirect("quiz:jogo")

    tema = request.POST.get("tema", "geral")
    categoria = None
    if tema != "geral":
        categoria = get_object_or_404(Categoria, slug=tema, ativa=True)

    try:
        services.iniciar_partida(request.user, categoria)
    except services.ErroDeJogo as erro:
        messages.error(request, str(erro))
        return redirect("quiz:inicio")
    return redirect("quiz:jogo")


@login_required
def jogo(request):
    partida = services.partida_em_andamento(request.user)
    if partida is None:
        messages.info(request, "Escolha um tema e comece uma partida.")
        return redirect("quiz:inicio")
    return render(request, "quiz/jogo.html", services.contexto_jogo(partida))


@login_required
@require_POST
def responder(request):
    partida = services.partida_em_andamento(request.user)
    if partida is None:
        return redirect("quiz:inicio")

    try:
        alternativa_id = int(request.POST.get("alternativa", ""))
    except ValueError:
        messages.warning(request, "Escolha uma alternativa antes de confirmar.")
        return redirect("quiz:jogo")

    try:
        rodada = services.responder(partida, alternativa_id)
    except services.ErroDeJogo as erro:
        messages.error(request, str(erro))
        return redirect("quiz:jogo")

    partida.refresh_from_db()
    if partida.status != Partida.Status.ANDAMENTO:
        return redirect("quiz:resultado", pk=partida.pk)

    messages.success(
        request, f"Resposta certa! Você já tem {regras.formatar_reais(regras.valor_acertar(rodada.nivel))}."
    )
    return redirect("quiz:jogo")


@login_required
@require_POST
def ajuda(request, tipo):
    acao = services.AJUDAS.get(tipo)
    if acao is None:
        raise Http404("Ajuda desconhecida.")

    partida = services.partida_em_andamento(request.user)
    if partida is None:
        return redirect("quiz:inicio")

    try:
        acao(partida)
    except services.ErroDeJogo as erro:
        messages.error(request, str(erro))
    return redirect("quiz:jogo")


@login_required
@require_POST
def parar(request):
    partida = services.partida_em_andamento(request.user)
    if partida is None:
        return redirect("quiz:inicio")
    services.parar(partida)
    return redirect("quiz:resultado", pk=partida.pk)


@login_required
@require_POST
def abandonar(request):
    partida = services.partida_em_andamento(request.user)
    if partida is not None:
        services.abandonar(partida)
        messages.info(request, "Partida abandonada. Quando quiser, é só começar outra.")
    return redirect("quiz:inicio")


@login_required
def resultado(request, pk):
    partida = get_object_or_404(Partida.objects.select_related("categoria"), pk=pk, jogador=request.user)
    if partida.status == Partida.Status.ANDAMENTO:
        return redirect("quiz:jogo")
    if partida.status == Partida.Status.ABANDONADA:
        return redirect("quiz:historico")

    correta = None
    escolhida = None
    if partida.status != Partida.Status.VENCEU:
        rodada = partida.rodadas.select_related("pergunta", "escolhida").get(nivel=partida.nivel_atual)
        correta = rodada.pergunta.alternativas.filter(correta=True).first()
        escolhida = rodada.escolhida

    posicao_ranking = None
    if partida.status in [Partida.Status.PAROU, Partida.Status.ERROU, Partida.Status.VENCEU]:
        partidas_ranking = Partida.objects.filter(
            status__in=[Partida.Status.PAROU, Partida.Status.ERROU, Partida.Status.VENCEU]
        ).annotate(
            tempo_total=ExpressionWrapper(
                F("finalizada_em") - F("iniciada_em"), output_field=DurationField()
            )
        )
        if partida.categoria_id is None:
            partidas_ranking = partidas_ranking.filter(categoria__isnull=True)
        else:
            partidas_ranking = partidas_ranking.filter(categoria_id=partida.categoria_id)
        
        top_10 = list(partidas_ranking.order_by("-premio_final", "tempo_total")[:10])
        for i, p in enumerate(top_10, start=1):
            if p.pk == partida.pk:
                posicao_ranking = i
                break
                
    ajudas_usadas = 6 - (partida.cartas + partida.placas + partida.tonhao + partida.pulos)

    context = {
        "partida": partida, 
        "correta": correta, 
        "escolhida": escolhida,
        "posicao_ranking": posicao_ranking,
        "ajudas_usadas": ajudas_usadas,
    }
    return render(request, "quiz/resultado.html", context)


# ---------------------------------------------------------------------------
# Ranking e histórico
# ---------------------------------------------------------------------------
@login_required
def ranking(request):
    categorias = Categoria.objects.filter(ativa=True)
    tema = request.GET.get("tema", "")

    partidas = (
        Partida.objects.filter(
            status__in=[Partida.Status.PAROU, Partida.Status.ERROU, Partida.Status.VENCEU]
        )
        .select_related("jogador", "categoria")
        .annotate(
            tempo_total=ExpressionWrapper(
                F("finalizada_em") - F("iniciada_em"), output_field=DurationField()
            )
        )
    )
    if tema == "geral":
        partidas = partidas.filter(categoria__isnull=True)
    elif tema:
        partidas = partidas.filter(categoria__slug=tema)

    contexto = {
        "partidas": partidas.order_by("-premio_final", "tempo_total")[:10],
        "categorias": categorias,
        "tema": tema,
    }
    return render(request, "quiz/ranking.html", contexto)


@login_required
def historico(request):
    partidas = Partida.objects.filter(jogador=request.user).select_related("categoria")
    pagina = Paginator(partidas, 10).get_page(request.GET.get("page"))
    return render(request, "quiz/historico.html", {"pagina": pagina})


# ---------------------------------------------------------------------------
# Área do editor: CRUD de perguntas (exige permissões do grupo Editores)
# ---------------------------------------------------------------------------
class PermissaoMixin(PermissionRequiredMixin):
    """Anônimo vai para o login; logado sem permissão recebe 403."""

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied
        return super().handle_no_permission()


class PerguntaListView(PermissaoMixin, ListView):
    permission_required = "quiz.view_pergunta"
    model = Pergunta
    template_name = "quiz/pergunta_list.html"
    context_object_name = "perguntas"
    paginate_by = 12

    def get_queryset(self):
        consulta = Pergunta.objects.select_related("categoria").order_by("-atualizada_em")
        self.filtro = FiltroPerguntasForm(self.request.GET or None)
        if self.filtro.is_valid():
            dados = self.filtro.cleaned_data
            if dados["q"]:
                consulta = consulta.filter(enunciado__icontains=dados["q"])
            if dados["categoria"]:
                consulta = consulta.filter(categoria=dados["categoria"])
            if dados["dificuldade"]:
                consulta = consulta.filter(dificuldade=dados["dificuldade"])
            if dados["situacao"] == "ativas":
                consulta = consulta.filter(ativa=True)
            elif dados["situacao"] == "inativas":
                consulta = consulta.filter(ativa=False)
        return consulta

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        parametros = self.request.GET.copy()
        parametros.pop("page", None)
        contexto["filtro"] = self.filtro
        contexto["qs"] = parametros.urlencode()
        return contexto


class PerguntaFormMixin(PermissaoMixin):
    model = Pergunta
    form_class = PerguntaForm
    template_name = "quiz/pergunta_form.html"
    success_url = reverse_lazy("quiz:perguntas")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        if "formset" not in contexto:
            contexto["formset"] = AlternativaFormSet(
                self.request.POST or None, instance=self.object
            )
        return contexto

    def form_valid(self, form):
        pergunta = form.save(commit=False)
        formset = AlternativaFormSet(self.request.POST, instance=pergunta)
        if not formset.is_valid():
            return self.render_to_response(self.get_context_data(form=form, formset=formset))

        with transaction.atomic():
            if pergunta.pk is None:
                pergunta.criada_por = self.request.user
            pergunta.save()
            formset.instance = pergunta
            formset.save()
        self.object = pergunta
        messages.success(self.request, "Pergunta salva.")
        return redirect(self.success_url)


class PerguntaCreateView(PerguntaFormMixin, CreateView):
    permission_required = "quiz.add_pergunta"


class PerguntaUpdateView(PerguntaFormMixin, UpdateView):
    permission_required = "quiz.change_pergunta"


class PerguntaDeleteView(PermissaoMixin, DeleteView):
    permission_required = "quiz.delete_pergunta"
    model = Pergunta
    template_name = "quiz/pergunta_confirm_delete.html"
    success_url = reverse_lazy("quiz:perguntas")

    def form_valid(self, form):
        try:
            resposta = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                "Esta pergunta já foi usada em partidas e não pode ser excluída. Desative-a.",
            )
            return redirect(self.success_url)
        messages.success(self.request, "Pergunta excluída.")
        return resposta
