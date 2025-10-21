# logistica/urls.py

from django.urls import path
from . import views

app_name = 'logistica'

urlpatterns = [
    # NOVA ROTA PARA O DASHBOARD
    path('dashboard/', views.dashboard_logistica, name='dashboard'),
    
    path('', views.listar_e_filtrar_dados, name='listar_dados'), 
    path('inserir/', views.inserir_dados_logistica, name='inserir_dados'),
    path('editar/<int:pk>/', views.editar_dados_logistica, name='editar_dados'),
]