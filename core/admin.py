# core/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import HUB, Usuario

# 1. Registrar o Modelo HUB (Empresa)
@admin.register(HUB)
class HUBAdmin(admin.ModelAdmin):
    list_display = ('nome', 'estado', 'data_criacao')
    search_fields = ('nome', 'estado')
    list_filter = ('estado',)

# 2. Registrar o Modelo Usuario
# É bom estender o UserAdmin para manter as funcionalidades de senha, permissões, etc.
@admin.register(Usuario)
class CustomUserAdmin(UserAdmin):
    # Adiciona 'hub' e 'cargo' aos campos visíveis no formulário de edição/criação
    fieldsets = UserAdmin.fieldsets + (
        ('Informações Adicionais', {'fields': ('hub', 'cargo')}),
    )
    # Adiciona 'hub' e 'cargo' à lista de colunas na tabela de usuários
    list_display = UserAdmin.list_display + ('hub', 'cargo',)
    list_filter = UserAdmin.list_filter + ('hub', 'cargo',)