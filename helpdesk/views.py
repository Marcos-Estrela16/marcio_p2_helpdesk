import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Q

from core.utils import org_atual
from .models import Chamado, Categoria, Prioridade, Equipe, SLA
from .forms import ChamadoForm, ResolverChamadoForm, PeriodoForm
from .dashboard import obter_metricas_dashboard, filtrar_periodo_chamados


@login_required
def index(request):
    """
    Lista de chamados com busca textual e filtros combinados via Q() (Feature 1).
    Blindado com isolamento multi-tenant (Aula 14) e otimizado com select_related para evitar N+1 (Aula 17).
    """
    org = org_atual(request)
    chamados_qs = (
        Chamado.objects.filter(organizacao=org)
        .select_related("categoria", "prioridade", "categoria__equipe")
    )

    # Métricas da fila para a organização atual
    total_chamados = chamados_qs.count()
    abertos = chamados_qs.filter(status__in=["aberto", "em_atendimento"]).count()
    resolvidos = chamados_qs.filter(status="resolvido").count()
    agora = timezone.now()
    fora_prazo = chamados_qs.filter(
        Q(status__in=["aberto", "em_atendimento"], prazo_sla__lt=agora)
        | Q(status__in=["resolvido", "fechado"], data_resolucao__gt=Q(prazo_sla=agora))
    ).count()

    # Parâmetros de Busca e Filtro (Feature 1)
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    prioridade_id = request.GET.get("prioridade", "").strip()
    categoria_id = request.GET.get("categoria", "").strip()

    filtros = Q()
    if q:
        filtros &= (
            Q(titulo__icontains=q)
            | Q(descricao__icontains=q)
            | Q(protocolo__icontains=q)
            | Q(solicitante_nome__icontains=q)
        )

    if status:
        filtros &= Q(status=status)

    if prioridade_id:
        filtros &= Q(prioridade_id=prioridade_id)

    if categoria_id:
        filtros &= Q(categoria_id=categoria_id)

    chamados = chamados_qs.filter(filtros)
    total_filtrados = chamados.count()

    # Selects isolados por organização
    categorias = (
        Categoria.objects.filter(organizacao=org, ativa=True)
        .select_related("equipe")
        .order_by("nome")
    )
    prioridades = Prioridade.objects.all().order_by("peso")

    context = {
        "chamados": chamados,
        "total_chamados": total_chamados,
        "abertos": abertos,
        "resolvidos": resolvidos,
        "fora_prazo": fora_prazo,
        "total_filtrados": total_filtrados,
        "categorias": categorias,
        "prioridades": prioridades,
        "filtros_ativos": bool(q or status or prioridade_id or categoria_id),
        "organizacao_atual": org,
    }
    return render(request, "helpdesk/index.html", context)


@login_required
def novo_chamado(request):
    """
    Criação de novos chamados com isolamento multi-tenant (Aula 14, slide 13).
    A organização é injetada via request.user.perfil.organizacao, nunca via form.
    """
    org = org_atual(request)

    if request.method == "POST":
        form = ChamadoForm(request.POST, org=org)
        if form.is_valid():
            chamado = form.save(commit=False)
            chamado.organizacao = org
            chamado.save()
            prazo_str = (
                chamado.prazo_sla.strftime("%d/%m/%Y %H:%M")
                if chamado.prazo_sla
                else ""
            )
            messages.success(
                request,
                f"Chamado {chamado.protocolo} aberto com sucesso! Prazo de SLA calculado: {prazo_str}",
            )
            return redirect("detalhes_chamado", chamado_id=chamado.id)
    else:
        form = ChamadoForm(org=org)

    return render(
        request,
        "helpdesk/novo_chamado.html",
        {"form": form, "organizacao_atual": org},
    )


