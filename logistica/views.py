# logistica/views.py

from django.shortcuts import render, redirect, get_object_or_404 
from django.contrib.auth.decorators import login_required
from .forms import DadosDiariosLogisticaForm
from .models import DadosDiariosLogistica
from django.contrib import messages
from django.db.models import Q, Sum 
from datetime import date, datetime 
from .forms import PeriodoFiltroForm 

@login_required
def inserir_dados_logistica(request):
    """View para inserir novos dados de logística."""
    if request.method == 'POST':
        form = DadosDiariosLogisticaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Os dados de logística foram salvos com sucesso!')
            # Redireciona para a lista para ver o novo item
            return redirect('logistica:listar_dados')
        else:
            messages.error(request, 'Erro ao salvar os dados. Verifique o formulário.')
    else:
        form = DadosDiariosLogisticaForm()
        
    context = {
        'form': form,
        'titulo': 'Inserir Dados Diários de Logística',
    }
    return render(request, 'logistica/inserir_dados.html', context)

@login_required
def listar_e_filtrar_dados(request):
    """View para listar todos os dados e permitir filtragem por data."""
    dados = DadosDiariosLogistica.objects.all().order_by('-data_envio')
    query = request.GET.get('q') # Pega o valor do campo de busca

    if query:
        # Tenta interpretar a busca como uma data (formato YYYY-MM-DD ou DD/MM/YYYY)
        try:
            # Tenta converter para o formato de data do banco
            if '/' in query:
                # Usamos datetime.strptime para parsear a data DD/MM/YYYY
                data_busca = datetime.strptime(query, '%d/%m/%Y').strftime('%Y-%m-%d')
            else:
                # Se for YYYY-MM-DD, passa direto
                data_busca = query
            
            # Filtra por data exata
            dados = dados.filter(data_envio=data_busca)
        except ValueError:
            # Se a busca não for uma data válida, retorna uma mensagem de erro e lista vazia
            messages.warning(request, f"O termo de busca '{query}' não corresponde a uma data válida (Ex: 2025-10-18 ou 18/10/2025).")
            dados = DadosDiariosLogistica.objects.none()
            
    context = {
        'titulo': 'Dados Diários de Logística',
        'dados': dados,
        'query_termo': query if query else '',
    }
    return render(request, 'logistica/listar_dados.html', context)


@login_required
def editar_dados_logistica(request, pk):
    """View para buscar e editar um registro existente pelo PK."""
    # Busca o objeto (registro) pelo ID ou retorna 404
    dados = get_object_or_404(DadosDiariosLogistica, pk=pk)
    
    if request.method == 'POST':
        # Carrega os dados submetidos E o registro existente (instance=dados)
        form = DadosDiariosLogisticaForm(request.POST, instance=dados)
        if form.is_valid():
            form.save()
            messages.success(request, f'Dados de {dados.data_envio.strftime("%d/%m/%Y")} atualizados com sucesso!')
            # Redireciona para a lista após salvar
            return redirect('logistica:listar_dados')
        else:
            messages.error(request, 'Erro ao atualizar os dados. Verifique o formulário.')
    else:
        # Carrega o formulário com os dados existentes para edição (GET)
        form = DadosDiariosLogisticaForm(instance=dados)
        
    context = {
        'form': form,
        'titulo': f'Editar Dados de {dados.data_envio.strftime("%d/%m/%Y")}',
        # Passa o objeto 'dados' para o template, caso precise de informações como a data
        'dados': dados, 
    }
    # Reutiliza o template de inserção (inserir_dados.html)
    return render(request, 'logistica/inserir_dados.html', context)

