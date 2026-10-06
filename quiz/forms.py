from django import forms
from django.core.exceptions import ValidationError

from contas.forms import EstiloTailwindMixin

from .models import Alternativa, Categoria, Pergunta


class PerguntaForm(EstiloTailwindMixin, forms.ModelForm):
    class Meta:
        model = Pergunta
        fields = ["categoria", "dificuldade", "enunciado", "dica", "ativa"]
        widgets = {"enunciado": forms.Textarea(attrs={"rows": 6})}


class AlternativaForm(EstiloTailwindMixin, forms.ModelForm):
    class Meta:
        model = Alternativa
        fields = ["texto", "correta"]


class BaseAlternativaFormSet(forms.BaseInlineFormSet):
    """Exige exatamente 4 alternativas, com exatamente 1 correta."""

    def clean(self):
        super().clean()
        if any(self.errors):
            return

        preenchidas = [
            form
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE", False)
        ]
        if len(preenchidas) != 4:
            raise ValidationError("Informe exatamente 4 alternativas.")
        corretas = sum(1 for form in preenchidas if form.cleaned_data.get("correta"))
        if corretas != 1:
            raise ValidationError("Marque exatamente uma alternativa como correta.")

        for posicao, form in enumerate(preenchidas):
            form.instance.ordem = posicao


AlternativaFormSet = forms.inlineformset_factory(
    Pergunta,
    Alternativa,
    form=AlternativaForm,
    formset=BaseAlternativaFormSet,
    extra=0,
    min_num=4,
    max_num=4,
    validate_min=True,
    validate_max=True,
    can_delete=False,
)


class FiltroPerguntasForm(EstiloTailwindMixin, forms.Form):
    q = forms.CharField(label="Buscar no enunciado", required=False)
    categoria = forms.ModelChoiceField(
        label="Categoria", queryset=Categoria.objects.all(), required=False, empty_label="Todas"
    )
    dificuldade = forms.ChoiceField(
        label="Dificuldade",
        required=False,
        choices=[("", "Todas")] + list(Pergunta.Dificuldade.choices),
    )
    situacao = forms.ChoiceField(
        label="Situação",
        required=False,
        choices=[("", "Todas"), ("ativas", "Ativas"), ("inativas", "Inativas")],
    )
