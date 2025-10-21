from django.db import models
from core.models import HUB, Usuario # Importa modelos já existentes

class OnHold(models.Model):
    # ==================================
    # CAMPOS DE AUDITORIA E VINCULAÇÃO
    # ==================================
    # 🔑 AJUSTE CRÍTICO: Removida a redefinição redundante do campo no final do arquivo.
    data_envio = models.DateField(null=True, blank=True, verbose_name="Data de Envio/Referência")
    
    hub_upload = models.ForeignKey(HUB, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="HUB do Upload")
    usuario_upload = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Usuário do Upload")

    # ==================================
    # CAMPOS DO CSV (Mapeados pelo índice)
    # ==================================
    
    # Identificadores (Colunas 0, 1, 3)
    order_id = models.CharField(max_length=50, null=True, blank=True, verbose_name="Order ID")
    sls_tracking_number = models.CharField(max_length=50, null=True, blank=True, verbose_name="SLS Tracking Number")
    shopee_order_sn = models.CharField(max_length=50, null=True, blank=True, verbose_name="Shopee Order SN")
    
    # ✅ NOVO CAMPO: Driver Name (Coluna 11)
    driver_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Driver Name")
    
    # Destino e Cliente (Colunas 4, 5, 6, 9)
    sort_code_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Sort Code Name")
    buyer_name = models.CharField(max_length=150, null=True, blank=True, verbose_name="Nome Comprador")
    buyer_phone = models.CharField(max_length=20, null=True, blank=True, verbose_name="Telefone Comprador")
    postal_code = models.CharField(max_length=10, null=True, blank=True, verbose_name="CEP")
    
    # Status OnHold (Colunas 16, 17, 19)
    onhold_time = models.DateField(null=True, blank=True, verbose_name="OnHold Data") 
    onhold_reason = models.CharField(max_length=255, null=True, blank=True, verbose_name="Motivo OnHold") # Motivo da retenção
    status = models.CharField(max_length=50, null=True, blank=True, verbose_name="Status")
    
    # Detalhes Adicionais (Colunas 21, 35, 23-28)
    manifest_number = models.CharField(max_length=50, null=True, blank=True, verbose_name="Manifest Number") # Coluna 21
    payment_method = models.CharField(max_length=50, null=True, blank=True, verbose_name="Payment Method") # Coluna 35
    
    # Informações de Peso/Dimensão (Campos numéricos)
    parcel_weight = models.FloatField(null=True, blank=True, verbose_name="Peso (kg)") # Coluna 23
    length = models.FloatField(null=True, blank=True, verbose_name="Comprimento (cm)") # Coluna 25
    width = models.FloatField(null=True, blank=True, verbose_name="Largura (cm)") # Coluna 26
    height = models.FloatField(null=True, blank=True, verbose_name="Altura (cm)") # Coluna 27


    def __str__(self):
        return f"{self.sls_tracking_number} - {self.onhold_reason} ({self.hub_upload.nome if self.hub_upload else 'N/A'})"
    
    class Meta:
        verbose_name = "Registro OnHold"
        verbose_name_plural = "Registros OnHold"
        ordering = ['-data_envio', 'onhold_time'] # Ordena pelo mais recente
        
        # 🔑 AJUSTE FINAL: A restrição unique_together foi REMOVIDA para permitir duplicatas.
        # unique_together = ('order_id', 'onhold_time') <--- ESTA LINHA FOI EXCLUÍDA

