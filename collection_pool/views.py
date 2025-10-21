# collection_pool/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import csv
import io
from datetime import datetime
from django.db import IntegrityError
import pandas as pd
from django.contrib.postgres.aggregates import ArrayAgg
from django.template.defaultfilters import slugify
from django.contrib import messages

from .forms import UploadPoolForm, PoolFilterForm
from .models import Pool
from django.db.models import Count, Q
from django.core.paginator import Paginator

# Mapeamento dos nomes do CSV/Excel para os nomes do modelo Pool
COLUNA_MODELO_MAP_POOL = {
    'Shipment Id': 'shipment_id',
    'Zipcode': 'zipcode',
    'Destination Address': 'destination_address',
    'Neighborhood': 'neighborhood',
    'City': 'city',
    'Region': 'region',
    'Cluster': 'cluster',
    'Address Type': 'address_type',
    'LH Trip': 'lh_trip',
    'Destination Hub': 'destination_hub',
    'Status': 'status',
    'Length(cm)': 'length_cm',
    'Width(cm)': 'width_cm',
    'Height(cm)': 'height_cm',
    'Weight(kg)': 'weight_kg',
    'Dimension Source Type': 'dimension_source_type',
    'TO ID': 'to_id',
}

@login_required
def upload_pool_csv(request):
    if request.method == 'POST':
        form = UploadPoolForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['arquivo_csv']
            data_envio_arquivo = form.cleaned_data['data_envio_arquivo']
            file_name = uploaded_file.name

            try:
                # LÓGICA DE DETECÇÃO E LEITURA DE ARQUIVO (CSV ou XLSX)
                if file_name.endswith('.csv'):
                    # Lendo CSV com codificação latin-1 (comum em arquivos brasileiros)
                    file_data = uploaded_file.read().decode("latin-1")
                    df = pd.read_csv(io.StringIO(file_data))
                elif file_name.endswith(('.xlsx', '.xls')):
                    # Lendo XLSX (Excel) diretamente (requer openpyxl)
                    df = pd.read_excel(uploaded_file)
                else:
                    messages.error(request, "Erro ao carregar dados. Formato de arquivo não suportado (use .csv, .xlsx ou .xls).")
                    return redirect('upload_pool_csv')

                # Limpar espaços nos cabeçalhos da tabela e renomear colunas
                df.columns = df.columns.str.strip()
                df.rename(columns=COLUNA_MODELO_MAP_POOL, inplace=True)
                
                # Obter lista de campos válidos no modelo Pool
                valid_fields = [field.name for field in Pool._meta.fields]
                
                novos_itens = []
                erros_linha = 0
                
                # Itera sobre o DataFrame do Pandas
                for index, row in df.iterrows():
                    pool_data = {}
                    
                    try:
                        # Converte a linha do Pandas para um dicionário Python
                        raw_data = row.to_dict()
                        
                        # Limpeza e validação dos dados
                        for model_field in raw_data:
                            value = raw_data.get(model_field)
                            
                            if model_field in valid_fields:
                                
                                # 1. Tratamento de valores NaN (nulos do Pandas)
                                if pd.isna(value):
                                    pool_data[model_field] = None
                                    continue
                                
                                # 2. Tratamento de campos numéricos
                                if model_field in ['length_cm', 'width_cm', 'height_cm', 'weight_kg']:
                                    try:
                                        # Assumindo que o Pandas já tratou a vírgula/ponto, mas garantindo que é float
                                        pool_data[model_field] = float(value)
                                    except (ValueError, TypeError):
                                        pool_data[model_field] = None 
                                # 3. Tratamento de strings
                                elif isinstance(value, str):
                                    pool_data[model_field] = value.strip()

                        # Adiciona campos de controle
                        pool_data['data_envio_arquivo'] = data_envio_arquivo
                        pool_data['usuario_upload'] = request.user
                        
                        # Validação obrigatória
                        if not pool_data.get('shipment_id'):
                            erros_linha += 1
                            continue
                            
                        pool_obj = Pool(**pool_data)
                        novos_itens.append(pool_obj)
                        
                    except Exception:
                        erros_linha += 1
                        
                # 🚀 Lógica de UPSERT
                # Define os campos a serem atualizados em caso de conflito (shipment_id duplicado)
                update_fields = [
                    'zipcode', 'destination_address', 'neighborhood', 'city', 'region', 'cluster', 
                    'address_type', 'lh_trip', 'destination_hub', 'status', 
                    'length_cm', 'width_cm', 'height_cm', 'weight_kg', 'dimension_source_type', 'to_id',
                    # Campos de controle que devem refletir os dados mais recentes:
                    'data_envio_arquivo', 'usuario_upload' 
                ]
                
                # Executa o bulk_create com upsert: Insere novos, atualiza existentes
                Pool.objects.bulk_create(
                    novos_itens, 
                    update_conflicts=True, 
                    unique_fields=['shipment_id'], # A chave de unicidade
                    update_fields=update_fields    # Os campos que devem ser atualizados
                )

                # Mensagem de sucesso ajustada para refletir o comportamento de UPSERT:
                itens_processados = len(df) - erros_linha
                messages.success(request, f"Upload concluído. Foram processadas {itens_processados} linhas válidas. Os registros novos foram **inseridos** e os existentes foram **atualizados** com sucesso.")
                return redirect('upload_pool_csv') 

            except Exception as e:
                # 🚨 CORREÇÃO APLICADA AQUI
                # Removemos a tentativa de usar 'itens_processados' (ou 'itens_processadas')
                # que causava o erro se a exceção ocorresse antes dela ser definida.
                print(f"Erro detalhado no processamento: {e}") # Para debug no console do servidor
                messages.error(request, "Erro ao carregar dados. Verifique o formato do arquivo ou se há dados inválidos.")
                return redirect('upload_pool_csv')

        else:
            messages.error(request, "Erro ao carregar dados. Verifique se o arquivo e a data foram selecionados corretamente.")
    else:
        form = UploadPoolForm()
        
    context = {
        'form': form, 
        'titulo': 'Upload Collection Pool',
        'subtitulo': 'Carregamento da Base de Pedidos para Coleta (Collection Pool)'
    }
    
    return render(request, 'collection_pool/upload_pool_csv.html', context)

