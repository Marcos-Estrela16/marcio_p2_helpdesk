from django.db.models import Count, Q, F
from django.db.models.functions import TruncMonth
from django.utils import timezone
from .models import Chamado
from .forms import PeriodoForm

def filtrar_periodo_chamados(request, qs):
    """
    Filtra o queryset de chamados com base no PeriodoForm (Aula 17, slide 11).
    Valida os parâmetros 'inicio' e 'fim' da URL (request.GET) prevenindo erros 500.
    """
    form = PeriodoForm(request.GET or None)
    if form.is_valid():
        inicio = form.cleaned_data.get("inicio")
        fim = form.cleaned_data.get("fim")
        if inicio:
            qs = qs.filter(data_abertura__date__gte=inicio)
        if fim:
            qs = qs.filter(data_abertura__date__lte=fim)
    return qs, form


def obter_metricas_dashboard(request, org):
    """
    Calcula as 4 métricas de negócio para o Dashboard (Aula 17):
    1. KPIs com aggregate (Total, Abertos, Resolvidos, Fora do Prazo / SLA Estourado)
    2. Ranking com values + annotate + order_by (Top 5 categorias com mais chamados)
    3. Série Temporal com TruncMonth (Evolução de chamados abertos por mês)
    4. Distribuição por Prioridade (Fatias do todo)
    """
    agora = timezone.now()

    # Sempre partimos do queryset filtrado pela organização atual
    base = Chamado.objects.filter(organizacao=org)
    base, form = filtrar_periodo_chamados(request, base)

    # 1. KPIs Agregados em uma única query
    kpis = base.aggregate(
        total=Count("id"),
        abertos=Count("id", filter=Q(status__in=["aberto", "em_atendimento"])),
        resolvidos=Count("id", filter=Q(status__in=["resolvido", "fechado"])),
        fora_prazo=Count(
            "id",
            filter=(
                (Q(status__in=["aberto", "em_atendimento"]) & Q(prazo_sla__lt=agora))
                | (Q(status__in=["resolvido", "fechado"]) & Q(data_resolucao__gt=F("prazo_sla")))
            ),
        ),
    )

    # 2. Ranking: Top 5 Categorias
    ranking = (
        base.values("categoria__nome")
        .annotate(total=Count("id"))
        .order_by("-total")[:5]
    )

    # 3. Série Temporal: Chamados por mês
    por_mes = (
        base.annotate(mes=TruncMonth("data_abertura"))
        .values("mes")
        .annotate(total=Count("id"))
        .order_by("mes")
    )

    # 4. Distribuição: Chamados por Prioridade
    por_prioridade = (
        base.values("prioridade__nome", "prioridade__cor_badge")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    return {
        "kpis": kpis,
        "ranking": ranking,
        "por_mes": por_mes,
        "por_prioridade": por_prioridade,
        "form": form,
        "base_queryset": base,
    }
