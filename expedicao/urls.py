# urls.py

from django.urls import path
from . import views

app_name = 'expedicao'

urlpatterns = [
    # Rota para o Upload: /expedicao/upload/
    path('upload/', views.UploadExpedicaoView.as_view(), name='upload'),
    
    # Rota principal (Dashboard): /expedicao/
    path('', views.DashboardExpedicaoView.as_view(), name='dashboard'),

    # NOVO: Rota para Detalhes: /expedicao/detalhes/1/
    path('detalhes/<int:pk>/', views.DetalhesExpedicaoView.as_view(), name='detalhes'),

    # NOTA: A rota 'sucesso/' foi removida.
]