from django import forms

class UploadRastreioForm(forms.Form):
    arquivo_csv = forms.FileField(
        label='Arquivo CSV de Rastreio',
        help_text='Selecione o arquivo forward_order.csv'
    )
    data_envio_arquivo = forms.DateField(
        label='Data de Envio do Arquivo',
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='Informe a data que será associada a este lote de dados.'
    )