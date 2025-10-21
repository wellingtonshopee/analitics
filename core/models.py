# core/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser # Importar para estender

class HUB(models.Model):
    # O nome da empresa (Ex.: HUB LMG21 Muriaé)
    nome = models.CharField(max_length=150, unique=True, verbose_name="Nome da Empresa (HUB)")
    # O estado (Ex.: MG)
    estado = models.CharField(max_length=2, verbose_name="UF") 
    
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "HUB"
        verbose_name_plural = "HUBs"
        ordering = ['nome'] # Ordenar pelo nome

    def __str__(self):
        return f"{self.nome} ({self.estado})"

# No Django, 'models.Model' representa uma tabela no banco de dados.

class Usuario(AbstractUser):
    # O usuário deve ser vinculado a um HUB (Empresa)
    # models.ForeignKey cria a relação (chave estrangeira)
    # on_delete=models.SET_NULL: Se o HUB for deletado, o usuário fica sem HUB (pode ser ajustado)
    hub = models.ForeignKey(
        HUB, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, # Permite que o campo seja nulo no banco e formulários
        verbose_name="Empresa (HUB) Vinculada"
    )
    
    # Adicionando um campo extra (opcional, apenas para exemplo)
    cargo = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = "Usuário do Sistema"
        verbose_name_plural = "Usuários do Sistema"

    def __str__(self):
        # Retorna o nome de usuário e o nome do HUB, se houver
        hub_nome = self.hub.nome if self.hub else "Nenhum HUB"
        return f"{self.username} - {hub_nome}"
