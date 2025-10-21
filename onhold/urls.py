from django.urls import path
from . import views

urlpatterns = [
    path('onhold/', views.dashboard_onhold, name='dashboard_onhold'), 
    path('onhold/upload/', views.upload_csv_onhold, name='upload_onhold'),
    path('onhold/consulta/', views.consulta_onhold, name='consulta_onhold'),
    path('onhold/consulta/<path:motivo>/', views.consulta_por_motivo, name='consulta_por_motivo'),

    # ✅ NOVA ROTA para Exportação
    path('onhold/export_por_motivo/<str:motivo>/', views.export_por_motivo_csv, name='export_por_motivo_csv'),
    path('consulta/motorista/', views.consulta_onhold_por_motorista, name='consulta_por_motorista'),
    path('acoes/', views.menu_acoes_onhold, name='menu_onhold'), # <- Nova URL para o Menu
    path('exportar/onhold/motorista/', views.exportar_onhold_motorista_csv, name='exportar_onhold_motorista_csv'),
    # NOVA URL: Detalhe por Motorista
    path('consulta/motorista/', views.consulta_por_motorista, name='consulta_por_motorista'),
    # ✅ NOVA ROTA: Upload de OnHold Inicial
    path('onhold/upload_inicial/', views.upload_csv_onhold_inicial, name='upload_onhold_inicial'),
    path('onhold/dashboard_inicial/', views.dashboard_onhold_inicial_dia, name='dashboard_onhold_inicial_dia'),
    path('onhold/detalhe_inicial/', views.detalhe_pacotes_inicial, name='detalhe_pacotes_inicial'),
    path('onhold/volumosos/', views.detalhe_volumosos, name='detalhe_volumosos'),
    

]