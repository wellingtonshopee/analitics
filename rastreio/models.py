# rastreio/models.py

from django.db import models
from django.conf import settings # NOVO: Importe settings
# REMOVIDO: from django.contrib.auth.models import User 

class Rastreio(models.Model):
    # Campos Administrativos
    data_envio_arquivo = models.DateField(null=True, blank=True, verbose_name="Data de Envio do Arquivo")
    data_upload = models.DateTimeField(auto_now_add=True, verbose_name="Data de Upload")
    
    # CORRIGIDO: Referencia o modelo de usuário correto
    usuario_upload = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Usuário de Upload"
    )
    
    # Campos da Planilha (Dados de Rastreio)
    order_id = models.CharField(max_length=50, null=True, blank=True, verbose_name="Order ID")
    sls_tracking_number = models.CharField(max_length=50, null=True, blank=True, verbose_name="SLS Tracking Number")
    shopee_order_sn = models.CharField(max_length=50, null=True, blank=True, verbose_name="Shopee Order SN")
    longitude = models.CharField(max_length=50, null=True, blank=True)
    latitude = models.CharField(max_length=50, null=True, blank=True)
    sort_code_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Sort Code Name")
    zipcode_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Zipcode Name")
    buyer_name = models.CharField(max_length=150, null=True, blank=True, verbose_name="Buyer Name")
    buyer_phone = models.CharField(max_length=50, null=True, blank=True, verbose_name="Buyer Phone")
    buyer_address = models.TextField(null=True, blank=True, verbose_name="Buyer Address")
    location_type = models.CharField(max_length=50, null=True, blank=True, verbose_name="Location Type")
    postal_code = models.CharField(max_length=20, null=True, blank=True, verbose_name="Postal Code")
    driver_id = models.CharField(max_length=50, null=True, blank=True, verbose_name="Driver ID")
    driver_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Driver Name")
    driver_phone = models.CharField(max_length=50, null=True, blank=True, verbose_name="Driver Phone")
    lm_hub_receive_time = models.CharField(max_length=50, null=True, blank=True, verbose_name="LM Hub Receive time")
    current_station_received_time = models.CharField(max_length=50, null=True, blank=True, verbose_name="Current Station Received Time")
    delivering_time = models.CharField(max_length=50, null=True, blank=True, verbose_name="Delivering Time")
    delivered_time = models.CharField(max_length=50, null=True, blank=True, verbose_name="Delivered Time")
    onhold_time = models.CharField(max_length=50, null=True, blank=True, verbose_name="OnHold Time")
    onhold_reason = models.CharField(max_length=255, null=True, blank=True, verbose_name="OnHoldReason")
    reschedule_date = models.CharField(max_length=50, null=True, blank=True, verbose_name="Reschedule Date")
    status = models.CharField(max_length=50, null=True, blank=True, verbose_name="Status")
    reject_remark = models.CharField(max_length=255, null=True, blank=True, verbose_name="Reject remark")
    cod_amount = models.FloatField(null=True, blank=True, verbose_name="COD Amount")
    manifest_number = models.CharField(max_length=50, null=True, blank=True, verbose_name="Manifest Number")
    order_account = models.CharField(max_length=50, null=True, blank=True, verbose_name="Order Account")
    original_asf = models.FloatField(null=True, blank=True, verbose_name="Original ASF")
    rounding_asf = models.FloatField(null=True, blank=True, verbose_name="Rounding ASF")
    total_of_on_hold_times = models.IntegerField(null=True, blank=True, verbose_name="Total of On Hold Times")
    reschedule_time = models.CharField(max_length=50, null=True, blank=True, verbose_name="Reschedule Time")
    delivery_attempts = models.IntegerField(null=True, blank=True, verbose_name="Delivery Attempts")
    bulky_type = models.CharField(max_length=50, null=True, blank=True, verbose_name="Bulky Type")
    sla_target_date = models.CharField(max_length=50, null=True, blank=True, verbose_name="SLA Target Date")
    time_to_sla = models.CharField(max_length=50, null=True, blank=True, verbose_name="Time to SLA")
    payment_method = models.CharField(max_length=50, null=True, blank=True, verbose_name="Payment Method")
    current_station = models.CharField(max_length=100, null=True, blank=True, verbose_name="Current Station")
    return_destination = models.CharField(max_length=100, null=True, blank=True, verbose_name="Return Destination")
    shop_id = models.CharField(max_length=50, null=True, blank=True, verbose_name="Shop ID")
    shop_category = models.CharField(max_length=50, null=True, blank=True, verbose_name="Shop Category")
    inbound_3pl = models.CharField(max_length=50, null=True, blank=True, verbose_name="Inbound 3PL")
    outbound_3pl = models.CharField(max_length=50, null=True, blank=True, verbose_name="Outbound 3PL")
    channel = models.CharField(max_length=50, null=True, blank=True, verbose_name="Channel")
    _3pl_tn = models.CharField(max_length=50, null=True, blank=True, verbose_name="3PL TN")
    destination_hub = models.CharField(max_length=100, null=True, blank=True, verbose_name="Destination Hub")
    zone = models.CharField(max_length=50, null=True, blank=True, verbose_name="Zone")
    calculation_status = models.CharField(max_length=50, null=True, blank=True, verbose_name="Calculation Status")
    specical_dg_type = models.CharField(max_length=50, null=True, blank=True, verbose_name="Specical Dg Type")
    damaged_tag = models.CharField(max_length=50, null=True, blank=True, verbose_name="Damaged Tag")

    class Meta:
        verbose_name = "Rastreio"
        verbose_name_plural = "Rastreios"

    def __str__(self):
        return self.sls_tracking_number or self.order_id or "Rastreio Sem ID"