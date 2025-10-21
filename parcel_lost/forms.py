# parcel_lost/forms.py
from django import forms
from .models import ParcelLost
from django.utils import timezone
from datetime import timedelta

# --- Formulário de Registro Manual ---
class ParcelLostForm(forms.ModelForm):
    # O campo de data de registro será um DateInput
    data_registro = forms.DateField(
        label='Data de Registro (Referência)',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=timezone.localdate # Valor padrão para a data atual
    )
    
    # O campo de data de ocorrência também será um DateInput
    data_ocorrencia_spx = forms.DateField(
        label='Data Ocorrência SPX',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )

    class Meta:
        model = ParcelLost
        fields = [
            'data_registro', 
            'spx_tracking_number', 
            'final_status_avaria', 
            'data_ocorrencia_spx'
        ]
        widgets = {
            'spx_tracking_number': forms.TextInput(attrs={'class': 'form-control'}),
            'final_status_avaria': forms.Select(attrs={'class': 'form-select'}),
        }


# --- Formulário de Filtros para o Dashboard ---
class LostFilterForm(forms.Form):
    data_inicio = forms.DateField(
        label="Data Início",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    data_fim = forms.DateField(
        label="Data Fim",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )

    # Filtro por tipo de avaria (Lost ou Damage)
    TIPO_CHOICES = (
        ('', 'Todos (Lost/Damage)'),
        ('LOST', 'Apenas Perdas (Lost)'),
        ('DAMAGE', 'Apenas Avarias (Damage)'),
    )
    tipo_avaria = forms.ChoiceField(
        choices=TIPO_CHOICES,
        label="Tipo de Ocorrência",
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Define datas padrão: hoje e 30 dias atrás, se não houver dados no banco
        try:
            # Tenta pegar a data mais recente no banco como referência
            data_padrao_fim = ParcelLost.objects.latest('data_registro').data_registro
        except ParcelLost.DoesNotExist:
            data_padrao_fim = timezone.localdate()

        data_padrao_inicio = data_padrao_fim - timedelta(days=30)
        
        self.fields['data_inicio'].initial = data_padrao_inicio
        self.fields['data_fim'].initial = data_padrao_fim