# sistema_logistica/urls.py

from django.contrib import admin
from django.urls import path, include 
from django.conf import settings 
from django.conf.urls.static import static 
from django.shortcuts import redirect 

urlpatterns = [
    # 1. ROTA RAIZ: O app 'core' DEVE SER O ÚNICO COM path('') (Define 'dashboard')
    path('', include('core.urls')), 
    
    # Rotas padrão de Login/Logout do Django
    path('accounts/', include('django.contrib.auth.urls')),
    
    # Rota do novo módulo
    path('expedicao/', include('expedicao.urls')), # Rota adicionada
    
    # Demais rotas (com prefixos únicos)
    path('onhold/', include('onhold.urls')), 
    path('rastreio/', include('rastreio.urls')),
    path('pool/', include('collection_pool.urls')), 
    path('parcel/', include('parcel_sweeper.urls')),
    path('parcel-lost/', include('parcel_lost.urls')),
    path('inventory/', include('inventory_analysis.urls')),
    path('conferencia/', include('conferencia.urls', namespace='conferencia')),
    path('apresentacao/', include('apresentacao.urls')),
    path('logistica/', include('logistica.urls')),
   
    # Rota do painel de administração
    path('admin/', admin.site.urls),
]

# BLOCO ESSENCIAL PARA SERVIR ARQUIVOS DE MÍDIA EM MODO DE DESENVOLVIMENTO
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)