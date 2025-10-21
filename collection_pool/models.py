# collection_pool/models.py

from django.db import models
from django.conf import settings # Para importar o User

class Pool(models.Model):
    # Campos de controle
    data_envio_arquivo = models.DateField(
        verbose_name="Data de Envio do Arquivo"
    )
    usuario_upload = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Usuário de Upload"
    )
    data_upload = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data de Upload no Sistema"
    )

    # Campos de dados (Baseado no CSV)
    shipment_id = models.CharField(max_length=50, verbose_name="Shipment Id", db_index=True, unique=True)
    zipcode = models.CharField(max_length=20, verbose_name="Zipcode", null=True, blank=True)
    destination_address = models.TextField(verbose_name="Destination Address", null=True, blank=True)
    neighborhood = models.CharField(max_length=100, verbose_name="Neighborhood", null=True, blank=True)
    city = models.CharField(max_length=100, verbose_name="City", null=True, blank=True)
    region = models.CharField(max_length=100, verbose_name="Region", null=True, blank=True)
    cluster = models.CharField(max_length=100, verbose_name="Cluster", null=True, blank=True)
    address_type = models.CharField(max_length=50, verbose_name="Address Type", null=True, blank=True)
    lh_trip = models.CharField(max_length=50, verbose_name="LH Trip", null=True, blank=True)
    destination_hub = models.CharField(max_length=100, verbose_name="Destination Hub", null=True, blank=True)
    status = models.CharField(max_length=50, verbose_name="Status", null=True, blank=True)
    length_cm = models.FloatField(verbose_name="Length(cm)", null=True, blank=True)
    width_cm = models.FloatField(verbose_name="Width(cm)", null=True, blank=True)
    height_cm = models.FloatField(verbose_name="Height(cm)", null=True, blank=True)
    weight_kg = models.FloatField(verbose_name="Weight(kg)", null=True, blank=True)
    dimension_source_type = models.CharField(max_length=50, verbose_name="Dimension Source Type", null=True, blank=True)
    to_id = models.CharField(max_length=50, verbose_name="TO ID", null=True, blank=True)

    class Meta:
        verbose_name = "Item do Collection Pool"
        verbose_name_plural = "Itens do Collection Pool"
        # 🚨 RESTRIÇÃO unique_together REMOVIDA para permitir duplicatas de shipment_id
        # unique_together = ('shipment_id', 'data_envio_arquivo') <--- REMOVER ESTA LINHA
        # Duplicatas agora serão controladas apenas pelo id primário do Django. 

    def __str__(self):
        return self.shipment_id