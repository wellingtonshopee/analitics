# collection_pool/urls.py (Adicione a nova rota)

from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_pool_csv, name='upload_pool_csv'),
    path('menu/', views.menu_pool, name='menu_pool'),
    # 🚨 NOVO: Rota do Dashboard
    path('dashboard/', views.dashboard_pool, name='dashboard_pool'),
    path('detalhes/<str:status_slug>/', views.pool_detail_list, name='pool_detail_list'),
    path('detalhes/cidade/<str:city_slug>/', views.pool_detail_list_by_city, name='pool_detail_list_by_city'),
    path('deletar-registros/', views.delete_pool_records, name='delete_pool_records'),
]