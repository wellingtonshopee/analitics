# logistica/models.py

from django.db import models

class DadosDiariosLogistica(models.Model):
    # Campos base
    data_envio = models.DateField(unique=True, verbose_name="Data de Envio")

    # Campos de Totais
    total_rotas = models.IntegerField(default=0, verbose_name="Total de Rotas")
    total_pacotes_iniciados = models.IntegerField(default=0, verbose_name="Total de Pacotes Iniciados")
    total_pacotes_finalizados = models.IntegerField(default=0, verbose_name="Total de Pacotes Finalizados")
    total_pacotes_escaneados = models.IntegerField(default=0, verbose_name="Total de Pacotes Escaneados")

    # Campos de Desvios/Problemas
    total_missorted = models.IntegerField(default=0, verbose_name="Total de Missorted")
    total_missing_expedicao = models.IntegerField(default=0, verbose_name="Total de Missing Expedição")
    total_onhold = models.IntegerField(default=0, verbose_name="Total Onhold")
    onhold_devolvidos = models.IntegerField(default=0, verbose_name="Onhold Devolvidos")
    onhold_devolver = models.IntegerField(default=0, verbose_name="Onhold a Devolver")
    
    # Outras Métricas
    volumosos_no_hub = models.IntegerField(default=0, verbose_name="Volumosos No HUB")
    pnr = models.IntegerField(default=0, verbose_name="PNR")
    backlog_parcel = models.IntegerField(default=0, verbose_name="Backlog Parcel")
    pedidos_roteirizar_pool = models.IntegerField(default=0, verbose_name="Pedidos a Roteirizar Pool")
    total_reversa = models.IntegerField(default=0, verbose_name="Total Reversa")
    missing_parcel = models.IntegerField(default=0, verbose_name="Missing Parcel")
    avaria_soc = models.IntegerField(default=0, verbose_name="Avaria SOC")
    avaria_hub = models.IntegerField(default=0, verbose_name="Avaria HUB")
    backlog_agarrado_varios_dias = models.IntegerField(default=0, verbose_name="Backlog Agarrado no HUB - Vários dias")

    class Meta:
        verbose_name = "Dado Diário de Logística"
        verbose_name_plural = "Dados Diários de Logística"
        ordering = ['-data_envio']

    def __str__(self):
        return f"Dados de Logística - {self.data_envio.strftime('%d/%m/%Y')}"