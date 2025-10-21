# conferencia/models.py

from django.db import models
from django.utils import timezone

# 1. Modelo para armazenar os uploads (metadados)
class UploadConferencia(models.Model):
    """Armazena informações sobre o arquivo que foi feito upload."""
    
    TIPO_CHOICES = (
        ('A', 'Lista A'),
        ('B', 'Lista B'),
    )
    
    tipo_lista = models.CharField(
        max_length=1, 
        choices=TIPO_CHOICES,
        help_text="Indica se é a Lista A ou Lista B."
    )
    
    # Armazena o arquivo, caso queira reprocessá-lo
    arquivo_original = models.FileField(upload_to='conferencia_uploads/')
    data_upload = models.DateTimeField(default=timezone.now)
    
    # Status pode ser 'PENDENTE', 'CARREGADO', 'CONFERIDO'
    status = models.CharField(max_length=15, default='CARREGADO', 
                              help_text="Status do processamento do arquivo.")

    def __str__(self):
        return f"Upload {self.get_tipo_lista_display()} - {self.data_upload.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        verbose_name = "Upload de Conferência"
        verbose_name_plural = "Uploads de Conferência"


# 2. Modelo para armazenar os registros individuais de ambas as listas
class RegistroConferencia(models.Model):
    """Armazena cada linha/registro das listas A e B e o resultado da comparação."""
    
    LISTA_CHOICES = (
        ('A', 'Lista A'),
        ('B', 'Lista B'),
    )
    
    # Os status de conferência que o usuário solicitou (Azul, Vermelho, Verde)
    STATUS_CHOICES = (
        ('SOMENTE_A', 'Somente na Lista A (Azul)'),     # A - B
        ('SOMENTE_B', 'Somente na Lista B (Vermelho)'),  # B - A
        ('PRESENTE', 'Presente em Ambas (Verde)'),      # A ∩ B
        ('PENDENTE', 'Aguardando Conferência'),
    )

    # Campo CRUCIAL: O código que será usado para a comparação (Ex: um SKU, código de rastreio, etc.)
    codigo_item = models.CharField(max_length=255, db_index=True)
    
    # Campo para guardar dados adicionais do registro, se o arquivo tiver mais colunas
    # JSONField é eficiente para dados semi-estruturados.
    dados_extras = models.JSONField(null=True, blank=True) 

    # Qual lista este registro pertence originalmente
    lista_origem = models.CharField(max_length=1, choices=LISTA_CHOICES)
    
    # Resultado da conferência para este registro. Só será preenchido após a execução da conferência.
    status_conferencia = models.CharField(
        max_length=15, 
        choices=STATUS_CHOICES, 
        default='PENDENTE',
        help_text="Resultado da comparação entre as listas."
    )

    def __str__(self):
        return f"[{self.lista_origem}] {self.codigo_item} - {self.get_status_conferencia_display()}"
        
    class Meta:
        verbose_name = "Registro de Conferência"
        verbose_name_plural = "Registros de Conferência"
        # Garante que um mesmo código (ex: SKU) não seja carregado duas vezes na mesma lista
        unique_together = ('codigo_item', 'lista_origem')