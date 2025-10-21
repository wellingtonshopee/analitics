# collection_pool/forms.py

from django import forms
from .models import Pool # Importar o modelo Pool

# Se você já tem o UploadPoolForm, mantenha-o. Caso contrário, crie-o.
class UploadPoolForm(forms.Form):
    arquivo_csv = forms.FileField(
        label='Arquivo CSV ou XLSX da Collection Pool', 
        help_text='Formatos aceitos: .csv, .xlsx. Certifique-se de que os cabeçalhos estão corretos.'
    )
    data_envio_arquivo = forms.DateField(
        label='Data de Referência da Base',
        help_text='Data a ser associada aos registros importados (ex: data de extração da base).',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )


# 🚨 NOVO: Formulário de Filtros para o Dashboard
class PoolFilterForm(forms.Form):
    # Filtro de Data Início (com valor inicial para mostrar dados)
    data_inicio = forms.DateField(
        label="Data Início (Arquivo)",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    # Filtro de Data Fim
    data_fim = forms.DateField(
        label="Data Fim (Arquivo)",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )

    # Filtros de Seleção (populados dinamicamente)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populando choices com dados únicos do banco de dados
        status_choices = [('', 'Todos')] + list(set((s, s) for s in Pool.objects.values_list('status', flat=True).distinct().exclude(status__isnull=True).exclude(status='')))
        city_choices = [('', 'Todas')] + list(set((c, c) for c in Pool.objects.values_list('city', flat=True).distinct().exclude(city__isnull=True).exclude(city='')))
        hub_choices = [('', 'Todos')] + list(set((dh, dh) for dh in Pool.objects.values_list('destination_hub', flat=True).distinct().exclude(destination_hub__isnull=True).exclude(destination_hub='')))

        self.fields['status'] = forms.ChoiceField(
            label="Status",
            required=False,
            choices=status_choices,
            widget=forms.Select(attrs={'class': 'form-select'})
        )
        self.fields['city'] = forms.ChoiceField(
            label="Cidade",
            required=False,
            choices=city_choices,
            widget=forms.Select(attrs={'class': 'form-select'})
        )
        self.fields['destination_hub'] = forms.ChoiceField(
            label="Destination Hub",
            required=False,
            choices=hub_choices,
            widget=forms.Select(attrs={'class': 'form-select'})
        )