@login_required
def dashboard_logistica(request):
    """
    View para exibir os KPIs em formato de Cards (agregados) organizados por Temas.
    Inclui o cálculo da métrica de Missorted/Iniciados para o gráfico de velocímetro.
    """
    form = PeriodoFiltroForm(request.GET)
    data_inicio = None
    data_fim = None
    
    # 1. Aplicar Filtro de Período
    dados_filtrados = DadosDiariosLogistica.objects.all()

    if form.is_valid():
        data_inicio = form.cleaned_data.get('data_inicio')
        data_fim = form.cleaned_data.get('data_fim')
        
        if data_inicio:
            dados_filtrados = dados_filtrados.filter(data_envio__gte=data_inicio)
        if data_fim:
            dados_filtrados = dados_filtrados.filter(data_envio__lte=data_fim)

    # 2. Calcular Agregações (Somas para os KPIs)
    totais = dados_filtrados.aggregate(
        total_rotas=Sum('total_rotas'),
        total_pacotes_iniciados=Sum('total_pacotes_iniciados'),
        total_pacotes_finalizados=Sum('total_pacotes_finalizados'),
        total_pacotes_escaneados=Sum('total_pacotes_escaneados'),
        total_missorted=Sum('total_missorted'),
        total_missing_expedicao=Sum('total_missing_expedicao'),
        total_missing_parcel=Sum('missing_parcel'),
        total_reversa=Sum('total_reversa'),
        total_avaria_soc=Sum('avaria_soc'),
        total_avaria_hub=Sum('avaria_hub'),
        total_onhold=Sum('total_onhold'),
        total_onhold_devolvidos=Sum('onhold_devolvidos'),
        total_onhold_devolver=Sum('onhold_devolver'),
        total_backlog_agarrado=Sum('backlog_agarrado_varios_dias'),
        total_volumosos_hub=Sum('volumosos_no_hub'),
        total_pnr=Sum('pnr'),
        total_backlog_parcel=Sum('backlog_parcel'),
        total_pedidos_roteirizar_pool=Sum('pedidos_roteirizar_pool'),
    )

    # 3. Lógica do Gráfico de Velocímetro (KPI Missorted / Pacotes Iniciados)
    pacotes_iniciados = totais.get('total_pacotes_iniciados') or 0
    total_missorted = totais.get('total_missorted') or 0
    LIMITE_PERCENTUAL = 0.0067 # 0.67%
    
    performance = {
        'percentual': 0,
        'status': 'success', 
        'mensagem': 'Nenhum dado para calcular.',
    }
    
    if pacotes_iniciados > 0:
        percentual_missorted = total_missorted / pacotes_iniciados
        performance['percentual'] = round(percentual_missorted * 100, 4)

        if percentual_missorted > LIMITE_PERCENTUAL:
            performance['status'] = 'danger' # Vermelho
            performance['mensagem'] = f'Acima do limite de {LIMITE_PERCENTUAL*100:.2f}% (Meta não atingida!)'
        else:
            performance['status'] = 'success' # Verde
            performance['mensagem'] = f'Dentro do limite de {LIMITE_PERCENTUAL*100:.2f}%'
            
    # 4. Organização dos KPIs por Tema
    temas_kpis = {}

    # TEMA 1: Expedição - Carregamento
    temas_kpis['Expedição - Carregamento'] = {
        'kpis': [
            {'titulo': 'Total de Rotas', 'valor': totais.get('total_rotas') or 0, 'icone': 'fa-route', 'cor': 'primary'},
            {'titulo': 'Total Pacotes Iniciados', 'valor': totais.get('total_pacotes_iniciados') or 0, 'icone': 'fa-play', 'cor': 'info'},
            {'titulo': 'Total Pacotes Finalizados', 'valor': totais.get('total_pacotes_finalizados') or 0, 'icone': 'fa-check-circle', 'cor': 'success'},
            {'titulo': 'Total Escaneados', 'valor': totais.get('total_pacotes_escaneados') or 0, 'icone': 'fa-qrcode', 'cor': 'secondary'},
            {'titulo': 'Total Missing Expedição', 'valor': totais.get('total_missing_expedicao') or 0, 'icone': 'fa-minus-circle', 'cor': 'danger'},
            {'titulo': 'Total Missorted', 'valor': totais.get('total_missorted') or 0, 'icone': 'fa-times', 'cor': 'danger'},
        ],
        'performance_chart': performance
    }

    # TEMA 2: Inventário
    temas_kpis['Resultado Inventário'] = {
        'kpis': [
            {'titulo': 'Pedidos a Roteirizar Collection Pool', 'valor': totais.get('total_pedidos_roteirizar_pool') or 0, 'icone': 'fa-list-ol', 'cor': 'primary'},
            # COR ALTERADA: De 'warning' para 'info' (Azul Claro)
            {'titulo': 'Backlog Parcel Sweeper', 'valor': totais.get('total_backlog_parcel') or 0, 'icone': 'fa-box-open', 'cor': 'info'},
            # COR ALTERADA: De 'danger' para 'warning' (Amarelo)
            {'titulo': 'Missing Parcel Sweeper', 'valor': totais.get('total_missing_parcel') or 0, 'icone': 'fa-search-minus', 'cor': 'warning'},
            {'titulo': 'Total Aguardando Reversa', 'valor': totais.get('total_reversa') or 0, 'icone': 'fa-undo', 'cor': 'secondary'},
            {'titulo': 'Total Avaria SOC', 'valor': totais.get('total_avaria_soc') or 0, 'icone': 'fa-car-crash', 'cor': 'danger'},
            {'titulo': 'Total Avaria HUB', 'valor': totais.get('total_avaria_hub') or 0, 'icone': 'fa-warehouse', 'cor': 'danger'},
        ]
    }

    # TEMA 3: On Hold
    temas_kpis['Resultado On Hold'] = {
        'kpis': [
            {'titulo': 'Total Onhold', 'valor': totais.get('total_onhold') or 0, 'icone': 'fa-pause-circle', 'cor': 'warning'},
            {'titulo': 'Onhold Pacotes Devolvidos', 'valor': totais.get('total_onhold_devolvidos') or 0, 'icone': 'fa-reply', 'cor': 'success'},
            {'titulo': 'Onhold Pacotes a Devolver', 'valor': totais.get('total_onhold_devolver') or 0, 'icone': 'fa-arrow-circle-left', 'cor': 'danger'},
            {'titulo': 'Backlog Pacotes Agarrado no HUB', 'valor': totais.get('total_backlog_agarrado') or 0, 'icone': 'fa-lock', 'cor': 'dark'},
            {'titulo': 'Volumosos no HUB', 'valor': totais.get('total_volumosos_hub') or 0, 'icone': 'fa-weight-hanging', 'cor': 'info'},
            {'titulo': 'Total PNR - Perda declarada', 'valor': totais.get('total_pnr') or 0, 'icone': 'fa-exclamation-triangle', 'cor': 'warning'},
        ]
    }
    
    context = {
        'titulo': 'Dashboard de Agregação de Logística',
        'form_filtro': form,
        'temas_kpis': temas_kpis, 
        'data_inicio': data_inicio,
        'data_fim': data_fim,
    }
    return render(request, 'logistica/dashboard.html', context)