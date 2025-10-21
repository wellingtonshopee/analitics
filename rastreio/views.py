# rastreio/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse # Importação necessária para exportação CSV
import csv # Importação necessária para exportação CSV
import io
from datetime import datetime
from django.db import IntegrityError
from django.db.models import Count, Q  # Importando Q para filtros complexos
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import pandas as pd
import numpy as np


from .forms import UploadRastreioForm
from .models import Rastreio

# Constante para o hub de Muriaé
MURIAE_HUB = 'LM Hub_MG_Muriaé'
REGISTROS_POR_PAGINA = 50

# Mapeamento dos nomes do CSV para os nomes do modelo Rastreio
COLUNA_MODELO_MAP = {
    'Order ID': 'order_id',
    'SLS Tracking Number': 'sls_tracking_number',
    'Shopee Order SN': 'shopee_order_sn',
    'Longitude': 'longitude',
    'Latitude': 'latitude',
    'Sort Code Name': 'sort_code_name',
    'Zipcode Name': 'zipcode_name',
    'Buyer Name': 'buyer_name',
    'Buyer Phone': 'buyer_phone',
    'Buyer Address': 'buyer_address',
    'Location Type': 'location_type',
    'Postal Code': 'postal_code',
    'Driver ID': 'driver_id',
    'Driver Name': 'driver_name',
    'Driver Phone': 'driver_phone',
    'LM Hub Receive time': 'lm_hub_receive_time',
    'Current Station Received Time': 'current_station_received_time',
    'Current Station': 'current_station',
    'Status': 'status',
    'Return Destination': 'return_destination',
    'Shop ID': 'shop_id',
    'Shop Category': 'shop_category',
    'Inbound 3PL': 'inbound_3pl',
    'Outbound 3PL': 'outbound_3pl',
    'Channel': 'channel',
    '3PL TN': '_3pl_tn',
    'Destination Hub': 'destination_hub',
    'Zone': 'zone',
    'Calculation Status': 'calculation_status',
    'Specical DG Type': 'specical_dg_type',
}

def converter_data_para_db(valor):
    """Converte um valor de data/hora comum para o formato aceito pelo DateField."""
    if pd.isna(valor) or valor in ('', 'N/A'):
        return None
    
    # Tenta vários formatos
    formatos_a_tentar = [
        '%Y-%m-%d',  # YYYY-MM-DD
        '%m/%d/%Y',  # MM/DD/YYYY
        '%d/%m/%Y',  # DD/MM/YYYY
        '%Y-%m-%d %H:%M:%S',
        '%m/%d/%Y %H:%M:%S',
        '%d/%m/%Y %H:%M:%S',
    ]

    for formato in formatos_a_tentar:
        try:
            # Retorna apenas a parte da data
            return datetime.strptime(str(valor).split(' ')[0], formato.split(' ')[0]).date()
        except ValueError:
            continue
    
    return None # Retorna None se a conversão falhar

# ===================================================================================
# Views de Navegação
# ===================================================================================

@login_required
def menu_rastreio(request):
    """Exibe o menu de opções para a área de Rastreio."""
    return render(request, 'rastreio/menu_rastreio.html')


# ===================================================================================
# Views de Upload
# ===================================================================================

