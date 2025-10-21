# logistica/forms.py

from django import forms
from .models import DadosDiariosLogistica # Altere para o nome correto do seu app.models

class DadosDiariosLogisticaForm(forms.ModelForm):
    class Meta:
        model = DadosDiariosLogistica
        # Inclui todos os campos do modelo
        fields = '__all__' 
        
        # Opcional: Adiciona widgets para melhor UX (Bootstrap style)
        widgets = {
            'data_envio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            
            'total_rotas': forms.NumberInput(attrs={'class': 'form-control'}),
            'total_pacotes_iniciados': forms.NumberInput(attrs={'class': 'form-control'}),
            'total_pacotes_finalizados': forms.NumberInput(attrs={'class': 'form-control'}),
            'total_pacotes_escaneados': forms.NumberInput(attrs={'class': 'form-control'}),
            
            'total_missorted': forms.NumberInput(attrs={'class': 'form-control'}),
            'total_missing_expedicao': forms.NumberInput(attrs={'class': 'form-control'}),
            'total_onhold': forms.NumberInput(attrs={'class': 'form-control'}),
            'onhold_devolvidos': forms.NumberInput(attrs={'class': 'form-control'}),
            'onhold_devolver': forms.NumberInput(attrs={'class': 'form-control'}),
            
            'volumosos_no_hub': forms.NumberInput(attrs={'class': 'form-control'}),
            'pnr': forms.NumberInput(attrs={'class': 'form-control'}),
            'backlog_parcel': forms.NumberInput(attrs={'class': 'form-control'}),
            'pedidos_roteirizar_pool': forms.NumberInput(attrs={'class': 'form-control'}),
            'total_reversa': forms.NumberInput(attrs={'class': 'form-control'}),
            'missing_parcel': forms.NumberInput(attrs={'class': 'form-control'}),
            'avaria_soc': forms.NumberInput(attrs={'class': 'form-control'}),
            'avaria_hub': forms.NumberInput(attrs={'class': 'form-control'}),
            'backlog_agarrado_varios_dias': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class PeriodoFiltroForm(forms.Form):
    data_inicio = forms.DateField(
        label='Data de Início',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False
    )
    data_fim = forms.DateField(
        label='Data de Fim',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False
    )
    
    # Adicionamos um clean para garantir que a data de fim não seja anterior à de início
    def clean(self):
        cleaned_data = super().clean()
        data_inicio = cleaned_data.get("data_inicio")
        data_fim = cleaned_data.get("data_fim")

        if data_inicio and data_fim and data_inicio > data_fim:
            raise forms.ValidationError(
                "A Data de Início não pode ser posterior à Data de Fim."
            )
        return cleaned_data        

