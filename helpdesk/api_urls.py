from django.urls import path
from .api_views import (
    ChamadoListCreate,
    ChamadoDetail,
    CategoriaListCreate,
    PrioridadeList,
    DashboardApi,
)

urlpatterns = [
    path("chamados/", ChamadoListCreate.as_view(), name="api_chamados_list_create"),
    path("chamados/<int:pk>/", ChamadoDetail.as_view(), name="api_chamados_detail"),
    path("categorias/", CategoriaListCreate.as_view(), name="api_categorias_list_create"),
    path("prioridades/", PrioridadeList.as_view(), name="api_prioridades_list"),
    path("dashboard/", DashboardApi.as_view(), name="api_dashboard"),
]
