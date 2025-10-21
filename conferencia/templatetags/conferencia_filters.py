# conferencia/templatetags/conferencia_filters.py

from django import template

# Objeto de registro do Django para templates
register = template.Library()

@register.filter
def sub(value, arg):
    """Subtrai o argumento (arg) do valor (value).
    
    Exemplo de uso no template: {{ count|sub:500 }}
    """
    try:
        # Tenta converter para inteiro
        return int(value) - int(arg)
    except (ValueError, TypeError):
        try:
            # Tenta converter para float se a conversão para int falhar
            return float(value) - float(arg)
        except (ValueError, TypeError):
            # Retorna o valor original (ou vazio) se não for numérico
            return value