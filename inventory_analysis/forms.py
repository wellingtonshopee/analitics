# inventory_analysis/forms.py

from django import forms
from datetime import date

# Definições das Ações para o filtro (baseadas nas constantes e lógicas do views.py)
ACTION_CHOICES = [
    ('', '--- Todas as Ações Sugeridas ---'),
    ('OK', 'OK'),
    ('ADICIONAR', 'ADICIONAR'),
    ('IGNORAR', 'IGNORAR'),
    ('ROTEIRIZAR', 'ROTEIRIZAR'),
    ('VERIFICAR', 'VERIFICAR'),
]

class DateRangeForm(forms.Form):
    """Formulário simples para filtrar dados por um período de tempo e Ação Sugerida."""
    
    # Define o campo de data de início com o tipo 'date' para melhor UX
    data_inicio = forms.DateField(
        label='De:',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=date.today
    )
    
    # Define o campo de data final
    data_fim = forms.DateField(
        label='Até:',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=date.today
    )
    
    # NOVO CAMPO DE FILTRO POR AÇÃO SUGERIDA
    acao_sugerida = forms.ChoiceField(
        label='Ação Sugerida:',
        required=False,
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )