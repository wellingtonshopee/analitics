# inventory_analysis/urls.py

from django.urls import path
from . import views

# O 'app_name' é importante para referenciar as URLs em templates (ex: {% url 'inventory_analysis:analysis_dashboard' %})
app_name = 'inventory_analysis' 

urlpatterns = [
    # Rota Principal: Dashboard (Ex: /inventory/dashboard/)
    path('dashboard/', views.analysis_dashboard, name='analysis_dashboard'),
    
    # Menu de Ações/Filtros (Ex: /inventory/actions/)
    path('actions/', views.action_menu, name='action_menu'),
    
    # Lista de Detalhes (Ex: /inventory/details/101/)
    # O <int:report_id> serve para passar um parâmetro de filtro na URL
    path('details/<int:report_id>/', views.detail_list, name='detail_list'),
    
    # Rota raiz do app (apenas redireciona para o dashboard, se desejar)
    path('', views.analysis_dashboard, name='index'), 

    # NOVO: Rota para exportação CSV (A partir da página de detalhes)
    path('export/<int:report_id>/', views.export_detail_list_csv, name='export_csv'),

    # NOVAS ROTAS PARA AÇÕES RÁPIDAS (AJAX/Redirect)
    path('action/add/<str:parcel_id>/', views.mark_as_added, name='mark_as_added'),
    path('action/remove/<str:parcel_id>/', views.remove_from_pool, name='remove_from_pool'),

]