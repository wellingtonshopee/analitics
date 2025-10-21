from django.contrib import admin
from .models import Apresentacao, Topico, Card

class CardInline(admin.TabularInline):
    """Define o Card como um item editável dentro do Tópico."""
    model = Card
    extra = 1 # Quantos formulários vazios adicionar

class TopicoInline(admin.TabularInline):
    """Define o Tópico como um item editável dentro da Apresentacao."""
    model = Topico
    extra = 1 # Permite adicionar mais tópicos
    inlines = [CardInline] # Permite adicionar Cards dentro do Tópico

@admin.register(Apresentacao)
class ApresentacaoAdmin(admin.ModelAdmin):
    list_display = ('data_apresentacao', 'data_criacao')
    search_fields = ('data_apresentacao',)
    date_hierarchy = 'data_apresentacao'
    
    # Aqui está a mágica: Adiciona o Topico e seus Cards na tela de Apresentacao
    inlines = [TopicoInline] 
    
# Opcional: registrar os outros modelos se quiser acesso direto
# admin.site.register(Topico)
# admin.site.register(Card)