@login_required
def upload_csv_rastreio(request):
    """Permite o upload de um arquivo CSV de Rastreio e o processa."""
    
    # Colunas Mínimas Requeridas para garantir que o arquivo seja válido
    CRITICAL_COLUMNS = ['SLS Tracking Number', 'Order ID', 'Status']
    
    if request.method == 'POST':
        form = UploadRastreioForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo_csv = request.FILES['arquivo_csv']
            data_envio_arquivo = form.cleaned_data['data_envio_arquivo']

            # Verifica se o arquivo é CSV
            if not arquivo_csv.name.endswith('.csv'):
                messages.error(request, 'Erro: O arquivo deve ser no formato CSV.')
                return render(request, 'rastreio/upload_csv_rastreio.html', {'form': form})

            # Processamento do arquivo com pandas para melhor robustez
            try:
                # Lendo o arquivo diretamente para DataFrame
                df = pd.read_csv(io.TextIOWrapper(arquivo_csv, encoding='utf-8'), sep=',')
                
                # 🛠️ NOVO: Limpa espaços em branco nos nomes das colunas (robusto contra 'SLS Tracking Number ')
                df.columns = [col.strip() for col in df.columns]
                
                df = df.replace({np.nan: None, '': None}) # Substitui NaN e strings vazias por None

                objetos_para_criar = []
                
                # 🛠️ NOVO: Garante que APENAS as colunas CRÍTICAS existem
                if not all(col in df.columns for col in CRITICAL_COLUMNS):
                    missing_cols = [col for col in CRITICAL_COLUMNS if col not in df.columns]
                    messages.error(request, f"Erro: O arquivo CSV está faltando colunas críticas necessárias. Colunas ausentes: {', '.join(missing_cols)}. O upload foi cancelado.")
                    return render(request, 'rastreio/upload_csv_rastreio.html', {'form': form})

                
                # 🛠️ NOVO: Itera sobre as linhas, mapeando SÓ as colunas que existem no CSV
                for index, row in df.iterrows():
                    dados_rastreio = {} # Inicializa o dicionário para cada linha
                    
                    # Itera sobre o dicionário de mapeamento (CSV_coluna: model_campo)
                    for coluna_csv, campo_modelo in COLUNA_MODELO_MAP.items():
                        
                        # Verifica se a coluna do CSV existe no DataFrame
                        if coluna_csv in df.columns:
                            # Mapeia apenas as colunas existentes no arquivo atual
                            dados_rastreio[campo_modelo] = row[coluna_csv]


                    # Adiciona campos de controle
                    dados_rastreio['data_envio_arquivo'] = data_envio_arquivo
                    dados_rastreio['usuario_upload'] = request.user
                    
                    # Cria o objeto Rastreio
                    objetos_para_criar.append(Rastreio(**dados_rastreio))
                
                # Insere em lote no banco de dados para performance
                Rastreio.objects.bulk_create(objetos_para_criar, ignore_conflicts=True)
                
                total_processado = len(df)
                # Adiciona filtro por usuário para precisão, caso haja múltiplos uploads no mesmo dia
                total_importado = Rastreio.objects.filter(data_envio_arquivo=data_envio_arquivo, usuario_upload=request.user).count()

                messages.success(request, f'Sucesso! {total_importado} de {total_processado} registros de Rastreio importados para o dia {data_envio_arquivo.strftime("%d/%m/%Y")}. Registros duplicados foram ignorados.')
                return redirect('dashboard_rastreio')

            except IntegrityError:
                messages.error(request, 'Erro de integridade ao salvar. Verifique se há IDs duplicados na base de dados.')
            except Exception as e:
                messages.error(request, f'Erro inesperado no processamento do arquivo: {e}')
                print(f"Erro detalhado: {e}")
        else:
            # Se o formulário for inválido
            messages.error(request, 'Erro de validação no formulário. Verifique os campos.')
    else:
        form = UploadRastreioForm()

    return render(request, 'rastreio/upload_csv_rastreio.html', {'form': form})


# ===================================================================================
# Views de Dashboard
# ===================================================================================

