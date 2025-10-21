# parcel_sweeper/urls.py

from django.urls import path
from . import views

app_name = 'parcel_sweeper'

urlpatterns = [
    # 🔑 Rota principal do app que leva ao menu de ações
    path('', views.menu_actions_sweeper, name='menu_actions_sweeper'), 
    
    path('upload/', views.upload_parcel, name='upload_parcel'),
    path('dashboard/', views.dashboard_parcel, name='dashboard'), 
    path('detalhe/<slug:count_type_slug>/', views.parcel_detail_list, name='detail_list'),
    path('detalhe/status/<slug:final_status_slug>/', views.parcel_status_detail_list, name='status_detail_list'),
    path('export/csv/', views.export_parcel_csv, name='export_csv'),
    path('update-lost-status/', views.run_status_update, name='update_lost_status'),
]