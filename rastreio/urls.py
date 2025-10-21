# rastreio/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_csv_rastreio, name='upload_csv_rastreio'),
    path('dashboard/', views.dashboard_rastreio, name='dashboard_rastreio'), 
    path('menu/', views.menu_rastreio, name='menu_rastreio'),
    
    # 🌟 NOVOS PATHS NECESSÁRIOS 🌟
    path('detalhes/', views.detalhe_rastreio_view, name='detalhe_rastreio_view'),
    path('exportar/', views.exportar_csv_rastreio, name='exportar_csv_rastreio'), # CORREÇÃO DO ERRO
]