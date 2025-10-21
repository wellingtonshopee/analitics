# parcel_lost/urls.py

from django.urls import path
from . import views

app_name = 'parcel_lost'

urlpatterns = [
    # Rota para o Menu de Ações (Onde o card da dashboard principal aponta)
    path('menu-actions/', views.menu_actions_lost, name='menu_actions_lost'), 
    
    # Rota para a Dashboard de Gráficos e KPIs
    path('dashboard/', views.dashboard_lost, name='dashboard_lost'),
    
    # Rota para o Cadastro Manual
    path('register/', views.register_lost, name='register'),
    
    # 🔑 ROTA CORRIGIDA: Resolve o erro NoReverseMatch para os cartões de KPI 🔑
    path('list/<slug:type_slug>/', views.lost_detail_list, name='detail_list'),
    

]