@login_required
def menu_pool(request):
    """Renderiza o menu de ações do Collection Pool."""
    return render(request, 'collection_pool/menu_pool.html', {'titulo': 'Menu Collection Pool'})

@login_required
def dashboard_pool(request):
    """Dashboard de Collection Pool com filtros e KPIs."""
    
    # Base queryset
    queryset = Pool.objects.all()
    
    # 1. Obter e popular o formulário
    from .forms import PoolFilterForm # Reafirmando o import aqui por segurança
    form = PoolFilterForm(request.GET or None)

    # 💡 NOVO: Capturar os parâmetros GET para manter os filtros ativos ao navegar
    filter_query_params = request.GET.copy()
    # Opcional: Remova parâmetros que não são filtros de dados (como 'page')
    if 'page' in filter_query_params:
        del filter_query_params['page']
        
    # Gerar a string de query (ex: "data_inicio=2025-10-01&status=Received")
    filter_query_string = filter_query_params.urlencode()
    # FIM NOVO: Captura de Query String

    if form.is_valid():
        # 2. Aplicar Filtros
        
        # Filtro de Data
        data_inicio = form.cleaned_data.get('data_inicio')
        data_fim = form.cleaned_data.get('data_fim')
        
        if data_inicio:
            queryset = queryset.filter(data_envio_arquivo__gte=data_inicio)
        if data_fim:
            # Inclui o dia final
            queryset = queryset.filter(data_envio_arquivo__lte=data_fim) 
            
        # Filtros de Seleção (Status, City, Hub)
        status = form.cleaned_data.get('status')
        city = form.cleaned_data.get('city')
        destination_hub = form.cleaned_data.get('destination_hub')
        
        if status:
            queryset = queryset.filter(status=status)
        if city:
            queryset = queryset.filter(city=city)
        if destination_hub:
            queryset = queryset.filter(destination_hub=destination_hub)

    # 3. Calcular KPIs (Usando Aggregation no queryset filtrado)
    kpis = {}
    
    # KPI 1: Total de Registros
    total_registros = queryset.count()
    kpis['total_registros'] = total_registros

    # NOVO KPI: Total para cada Status diferente (Dinâmico)
    # Exclui valores nulos ou vazios de 'status'
    kpis['total_por_status_dinamico'] = queryset.exclude(Q(status__isnull=True) | Q(status='')).values('status').annotate(
        count=Count('status')
    ).order_by('-count')

    # KPI 2: Total para cada City diferente (Top 5 para exibição)
    kpis['total_por_cidade'] = queryset.exclude(Q(city__isnull=True) | Q(city='')).values('city').annotate(
        count=Count('city')
    ).order_by('-count')

    # KPI 3: Total por Status (LMHub_Received vs Outros)
    LMHUB_RECEIVED_STATUS = 'LMHub_Received'
    kpis['status_received'] = queryset.filter(status=LMHUB_RECEIVED_STATUS).count()
    kpis['status_outros'] = queryset.exclude(status=LMHUB_RECEIVED_STATUS).count()

    # KPI 4: Total por Destination Hub (LM Hub_MG_Muriaé vs Outros)
    MURIAE_HUB = 'LM Hub_MG_Muriaé'
    kpis['hub_muriae'] = queryset.filter(destination_hub=MURIAE_HUB).count()
    kpis['hub_outros'] = queryset.exclude(destination_hub=MURIAE_HUB).count()

    # 4. Contexto para o template
    context = {
        'form': form,
        'kpis': kpis,
        'titulo': 'Dashboard Collection Pool',
        'total_registros': total_registros,
        'filter_query_string': filter_query_string # 💡 Adiciona a query string ao contexto
    }
    
    return render(request, 'collection_pool/dashboard_pool.html', context)

