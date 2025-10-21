from django import forms
from datetime import date, timedelta
from django.utils import timezone # Importar para usar a data atual no fuso horário local

class DateRangeForm(forms.Form):
    """Formulário simples para filtrar dados por um período de tempo."""
    
    # Campo de Data de Início
    data_inicio = forms.DateField(
        label='Data Início',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    
    # Campo de Data Final
    data_fim = forms.DateField(
        label='Data Fim',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Define datas padrão para o formulário aparecer preenchido na primeira vez
        data_padrao_fim = timezone.localdate()
        data_padrao_inicio = data_padrao_fim - timedelta(days=7) # Pega os últimos 7 dias

        # Aplica o valor inicial APENAS se o formulário não tiver sido submetido
        if 'data_inicio' not in self.data:
            self.fields['data_inicio'].initial = data_padrao_inicio
        if 'data_fim' not in self.data:
            self.fields['data_fim'].initial = data_padrao_fim