class OnholdInicial(models.Model):
    # ==================================
    # CAMPOS DE AUDITORIA E VINCULAÇÃO
    # (Exatamente como em OnHold)
    # ==================================
    data_envio = models.DateField(null=True, blank=True, verbose_name="Data de Envio/Referência")
    hub_upload = models.ForeignKey(HUB, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="HUB do Upload")
    usuario_upload = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Usuário do Upload")

    # ==================================
    # CAMPOS DO CSV (41 COLUNAS)
    # Colunas mapeadas com base no cabeçalho
    # ==================================
    order_id = models.CharField(max_length=50, null=True, blank=True, verbose_name="Order ID") # Coluna 0
    sls_tracking_number = models.CharField(max_length=50, null=True, blank=True, verbose_name="SLS Tracking Number") # Coluna 1
    # ... (omitindo colunas 2 a 3 para brevidade) ...
    shopee_order_sn = models.CharField(max_length=50, null=True, blank=True, verbose_name="Shopee Order SN") # Coluna 3
    sort_code_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Sort Code Name") # Coluna 4
    buyer_name = models.CharField(max_length=150, null=True, blank=True, verbose_name="Nome Comprador") # Coluna 5
    buyer_phone = models.CharField(max_length=20, null=True, blank=True, verbose_name="Telefone Comprador") # Coluna 6
    buyer_address = models.CharField(max_length=255, null=True, blank=True, verbose_name="Endereço Comprador") # Coluna 7
    location_type = models.CharField(max_length=50, null=True, blank=True, verbose_name="Location Type") # Coluna 8
    postal_code = models.CharField(max_length=10, null=True, blank=True, verbose_name="CEP") # Coluna 9
    driver_id = models.CharField(max_length=50, null=True, blank=True, verbose_name="Driver ID") # Coluna 10
    driver_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Driver Name") # Coluna 11
    driver_phone = models.CharField(max_length=20, null=True, blank=True, verbose_name="Driver Phone") # Coluna 12
    pick_up_time = models.CharField(max_length=50, null=True, blank=True, verbose_name="Pick Up Time") # Coluna 13 (Manter como CharField, se não for usar como filtro)
    soc_received_time = models.CharField(max_length=50, null=True, blank=True, verbose_name="SOC Received Time") # Coluna 14
    delivered_time = models.CharField(max_length=50, null=True, blank=True, verbose_name="Delivered Time") # Coluna 15
    onhold_time = models.CharField(max_length=50, null=True, blank=True, verbose_name="OnHold Time") # Coluna 16
    onhold_reason = models.CharField(max_length=255, null=True, blank=True, verbose_name="Motivo OnHold") # Coluna 17
    reschedule_time = models.CharField(max_length=50, null=True, blank=True, verbose_name="Reschedule Time") # Coluna 18
    status = models.CharField(max_length=50, null=True, blank=True, verbose_name="Status") # Coluna 19
    reject_remark = models.CharField(max_length=255, null=True, blank=True, verbose_name="Reject Remark") # Coluna 20
    manifest_number = models.CharField(max_length=50, null=True, blank=True, verbose_name="Manifest Number") # Coluna 21
    order_account = models.CharField(max_length=50, null=True, blank=True, verbose_name="Order Account") # Coluna 22
    parcel_weight = models.FloatField(null=True, blank=True, verbose_name="Peso (kg)") # Coluna 23
    sls_weight = models.FloatField(null=True, blank=True, verbose_name="SLS Weight (kg)") # Coluna 24
    length = models.FloatField(null=True, blank=True, verbose_name="Comprimento (cm)") # Coluna 25
    width = models.FloatField(null=True, blank=True, verbose_name="Largura (cm)") # Coluna 26
    height = models.FloatField(null=True, blank=True, verbose_name="Altura (cm)") # Coluna 27
    original_asf = models.FloatField(null=True, blank=True, verbose_name="Original ASF") # Coluna 28
    rounding_asf = models.FloatField(null=True, blank=True, verbose_name="Rounding ASF") # Coluna 29
    cod_fee = models.FloatField(null=True, blank=True, verbose_name="COD Fee") # Coluna 30
    delivery_attempts = models.IntegerField(null=True, blank=True, verbose_name="Delivery Attempts") # Coluna 31
    bulky_type = models.CharField(max_length=50, null=True, blank=True, verbose_name="Bulky Type") # Coluna 32
    sla_target_date = models.CharField(max_length=50, null=True, blank=True, verbose_name="SLA Target Date") # Coluna 33
    time_to_sla = models.CharField(max_length=50, null=True, blank=True, verbose_name="Time to SLA") # Coluna 34
    payment_method = models.CharField(max_length=50, null=True, blank=True, verbose_name="Payment Method") # Coluna 35
    pickup_station = models.CharField(max_length=150, null=True, blank=True, verbose_name="Pickup Station") # Coluna 36
    destination_station = models.CharField(max_length=150, null=True, blank=True, verbose_name="Destination Station") # Coluna 37
    next_station = models.CharField(max_length=150, null=True, blank=True, verbose_name="Next Station") # Coluna 38
    current_station = models.CharField(max_length=150, null=True, blank=True, verbose_name="Current Station") # Coluna 39
    channel = models.CharField(max_length=50, null=True, blank=True, verbose_name="Channel") # Coluna 40
    previous_3pl = models.CharField(max_length=50, null=True, blank=True, verbose_name="Previous 3PL") # Coluna 41
    next_3pl = models.CharField(max_length=50, null=True, blank=True, verbose_name="Next 3PL") # Coluna 42
    shop_id = models.CharField(max_length=50, null=True, blank=True, verbose_name="Shop ID") # Coluna 43
    shop_category = models.CharField(max_length=50, null=True, blank=True, verbose_name="Shop Category") # Coluna 44
    inbound_3pl = models.CharField(max_length=50, null=True, blank=True, verbose_name="Inbound 3PL") # Coluna 45
    outbound_3pl = models.CharField(max_length=50, null=True, blank=True, verbose_name="Outbound 3PL") # Coluna 46

    def __str__(self):
        return f"Inicial: {self.sls_tracking_number} ({self.data_envio})"
    
    class Meta:
        verbose_name = "Registro OnHold Inicial (Completo)"
        verbose_name_plural = "Registros OnHold Inicial (Completos)"
        ordering = ['-data_envio']        