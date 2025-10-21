# apresentacao/urls.py
from django.urls import path
from . import views

app_name = 'apresentacao'

urlpatterns = [
    # Tela de Seleção/Criação de Apresentação
    path('', views.selecionar_apresentacao, name='selecionar_apresentacao'),
    
    # Tela de Visualização do Painel (Power BI Style)
    path('detalhe/<int:pk>/', views.detalhe_apresentacao, name='detalhe_apresentacao'),
    
    # Tela de Edição Dinâmica (com Formsets Aninhados)
    path('editar/<int:pk>/', views.editar_apresentacao, name='editar_apresentacao'),
]