@login_required
def pool_detail_list(request, status_slug):
    """
    Exibe uma lista paginada dos itens da Collection Pool filtrados por Status,
    usando o slug da URL para encontrar o status original do DB.
    """
    
    # 1. Lógica de Decodificação e Busca do Status Original
    
    # Busca todos os status distintos (válidos) no banco de dados
    distinct_statuses = Pool.objects.values_list('status', flat=True).distinct().exclude(status__isnull=True).exclude(status='')
    
    # Tenta encontrar o status original (Case-Sensitive) que gerou o slug da URL
    original_status = None
    for s in distinct_statuses:
        # Compara o slug da URL com o slug gerado a partir do status do DB
        if slugify(s) == status_slug:
            original_status = s
            break

    if original_status:
        status_filtrado = original_status
        # Filtra usando o status original (case-sensitive, para ser exato)
        queryset = Pool.objects.filter(status=status_filtrado)
    else:
        # Se não encontrou, o status_slug é inválido ou não há dados.
        # Usamos uma string limpa para o título e um Queryset vazio.
        status_filtrado = status_slug.replace('-', ' ').title()
        queryset = Pool.objects.none() # Queryset vazio

    # ----------------------------------------------------------------------------------
    # 💡 CORREÇÃO APLICADA: Aplica os filtros adicionais (data, city, hub) passados via URL
    form = PoolFilterForm(request.GET)
    if form.is_valid():
        data_inicio = form.cleaned_data.get('data_inicio')
        data_fim = form.cleaned_data.get('data_fim')
        city = form.cleaned_data.get('city')
        destination_hub = form.cleaned_data.get('destination_hub')
        
        # Aplica os filtros se existirem (ignora 'status' pois já está filtrado pelo slug)
        if data_inicio:
            queryset = queryset.filter(data_envio_arquivo__gte=data_inicio)
        if data_fim:
            # Inclui o dia final
            queryset = queryset.filter(data_envio_arquivo__lte=data_fim)
        # Note: 'status' é ignorado aqui, pois já foi filtrado acima
        if city:
            queryset = queryset.filter(city=city)
        if destination_hub:
            queryset = queryset.filter(destination_hub=destination_hub)
    # ----------------------------------------------------------------------------------
    
    
    # 2. Capturar a Query String para o botão 'Voltar'
    filter_query_params = request.GET.copy()
    if 'page' in filter_query_params:
        del filter_query_params['page']
    filter_query_string = filter_query_params.urlencode()
    
    
    # 3. Aplica filtros de pesquisa (mantido do código anterior, opcional)
    search_query = request.GET.get('q')
    if search_query:
        # Note: Esta linha só é executada se houver um 'q' na URL.
        queryset = queryset.filter(
            Q(shipment_id__icontains=search_query) | 
            Q(city__icontains=search_query)
        )

    # Ordena o resultado final
    queryset = queryset.order_by('-data_envio_arquivo', 'shipment_id')


    # 4. Paginação
    paginator = Paginator(queryset, 50) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 5. Contexto
    context = {
        'titulo': f'Detalhes do Status: {status_filtrado}',
        'page_obj': page_obj,
        'status_filtrado': status_filtrado,
        'search_query': search_query,
        'total_registros': queryset.count(),
        'filter_query_string': filter_query_string # Adiciona para o link Voltar
    }
    
    return render(request, 'collection_pool/pool_detail_list.html', context)

