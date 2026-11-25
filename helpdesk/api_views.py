from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from core.utils import org_atual
from .models import Chamado, Categoria, Prioridade
from .serializers import ChamadoSerializer, CategoriaSerializer, PrioridadeSerializer
from .dashboard import obter_metricas_dashboard, filtrar_periodo_chamados

class ChamadoListCreate(generics.ListCreateAPIView):
    serializer_class = ChamadoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        org = org_atual(self.request)
        if not org:
            return Chamado.objects.none()
        return (
            Chamado.objects.filter(organizacao=org)
            .select_related("categoria", "prioridade", "categoria__equipe")
            .order_by("-data_abertura")
        )

    def perform_create(self, serializer):
        org = org_atual(self.request)
        serializer.save(organizacao=org)


class ChamadoDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ChamadoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        org = org_atual(self.request)
        if not org:
            return Chamado.objects.none()
        return (
            Chamado.objects.filter(organizacao=org)
            .select_related("categoria", "prioridade", "categoria__equipe")
        )


class CategoriaListCreate(generics.ListCreateAPIView):
    serializer_class = CategoriaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        org = org_atual(self.request)
        if not org:
            return Categoria.objects.none()
        return Categoria.objects.filter(organizacao=org).select_related("equipe")

    def perform_create(self, serializer):
        org = org_atual(self.request)
        serializer.save(organizacao=org)


class PrioridadeList(generics.ListAPIView):
    serializer_class = PrioridadeSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Prioridade.objects.all().select_related("sla")


class DashboardApi(APIView):
    """
    API do Dashboard (Aula 17, slide 35)
    Retorna métricas consolidadas em JSON para clientes externos e integrações.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        org = org_atual(request)
        if not org:
            return Response({"erro": "Usuário não possui organização vinculada."}, status=403)

        metricas = obter_metricas_dashboard(request, org)
        return Response({
            "organizacao": org.nome,
            "kpis": metricas["kpis"],
            "ranking": list(metricas["ranking"]),
            "por_mes": [
                {"mes": item["mes"].strftime("%Y-%m") if item["mes"] else "N/A", "total": item["total"]}
                for item in metricas["por_mes"]
            ],
            "por_prioridade": list(metricas["por_prioridade"]),
        })