@login_required
def dashboard_rastreio(request):
    """
    Exibe o dashboard de rastreio com filtros, KPIs e dados paginados.
    """
    
    # 1. Obtenção e Conversão dos Filtros da Requisição (GET)
    data_inicio_str = request.GET.get('data_inicio')
    data_fim_str = request.GET.get('data_fim')
    status_filtro = request.GET.get('status_filtro')
    hub_filtro = request.GET.get('hub_filtro')
    
    # 🌟 NOVO: Obtenção do filtro de busca global
    search_query = request.GET.get('q') 
    
    # Filtro de Exceção (somente_excecoes): Implementação para persistir a seleção no dashboard
    somente_excecoes = request.GET.get('somente_excecoes') == 'on'

    # QuerySet base
    queryset = Rastreio.objects.all()

    # 2. Aplicação dos Filtros
    
    # 🌟 NOVO: Filtro de Busca Global (Pesquisa em múltiplos campos)
    if search_query:
        queryset = queryset.filter(
            Q(sls_tracking_number__icontains=search_query) |
            Q(order_id__icontains=search_query) |
            Q(shopee_order_sn__icontains=search_query) |
            Q(status__icontains=search_query) |
            Q(current_station__icontains=search_query) |
            Q(destination_hub__icontains=search_query)
        )

    # Filtro de Data
    if data_inicio_str:
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            queryset = queryset.filter(data_envio_arquivo__gte=data_inicio)
        except ValueError:
            messages.error(request, "Formato de data de início inválido.")
    
    if data_fim_str:
        try:
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
            queryset = queryset.filter(data_envio_arquivo__lte=data_fim)
        except ValueError:
            messages.error(request, "Formato de data de fim inválido.")

    # Filtro de Status
    if status_filtro:
        queryset = queryset.filter(status=status_filtro)
    
    # Filtro de Destination Hub
    if hub_filtro:
        queryset = queryset.filter(destination_hub=hub_filtro)

    # Filtro de Exceção (Aplica no QuerySet principal para funcionar com Paginação)
    if somente_excecoes:
        # A exceção é: Status == 'LMHub_Received' E Destination Hub != 'LM Hub_MG_Muriaé'
        queryset = queryset.filter(
            Q(status='LMHub_Received') & ~Q(destination_hub=MURIAE_HUB)
        )
    
    # 3. Cálculo de KPIs e Dados Agregados
    total_registros = queryset.count()
    
    # Lista de opções para os filtros (para popular os dropdowns no template)
    status_opcoes = Rastreio.objects.values('status').annotate(count=Count('status')).exclude(Q(status__isnull=True) | Q(status='')).order_by('status')
    destination_hub_opcoes = Rastreio.objects.values('destination_hub').annotate(count=Count('destination_hub')).exclude(Q(destination_hub__isnull=True) | Q(destination_hub='')).order_by('destination_hub')
    
    # KPI: Total por Status (Top 10 para o card dinâmico)
    kpis_por_status = queryset.exclude(Q(status__isnull=True) | Q(status='')).values('status').annotate(
        count=Count('status')
    ).order_by('-count')[:10]
    
    
    # KPI: Total por Destination Hub (LM Hub_MG_Muriaé vs Outros)
    total_hub_muriae = queryset.filter(destination_hub=MURIAE_HUB).count()
    total_hub_outros = queryset.exclude(destination_hub=MURIAE_HUB).count()
    total_hub_diferente_muriae = total_hub_outros
    
    # Cálculo de Percentuais
    percentual_muriae = 0.0
    percentual_outros = 0.0
    
    if total_registros > 0:
        percentual_muriae = round((total_hub_muriae / total_registros) * 100, 1)
        percentual_outros = round((total_hub_outros / total_registros) * 100, 1)


    # 4. Paginação dos Dados da Tabela
    page = request.GET.get('page', 1)
    paginator = Paginator(queryset.order_by('-data_upload'), REGISTROS_POR_PAGINA) # Ordena pelo mais recente
    
    try:
        dados_paginados = paginator.page(page)
    except PageNotAnInteger:
        dados_paginados = paginator.page(1)
    except EmptyPage:
        dados_paginados = paginator.page(paginator.num_pages)
        
    # Extrai os dados essenciais para exibição na tabela
    dados_tabela = dados_paginados.object_list.values(
        'sls_tracking_number', 
        'status', 
        'current_station', 
        'destination_hub'
    )
    
    # 5. Criação da String de Filtros para a URL (para paginação)
    url_params = ''
    
    # 🌟 NOVO: Adiciona a query de busca aos parâmetros
    if search_query:
        url_params += f'&q={search_query}'
        
    if data_inicio_str:
        url_params += f'&data_inicio={data_inicio_str}'
        
    if data_fim_str:
        url_params += f'&data_fim={data_fim_str}'
        
    if status_filtro:
        url_params += f'&status_filtro={status_filtro}'
        
    if hub_filtro:
        url_params += f'&hub_filtro={hub_filtro}'

    if somente_excecoes: # Adiciona o parâmetro de exceção
        url_params += f'&somente_excecoes=on'
        

    # 6. Context
    context = {
        'titulo': 'Dashboard Rastreio de Pedidos',
        
        # Filtros
        'data_inicio_str': data_inicio_str,
        'data_fim_str': data_fim_str,
        'status_filtro': status_filtro,
        'hub_filtro': hub_filtro,
        'somente_excecoes': somente_excecoes,
        'search_query': search_query, # 🌟 NOVO: Adicionado ao contexto
        
        # Opcões de Filtro
        'status_opcoes': status_opcoes,
        'destination_hub_opcoes': destination_hub_opcoes,
        
        # KPIs
        'total_registros': total_registros,
        'kpis_por_status': kpis_por_status,
        
        # KPIs Muriaé vs Outros
        'total_hub_muriae': total_hub_muriae,
        'total_hub_outros': total_hub_outros,
        'percentual_muriae': percentual_muriae,
        'percentual_outros': percentual_outros,
        'total_hub_diferente_muriae': total_hub_diferente_muriae,
        
        # Paginação
        'dados_tabela': dados_tabela,
        'paginator': dados_paginados, # Objeto Page para a tabela principal
        'url_params': url_params,
    }

    return render(request, 'rastreio/dashboard_rastreio.html', context)

