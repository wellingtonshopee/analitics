from django.db import models
from django.conf import settings
from django.utils import timezone

# 1. Modelo de Metadados do Arquivo (Ajustado para o Form)
class ExpedicaoArquivo(models.Model):
    # NOVO: Campo para armazenar o arquivo (FileField)
    arquivo = models.FileField(
        upload_to='expedicoes/', 
        verbose_name='Arquivo CSV'
    ) 
    
    # NOVO: Campo de Data de Referência
    data_referencia = models.DateField(verbose_name='Data de Referência')

    # Campos de Metadados
    num_registros = models.IntegerField(default=0)
    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    data_envio = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.data_referencia} - {self.arquivo.name.split('/')[-1]}"

    class Meta:
        verbose_name = "Arquivo de Expedição"
        verbose_name_plural = "Arquivos de Expedição"
        
# 2. Modelo: Para armazenar cada registro do CSV (Nenhuma mudança necessária aqui)
class RegistroExpedicao(models.Model):
    arquivo_origem = models.ForeignKey(
        ExpedicaoArquivo, 
        on_delete=models.CASCADE,
        related_name='registros',
        verbose_name='Arquivo de Origem'
    )
    # Mapeamento das colunas do CSV
    at_to = models.CharField(max_length=50, verbose_name="AT/TO")
    corridor_cage = models.CharField(max_length=50, verbose_name="Corredor/Cage")
    total_initial_orders = models.IntegerField(verbose_name="Iniciais")
    total_final_orders = models.IntegerField(verbose_name="Finais")
    total_scanned_orders = models.IntegerField(verbose_name="Escaneados")
    missorted_orders = models.IntegerField(verbose_name="Missorted")
    missing_orders = models.IntegerField(verbose_name="Missing")
    validation_start_time = models.DateTimeField(null=True, blank=True, verbose_name="Início Validação")
    validation_end_time = models.DateTimeField(null=True, blank=True, verbose_name="Fim Validação")
    validation_operator = models.CharField(max_length=255, null=True, blank=True, verbose_name="Operador Validação")
    revalidation_operator = models.CharField(max_length=255, null=True, blank=True, verbose_name="Operador Revalidação")
    revalidated_count = models.IntegerField(default=0, verbose_name="Revalidados")
    at_to_validation_status = models.CharField(max_length=50, verbose_name="Status Validação")
    remark = models.TextField(null=True, blank=True, verbose_name="Observação")
    
    data_registro = models.DateTimeField(default=timezone.now, verbose_name="Data de Registro")

    class Meta:
        verbose_name = "Registro de Expedição"
        verbose_name_plural = "Registros de Expedição"