# inventory_analysis/apps.py

from django.apps import AppConfig

class InventoryAnalysisConfig(AppConfig):
    # O nome da classe deve ser 'BigAutoField' para a versão 5.2 do Django
    default_auto_field = 'django.db.models.BigAutoField' 
    name = 'inventory_analysis'
    verbose_name = 'Análise de Inventário'