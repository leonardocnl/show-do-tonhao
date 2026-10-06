from django import template

from quiz.regras import formatar_reais

register = template.Library()


@register.filter
def reais(valor):
    """1000000 -> 'R$ 1.000.000'."""
    return formatar_reais(valor or 0)


@register.filter
def tempo(duracao):
    """timedelta -> 'mm:ss'."""
    if not duracao:
        return "--:--"
    minutos, segundos = divmod(int(duracao.total_seconds()), 60)
    return f"{minutos:02d}:{segundos:02d}"


@register.filter
def com_estado(field):
    """Adiciona aria-invalid, border-err e aria-describedby se houver erro ou ajuda."""
    attrs = {}
    described_by = []
    
    if field.errors:
        attrs["aria-invalid"] = "true"
        attrs["class"] = "border-err"
        described_by.append(f"{field.id_for_label}_error")
        
    if field.help_text:
        described_by.append(f"{field.id_for_label}_help")
        
    if described_by:
        attrs["aria-describedby"] = " ".join(described_by)
        
    return field.as_widget(attrs=attrs)
