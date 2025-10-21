from django import forms
from .models import Parcel
# 🚨 NOVAS IMPORTAÇÕES NECESSÁRIAS
from django.utils import timezone 
from datetime import timedelta
from django.db.models import Count 


class UploadParcelForm(forms.Form):
    arquivo_csv = forms.FileField(
        label='Arquivo CSV do Parcel Sweeper',
        help_text='Apenas arquivos .csv são aceitos.'
    )
    data_referencia = forms.DateField(
        label='Data de Referência da Base',
        help_text='Data a ser associada aos registros importados (crucial para o filtro).',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )


# --- Formulário de Filtros para o Dashboard Parcel Sweeper (Ajustado para Múltipla Seleção) ---
class ParcelFilterForm(forms.Form):
    # Filtros de Data (sem valor inicial aqui, será setado em __init__)
    data_inicio = forms.DateField(
        label="Data Início (Arquivo)",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    data_fim = forms.DateField(
        label="Data Fim (Arquivo)",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )

    # 🔑 AJUSTE CRUCIAL: MUDANDO PARA SELEÇÃO MÚLTIPLA
    final_status = forms.MultipleChoiceField(
        label="Status Final",
        required=False,
        # O 'size: 6' torna a caixa maior, facilitando a visualização e seleção com CTRL/CMD
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 6}) 
    )
    
    # Sort Code (Mantido como seleção única)
    sort_code = forms.ChoiceField(
        label="Sort Code",
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # --- 1. Lógica para Datas Padrão (Último Carregamento) ---
        try:
            data_padrao_fim = Parcel.objects.latest('data_referencia').data_referencia
        except Parcel.DoesNotExist:
            data_padrao_fim = timezone.localdate()

        data_padrao_inicio = data_padrao_fim - timedelta(days=30) 
        
        # Define os valores iniciais SE NÃO HOUVER DADOS NA URL (request.GET)
        if 'data_inicio' not in self.data:
            self.fields['data_inicio'].initial = data_padrao_inicio
        if 'data_fim' not in self.data:
            self.fields['data_fim'].initial = data_padrao_fim

        # --- 2. Lógica de População de Choices ---
        
        # Final Status: 🔑 REMOVIDO ('', 'Todos') e ordenado.
        status_choices = [
            (s, s) 
            for s in Parcel.objects.values_list('final_status', flat=True)
                        .distinct()
                        .exclude(final_status__isnull=True)
                        .exclude(final_status='')
                        .order_by('final_status') # 🔑 Adicionado para melhor UX
        ]
        self.fields['final_status'].choices = status_choices
        
        # Sort Code: Mantido
        sort_code_choices = [('', 'Todos')] + [
            (sc, sc) 
            for sc in Parcel.objects.values_list('sort_code', flat=True)
                        .distinct()
                        .exclude(sort_code__isnull=True)
                        .exclude(sort_code='')
        ]
        self.fields['sort_code'].choices = sort_code_choices