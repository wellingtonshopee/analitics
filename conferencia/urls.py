# conferencia/urls.py

from django.urls import path
from . import views

app_name = 'conferencia'

urlpatterns = [
    # Rotas existentes
    path('upload/', views.upload_arquivos, name='upload_arquivos'),
    path('executar-conferencia/', views.executar_conferencia, name='executar_conferencia'),
    path('resultados/', views.listagem_resultados, name='listagem_resultados'),
    path('apagar/', views.apagar_registros, name='apagar_registros'),
    path('exportar/', views.exportar_resultados, name='exportar_resultados'),
    
    # --- NOVAS ROTAS PARA CHECAGEM RÁPIDA ---
    path('checagem-rapida/', views.checagem_rapida_form, name='checagem_rapida_form'),
    path('checagem-rapida/processar/', views.processar_checagem_rapida, name='processar_checagem_rapida'),
]