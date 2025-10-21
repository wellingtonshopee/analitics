# parcel_sweeper/models.py

from django.db import models
from django.conf import settings # Para importar o User
# 🔑 IMPORTAÇÃO NECESSÁRIA
from django.db.models import UniqueConstraint 

class Parcel(models.Model):
    # --- CAMPOS DE CONTROLE ---
    data_referencia = models.DateField(
        verbose_name="Data de Referência (Arquivo)",
        help_text="Data informada pelo usuário no upload, usada para filtros."
    )
    usuario_upload = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Usuário de Upload"
    )
    data_upload_sistema = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data de Upload no Sistema"
    )

    # --- CAMPOS DO CSV (`parcel`) ---
    # Coluna 1: SPX Tracking Number 
    spx_tracking_number = models.CharField(
        max_length=255,
        verbose_name="SPX Tracking Number",
        db_index=True,
        # ❌ REMOVIDO: unique=True (A unicidade agora será na Meta)
    )
    # Demais colunas do CSV
    scanned_status = models.CharField(max_length=255, verbose_name="Scanned Status", null=True, blank=True)
    expedite_tag = models.CharField(max_length=255, verbose_name="Expedite Tag", null=True, blank=True)
    final_status = models.CharField(max_length=255, verbose_name="Final Status", db_index=True, null=True, blank=True)
    sort_code = models.CharField(max_length=255, verbose_name="Sort Code", null=True, blank=True)
    next_step_action = models.CharField(max_length=255, verbose_name="Next Step Action", null=True, blank=True)
    
    # AJUSTE: Mudar para default=0 e garantir que seja um inteiro.
    on_hold_times = models.IntegerField(verbose_name="On Hold Times", default=0, null=True, blank=True)
    
    count_type = models.CharField(max_length=255, verbose_name="Count Type", null=True, blank=True)
    expected = models.CharField(max_length=10, verbose_name="Expected", null=True, blank=True)
    operator = models.CharField(max_length=255, verbose_name="Operator", null=True, blank=True)
    aging_time = models.CharField(max_length=255, verbose_name="Aging Time", null=True, blank=True)
    scanned_time = models.DateTimeField(verbose_name="Scanned Time", null=True, blank=True)

    class Meta:
        verbose_name = "Item Parcel"
        verbose_name_plural = "Itens Parcel"
        # 🔑 CHAVE: A restrição de unicidade agora é a combinação dos dois campos.
        constraints = [
            UniqueConstraint(
                fields=['spx_tracking_number', 'data_referencia'], 
                name='unique_parcel_day'
            )
        ]

    def __str__(self):
        return self.spx_tracking_number