from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ManualActionLog(models.Model):
    """
    Registra ações manuais do usuário que sobrescrevem a lógica de análise automática.
    """
    ACTION_CHOICES = [
        ('ADD', 'Adicionar à Collection Pool (Sobrescrever)'),
        ('REMOVE', 'Não Adicionar à Collection Pool (Ignorar)'),
        ('ROUTED', 'Marcar como Roteirizado (Sobrescrever)'),
    ]

    # Chave do item que está sendo modificado
    parcel_id = models.CharField(max_length=50, unique=True, db_index=True, verbose_name="Nº Rastreio")
    
    # Ação escolhida pelo usuário
    action_type = models.CharField(max_length=10, choices=ACTION_CHOICES, verbose_name="Tipo de Ação")
    
    # Metadados de registro
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data da Ação")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Usuário")

    class Meta:
        verbose_name = "Registro de Ação Manual"
        verbose_name_plural = "Registros de Ações Manuais"
        
    def __str__(self):
        return f"{self.parcel_id} - {self.get_action_type_display()}"