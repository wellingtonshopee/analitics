# conferencia/forms.py

from django import forms

class UploadArquivoForm(forms.Form):
    """Formulário para upload simultâneo dos arquivos Lista A e Lista B."""
    
    # Campo para a Lista A
    lista_a = forms.FileField(
        label='Arquivo Lista A',
        help_text='Máximo 100 mil registros. Formato sugerido: CSV (apenas com o campo de comparação).',
        widget=forms.FileInput(attrs={'accept': '.csv, .txt, .xlsx'})
    )
    
    # Campo para a Lista B
    lista_b = forms.FileField(
        label='Arquivo Lista B',
        help_text='Máximo 100 mil registros. Formato sugerido: CSV (apenas com o campo de comparação).',
        widget=forms.FileInput(attrs={'accept': '.csv, .txt, .xlsx'})
    )
    
class ChecagemRapidaForm(forms.Form):
    """
    Formulário para a Checagem Rápida por texto colado.
    """
    lista_a = forms.CharField(
        label='Lista A (Colar Códigos)',
        widget=forms.Textarea(attrs={
            'rows': 10,
            'class': 'form-control',
            'placeholder': 'Cole os códigos da Lista A aqui (um por linha, máx. 1000 registros)'
        }),
        help_text='Máximo de 1000 registros. Códigos duplicados serão contados como um único item.',
        required=True
    )
    lista_b = forms.CharField(
        label='Lista B (Colar Códigos)',
        widget=forms.Textarea(attrs={
            'rows': 10,
            'class': 'form-control',
            'placeholder': 'Cole os códigos da Lista B aqui (um por linha, máx. 1000 registros)'
        }),
        help_text='Máximo de 1000 registros. Códigos duplicados serão contados como um único item.',
        required=True
    )

    def clean_lista_a(self):
        # Verifica se o número de linhas excede o limite (1000)
        data = self.cleaned_data['lista_a']
        # Divide por linha e remove entradas vazias (strip)
        codes = [c.strip() for c in data.splitlines() if c.strip()]
        if len(codes) > 1000:
            raise forms.ValidationError("A Lista A excede o limite de 1000 registros.")
        return data

    def clean_lista_b(self):
        # Verifica se o número de linhas excede o limite (1000)
        data = self.cleaned_data['lista_b']
        # Divide por linha e remove entradas vazias (strip)
        codes = [c.strip() for c in data.splitlines() if c.strip()]
        if len(codes) > 1000:
            raise forms.ValidationError("A Lista B excede o limite de 1000 registros.")
        return data

