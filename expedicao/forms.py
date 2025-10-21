from django import forms
from .models import ExpedicaoArquivo

# CLASSE RENOMEADA: Para resolver o "ImportError" no views.py
class ExpedicaoArquivoForm(forms.ModelForm): 
    # Campo de Data (Data de Referência)
    data_referencia = forms.DateField(
        label="Data de Referência para o Lote (Filtro)",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=True
    )
    
    # Campo de Arquivo
    arquivo = forms.FileField(
        label="Selecione o arquivo CSV",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.csv'}),
        required=True
    )
    
    class Meta:
        model = ExpedicaoArquivo
        # Os campos devem corresponder aos campos do Model ExpedicaoArquivo
        fields = ['data_referencia', 'arquivo']