@login_required
def detalhe_rastreio_view(request):
    """
    Exibe a tabela de rastreios detalhada, aplicando os filtros passados por URL.
    Ideal para ser usada quando um KPI é clicado no dashboard.
    """
    
    # 1. Obtenção dos Filtros (Deve ser o mesmo do dashboard)
    data_inicio_str = request.GET.get('data_inicio')
    data_fim_str = request.GET.get('data_fim')
    status_filtro = request.GET.get('status_filtro')
    hub_filtro = request.GET.get('hub_filtro')
    somente_excecoes = request.GET.get('somente_excecoes') == 'on' 

    # QuerySet base
    registros_rastreio = Rastreio.objects.all()

    # 2. Construção do QuerySet (Usando Q para consistência com dashboard)
    filtros_q = Q()
    
    # Filtro de Data
    if data_inicio_str:
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            filtros_q &= Q(data_envio_arquivo__gte=data_inicio)
        except ValueError:
            pass
            
    if data_fim_str:
        try:
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
            filtros_q &= Q(data_envio_arquivo__lte=data_fim)
        except ValueError:
            pass

    # Filtrar por status (Filtro vindo do KPI)
    if status_filtro:
        filtros_q &= Q(status__iexact=status_filtro)
    
    if hub_filtro:
        filtros_q &= Q(destination_hub__iexact=hub_filtro)

    # Lógica de "somente_excecoes" (Aplicada corretamente)
    if somente_excecoes:
        # Exceção é: Status == 'LMHub_Received' E Destination Hub != 'LM Hub_MG_Muriaé'
        filtros_q &= Q(status__iexact='LMHub_Received') & ~Q(destination_hub__iexact=MURIAE_HUB)
    
    # Aplica todos os filtros e ordena
    registros_rastreio = registros_rastreio.filter(filtros_q).order_by('-data_upload')

    # 4. Paginação
    page = request.GET.get('page', 1)
    paginator_obj = Paginator(registros_rastreio, REGISTROS_POR_PAGINA) 

    try:
        registros_paginados = paginator_obj.page(page)
    except (PageNotAnInteger, EmptyPage):
        registros_paginados = paginator_obj.page(1)

    # 5. Parâmetros de URL para links de paginação
    url_params = ''
    if data_inicio_str: url_params += f'&data_inicio={data_inicio_str}'
    if data_fim_str: url_params += f'&data_fim={data_fim_str}'
    if status_filtro: url_params += f'&status_filtro={status_filtro}'
    if hub_filtro: url_params += f'&hub_filtro={hub_filtro}'
    if somente_excecoes: url_params += f'&somente_excecoes=on'
        
    # 6. Contexto (Ajustado para o template)
    context = {
        'titulo': f'Detalhes do Rastreio: {status_filtro}' if status_filtro else 'Detalhes do Rastreio',
        
        # O template espera 'paginator' para info e 'dados_tabela' para o loop
        'paginator': registros_paginados, # Objeto Page (para número da página e navegação)
        'dados_tabela': registros_paginados.object_list, # Lista de objetos para o loop da tabela (CORREÇÃO CRÍTICA)
        
        'total_registros': registros_rastreio.count(),
        
        # Passa os filtros
        'data_inicio_str': data_inicio_str,
        'data_fim_str': data_fim_str,
        'status_filtro': status_filtro,
        'hub_filtro': hub_filtro,
        'somente_excecoes': somente_excecoes,
        
        # O template usa 'url_params' na navegação e 'url_base_detalhe' nos botões.
        'url_params': url_params,
        'url_base_detalhe': url_params, # Definido para corrigir o uso nos botões de voltar/exportar
    }

    return render(request, 'rastreio/detalhe_rastreio.html', context)

