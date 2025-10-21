# parcel_lost/models.py
from django.db import models
from django.conf import settings
from django.db.models import UniqueConstraint

class ParcelLost(models.Model):
    # Opções para a lista suspensa (Status / Avaria)
    STATUS_CHOICES = (
        ('SOC_LOST', 'Soc - Lost'),
        ('SOC_DAMAGE', 'Soc - Damage'),
        ('HUB_LOST', 'HUB - Lost'),
        ('HUB_DAMAGE', 'HUB - Damage'),
    )

    # 🔑 CAMPOS PRINCIPAIS
    data_registro = models.DateField(
        verbose_name="Data de Registro (Referência)",
        help_text="Data de referência para este registro de perda/avaria."
    )
    spx_tracking_number = models.CharField(
        max_length=255,
        verbose_name="SPX Tracking Number",
        db_index=True,
    )
    final_status_avaria = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        verbose_name="Status / Avaria",
        db_index=True
    )
    data_ocorrencia_spx = models.DateField(
        verbose_name="Data Ocorrência SPX",
        help_text="Data em que a avaria foi registrada no sistema SPX para o cliente.",
        null=True, blank=True
    )

    # CAMPOS DE CONTROLE
    usuario_registro = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Usuário de Registro"
    )
    data_registro_sistema = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data de Registro no Sistema"
    )

    class Meta:
        verbose_name = "Perda ou Avaria"
        verbose_name_plural = "Perdas e Avarias"
        # Garante que não haja duplicidade para o mesmo rastreio no mesmo dia de registro
        constraints = [
            UniqueConstraint(
                fields=['spx_tracking_number', 'data_registro'], 
                name='unique_lost_parcel_day'
            )
        ]

    def __str__(self):
        return f"{self.spx_tracking_number} - {self.get_final_status_avaria_display()}"