@login_required
def detalhes_chamado(request, chamado_id):
    """
    Detalhes e resolução de chamado.
    Protegido contra IDOR (Insecure Direct Object Reference) garantindo 404 para IDs alheios (Aula 14, slide 14).
    """
    org = org_atual(request)
    chamado = get_object_or_404(
        Chamado.objects.select_related("categoria", "prioridade", "categoria__equipe"),
        id=chamado_id,
        organizacao=org,
    )
    form_resolver = ResolverChamadoForm(instance=chamado)

    if request.method == "POST":
        form_resolver = ResolverChamadoForm(request.POST, instance=chamado)
        if form_resolver.is_valid():
            c = form_resolver.save(commit=False)
            if c.status in ["resolvido", "fechado"] and not c.data_resolucao:
                c.data_resolucao = timezone.now()
            c.save()
            messages.success(request, f"Chamado {c.protocolo} atualizado com sucesso!")
            return redirect("detalhes_chamado", chamado_id=c.id)

    context = {
        "chamado": chamado,
        "form_resolver": form_resolver,
        "organizacao_atual": org,
    }
    return render(request, "helpdesk/detalhes_chamado.html", context)


@login_required
def slas_info(request):
    """Exibição dos parâmetros de SLA e equipes da organização."""
    org = org_atual(request)
    slas = SLA.objects.select_related("prioridade").all()
    equipes = Equipe.objects.filter(organizacao=org).prefetch_related("categorias")
    return render(
        request,
        "helpdesk/slas_info.html",
        {"slas": slas, "equipes": equipes, "organizacao_atual": org},
    )


@login_required
def dashboard(request):
    """
    Dashboard de Gestão e Métricas com 4 formatos de métrica (Aula 17):
    - KPIs agregados (Total, Abertos, Resolvidos, Fora do Prazo)
    - Ranking (Top 5 categorias com mais chamados)
    - Série Temporal (Evolução mensal com TruncMonth)
    - Distribuição (Chamados por prioridade)
    Integrado com PeriodoForm para filtragem de período segura e Chart.js via json_script.
    """
    org = org_atual(request)
    metricas = obter_metricas_dashboard(request, org)

    # Serialização limpa para gráficos no template
    dados_mes = [
        {
            "mes": item["mes"].strftime("%m/%Y") if item["mes"] else "N/A",
            "total": item["total"],
        }
        for item in metricas["por_mes"]
    ]

    dados_prioridade = [
        {
            "prioridade": item["prioridade__nome"],
            "total": item["total"],
        }
        for item in metricas["por_prioridade"]
    ]

    contexto = {
        "kpis": metricas["kpis"],
        "ranking": metricas["ranking"],
        "dados_mes": dados_mes,
        "dados_prioridade": dados_prioridade,
        "form": metricas["form"],
        "organizacao_atual": org,
    }
    return render(request, "helpdesk/dashboard.html", contexto)


@login_required
def exportar_csv(request):
    """
    Exportação de chamados em formato CSV (Aula 17, slide 34).
    Aplica rigorosamente o isolamento por organização e o filtro de período validado.
    Evita o problema N+1 com select_related.
    """
    org = org_atual(request)
    qs = (
        Chamado.objects.filter(organizacao=org)
        .select_related("categoria", "prioridade", "categoria__equipe")
        .order_by("-data_abertura")
    )
    qs, form = filtrar_periodo_chamados(request, qs)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="relatorio_chamados.csv"'

    # UTF-8 BOM para garantir compatibilidade com Microsoft Excel
    response.write("\ufeff".encode("utf-8"))

    writer = csv.writer(response, delimiter=";")
    writer.writerow([
        "Protocolo",
        "Título",
        "Solicitante",
        "E-mail",
        "Categoria",
        "Equipe",
        "Prioridade",
        "Status",
        "Data Abertura",
        "Prazo SLA",
        "Data Resolução",
        "Dentro do Prazo",
    ])

    for c in qs:
        abertura_str = c.data_abertura.strftime("%d/%m/%Y %H:%M") if c.data_abertura else ""
        prazo_str = c.prazo_sla.strftime("%d/%m/%Y %H:%M") if c.prazo_sla else ""
        resolucao_str = c.data_resolucao.strftime("%d/%m/%Y %H:%M") if c.data_resolucao else ""
        dentro_prazo_str = "Sim" if c.dentro_do_prazo else "Não"

        writer.writerow([
            c.protocolo,
            c.titulo,
            c.solicitante_nome,
            c.solicitante_email,
            c.categoria.nome if c.categoria else "",
            c.categoria.equipe.nome if c.categoria and c.categoria.equipe else "",
            c.prioridade.nome if c.prioridade else "",
            c.get_status_display(),
            abertura_str,
            prazo_str,
            resolucao_str,
            dentro_prazo_str,
        ])

    return response
