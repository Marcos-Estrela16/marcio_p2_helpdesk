from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("chamado/novo/", views.novo_chamado, name="novo_chamado"),
    path("chamado/<int:chamado_id>/", views.detalhes_chamado, name="detalhes_chamado"),
    path("slas/", views.slas_info, name="slas_info"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("chamados/exportar/", views.exportar_csv, name="exportar_csv"),
]
