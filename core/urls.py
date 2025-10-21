# core/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Rota raiz (/) direcionada para a view 'dashboard'
    path('', views.dashboard, name='dashboard'),
]