@login_required
def delete_pool_records(request):
    """Lida com a requisição POST para deletar múltiplos registros do Pool."""
    if request.method == 'POST':
        # Recebe a lista de IDs a serem deletados (nome 'selected_records' do checkbox no HTML)
        selected_ids = request.POST.getlist('selected_records')
        
        if not selected_ids:
            messages.error(request, 'Nenhum registro foi selecionado para remoção.')
            # Redireciona para a página anterior (ex: a página de detalhes da cidade)
            return redirect(request.META.get('HTTP_REFERER', 'dashboard_pool')) 
        
        # Filtra os objetos Pool pelos IDs fornecidos
        registros_para_deletar = Pool.objects.filter(id__in=selected_ids)
        
        # Conta e executa a exclusão
        count = registros_para_deletar.count()
        registros_para_deletar.delete()
        
        if count > 0:
            messages.success(request, f'{count} registro(s) removido(s) permanentemente da Pool com sucesso.')
        else:
            messages.warning(request, 'Os registros selecionados não foram encontrados no banco de dados.')

        # Redireciona para a página que enviou o formulário (geralmente a lista de detalhes)
        return redirect(request.META.get('HTTP_REFERER', 'dashboard_pool'))
        
    # Se for GET, redireciona para o dashboard por segurança
    return redirect('dashboard_pool')

@login_required
def pool_detail_list_by_city(request, city_slug):
    """
    Exibe uma lista paginada dos itens da Collection Pool filtrados por Cidade.
    """
    
    # 1. Lógica de Decodificação e Busca da Cidade Original (Robustez)
    
    # Busca todas as cidades distintas (válidas) no banco de dados
    distinct_cities = Pool.objects.values_list('city', flat=True).distinct().exclude(city__isnull=True).exclude(city='')
    
    # Tenta encontrar a cidade original (Case-Sensitive) que gerou o slug da URL
    original_city = None
    for c in distinct_cities:
        # 💡 Esta é a lógica robusta que valida o slug
        if slugify(c) == city_slug:
            original_city = c
            break

    if original_city:
        city_filtrada = original_city
        # Filtra usando a cidade original (case-sensitive)
        queryset = Pool.objects.filter(city=city_filtrada)
    else:
        # Se não encontrou, usa um queryset vazio para evitar erros e 
        # define um nome formatado apenas para exibição no título.
        city_filtrada = city_slug.replace('-', ' ').title()
        queryset = Pool.objects.none() 

    # ----------------------------------------------------------------------------------
    # 💡 CORREÇÃO APLICADA: Aplica os filtros adicionais (data, status, hub) passados via URL
    form = PoolFilterForm(request.GET)
    if form.is_valid():
        data_inicio = form.cleaned_data.get('data_inicio')
        data_fim = form.cleaned_data.get('data_fim')
        status = form.cleaned_data.get('status')
        destination_hub = form.cleaned_data.get('destination_hub')
        
        # Aplica os filtros se existirem (ignora 'city' pois já foi filtrada pelo slug)
        if data_inicio:
            queryset = queryset.filter(data_envio_arquivo__gte=data_inicio)
        if data_fim:
            # Inclui o dia final
            queryset = queryset.filter(data_envio_arquivo__lte=data_fim)
        if status:
            queryset = queryset.filter(status=status)
        # Note: 'city' é ignorado aqui, pois já foi filtrado acima
        if destination_hub:
            queryset = queryset.filter(destination_hub=destination_hub)
    # ----------------------------------------------------------------------------------
    
    # 2. Capturar a Query String para o botão 'Voltar'
    filter_query_params = request.GET.copy()
    if 'page' in filter_query_params:
        del filter_query_params['page']
    filter_query_string = filter_query_params.urlencode()
    
    # 3. Aplica filtros de pesquisa
    search_query = request.GET.get('q')
    if search_query:
        queryset = queryset.filter(
            Q(shipment_id__icontains=search_query) | 
            Q(status__icontains=search_query)
        )

    # Ordena o resultado final
    queryset = queryset.order_by('-data_envio_arquivo', 'shipment_id')


    # 4. Paginação
    paginator = Paginator(queryset, 50) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 5. Contexto
    context = {
        'titulo': f'Detalhes da Cidade: {city_filtrada}',
        'page_obj': page_obj,
        # Mantendo 'status_filtrado' para compatibilidade com o template pool_detail_list.html genérico
        'status_filtrado': city_filtrada, 
        'search_query': search_query,
        'total_registros': queryset.count(),
        'filter_query_string': filter_query_string # Adiciona para o link Voltar
    }
    
    # 6. Renderização (assumindo pool_detail_list.html é o template genérico)
    return render(request, 'collection_pool/pool_detail_list.html', context)