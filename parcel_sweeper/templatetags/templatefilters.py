# parcel_sweeper/templatetags/templatefilters.py

from django import template
from django.template.defaultfilters import slugify as default_slugify
# 🔑 NOVAS IMPORTAÇÕES NECESSÁRIAS
from urllib.parse import parse_qsl, urlencode 

register = template.Library()

@register.filter
def slugify(value):
    return default_slugify(value)

@register.filter
def add(value, arg):
    """Adiciona dois argumentos."""
    try:
        # Tenta a soma como inteiro ou float
        return float(value) + float(arg)
    except (ValueError, TypeError):
        # Retorna o valor original se a soma não for possível
        return value

# 🔑 NOVO FILTRO PARA CORRIGIR O ERRO
@register.filter
def exclude_page(query_string):
    """
    Remove o parâmetro 'page' de uma query string (URL-encoded).
    Isso é usado para garantir que o link de paginação não duplique o parâmetro 'page'.
    """
    # 1. Analisa a string (ex: 'name=Mis-sorted&page=2') em pares [('name', 'Mis-sorted'), ('page', '2')]
    query_list = parse_qsl(query_string)
    
    # 2. Filtra para remover o parâmetro 'page'
    # Converte 'page' para minúsculas para garantir que a comparação funcione, caso exista variação
    filtered_query_list = [(k, v) for k, v in query_list if k.lower() != 'page']
    
    # 3. Reconstrói a query string
    return urlencode(filtered_query_list)