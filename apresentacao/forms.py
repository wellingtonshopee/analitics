# apresentacao/forms.py
from django import forms
from django.forms.models import inlineformset_factory
from .models import Apresentacao, Topico, Card

# 1. Formulário principal (para a data)
class ApresentacaoForm(forms.ModelForm):
    class Meta:
        model = Apresentacao
        fields = ['data_apresentacao']
        widgets = {
            'data_apresentacao': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

# 2. Formulário para cada Card (a métrica individual)
class CardForm(forms.ModelForm):
    # Definir 'valor' como HiddenInput se você usar 'valor_formatado' como o campo principal
    valor = forms.DecimalField(
        required=False, 
        widget=forms.HiddenInput(),
    ) 

    class Meta:
        model = Card
        fields = ['titulo', 'valor_formatado', 'cor', 'ordem', 'valor', 'id']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'valor_formatado': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Ex: R$ 50k ou 98.5%'}),
            'cor': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'ordem': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'readonly': 'readonly'}),
            # O ID é necessário para edição/deleção, mas deve estar escondido
            'id': forms.HiddenInput(),
        }

# 3. Formset de Cards (Permite múltiplos cards dentro de um tópico)
CardFormSet = inlineformset_factory(
    Topico, # Modelo Pai
    Card,   # Modelo Filho
    form=CardForm,
    fields=['titulo', 'valor_formatado', 'cor', 'ordem', 'valor'],
    extra=1, # Adiciona 1 formulário vazio por padrão
    can_delete=True # Permite excluir cards
)


# 4. Formulário para cada Tópico
class TopicoForm(forms.ModelForm):
    class Meta:
        model = Topico
        fields = ['titulo', 'ordem', 'id']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'ordem': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'readonly': 'readonly'}),
            'id': forms.HiddenInput(),
        }

# 5. Formset de Tópicos (Permite múltiplos tópicos dentro da apresentação)
TopicoFormSet = inlineformset_factory(
    Apresentacao, # Modelo Pai
    Topico,       # Modelo Filho
    form=TopicoForm,
    fields=['titulo', 'ordem', 'id'],
    extra=1,
    can_delete=True,
)