# ===================================================================================
# Views de Exportação (FUNÇÃO ADICIONADA)
# ===================================================================================

@login_required
def exportar_csv_rastreio(request): 
    """
    Exporta os dados de rastreio para um arquivo CSV, 
    aplicando os mesmos filtros GET usados no detalhe e no dashboard.
    """
    
    # 1. Obter e Tratar Filtros (Lógica idêntica ao detalhe/dashboard)
    data_inicio_str = request.GET.get('data_inicio')
    data_fim_str = request.GET.get('data_fim')
    status_filtro = request.GET.get('status_filtro')
    hub_filtro = request.GET.get('hub_filtro')
    somente_excecoes = request.GET.get('somente_excecoes') == 'on'

    queryset = Rastreio.objects.all()
    filtros_q = Q()
    
    if data_inicio_str:
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            filtros_q &= Q(data_envio_arquivo__gte=data_inicio)
        except ValueError:
            pass
            
    if data_fim_str:
        try:
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
            filtros_q &= Q(data_envio_arquivo__lte=data_fim)
        except ValueError:
            pass

    if status_filtro:
        filtros_q &= Q(status__iexact=status_filtro)
    
    if hub_filtro:
        filtros_q &= Q(destination_hub__iexact=hub_filtro)
        
    if somente_excecoes:
        filtros_q &= Q(status__iexact='LMHub_Received') & ~Q(destination_hub__iexact=MURIAE_HUB)

    # 2. Filtrar dados
    dados_para_exportar = queryset.filter(filtros_q).values_list(
        'order_id', 'sls_tracking_number', 'shopee_order_sn', 'status', 
        'current_station', 'destination_hub', 'data_envio_arquivo', 
        'data_upload', 'usuario_upload__username' 
    )
    
    # 3. Preparar a Resposta HTTP
    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="rastreios_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'},
    )
    
    writer = csv.writer(response)
    
    # Cabeçalho do CSV
    writer.writerow([
        'Order ID', 'SLS Tracking Number', 'Shopee Order SN', 'Status', 
        'Current Station', 'Destination Hub', 'Data Arquivo', 'Data Upload', 'Usuário Upload'
    ])
    
    # Escrever dados
    writer.writerows(dados_para_exportar)
    
    return response