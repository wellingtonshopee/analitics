# inventory_analysis/views.py (CÓDIGO COMPLETO FINAL - Com ajuste de KPI Backlog e PERSISTÊNCIA MANUAL)

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse 
from django.db.models import Q # Importado para permitir filtros OR
import csv 
from datetime import date, datetime, timedelta 
from django.db.models import Subquery, OuterRef
from django.contrib import messages # Import para mensagens de feedback
from django.contrib.auth import get_user_model # NOVO: Import para usar request.user

# --- Imports dos Modelos ---
try:
    from collection_pool.models import Pool as CollectionPool
    from parcel_sweeper.models import Parcel as ParcelSweeper
    from rastreio.models import Rastreio
    # CORREÇÃO: Esta linha deve estar DESCOMENTADA para o banco de dados funcionar
    from .models import ManualActionLog 
except ImportError:
    # Classes Mock para evitar erros de importação em ambiente de teste
    class CollectionPool:
        objects = []
    class ParcelSweeper:
        objects = []
    class Rastreio:
        objects = []
    # MOCK para ManualActionLog: Garante que o .objects seja None, permitindo a verificação
    class ManualActionLog:
        objects = None 

# --- Import do Formulário ---
from .forms import DateRangeForm

# --- AÇÕES E STATUS DE CONFRONTO ---
# Novo Status
STATUS_NAO_ADICIONAR = 'NÃO ADICIONAR NA POOL'
STATUS_PARA_ADICIONAR = 'ADICIONAR NA COLLECTION POOL'
STATUS_JA_ADICIONADO = 'JÁ ADICIONADO NA COLLECTION POOL'

# Nova Ação
ACTION_NAO_ADICIONAR = 'IGNORAR'
ACTION_ADICIONAR = 'ADICIONAR'
ACTION_OK = 'OK'
# --- FIM AÇÕES E STATUS ---

# ==============================================================================
# LÓGICA DE DADOS (Helper Functions)
# ==============================================================================

def get_total_collection_pool_count(data_inicio, data_fim):
    """
    KPI: Calcula o total de registros na CollectionPool (collection_pool_pool)
    dentro do período, usando data_envio_arquivo (DateTimeField) e filtros __gte/__lt.
    """
    # Se os modelos são mocks (como está no seu snippet), retorne 0
    if CollectionPool.objects == []:
        return 0
        
    data_inicio_dt = datetime.combine(data_inicio, datetime.min.time())
    # O limite superior agora é o início do dia seguinte (exclusive)
    data_fim_dt_exclusiva = datetime.combine(data_fim + timedelta(days=1), datetime.min.time())
    
    return CollectionPool.objects.filter(
        # Filtro para DateTimeField
        data_envio_arquivo__gte=data_inicio_dt, 
        data_envio_arquivo__lt=data_fim_dt_exclusiva
    ).count()


def get_total_parcel_sweeper_count(data_inicio, data_fim):
    """
    KPI: Calcula o total de registros do Parcel Sweeper (tabela parcel_sweeper_parcel) 
    com filtros específicos: final_status IN ('LMHub_Received', 'Return_LMHub_Received') 
    e count_type = 'Backlog', dentro do período data_referencia.
    """
    # Se os modelos são mocks (como está no seu snippet), retorne 0
    if ParcelSweeper.objects == []:
        return 0
    
    # 1. Filtra pelo intervalo de datas na coluna 'data_referencia'
    qs = ParcelSweeper.objects.filter(
        data_referencia__range=[data_inicio, data_fim]
    )
    
    # 2. Filtra pela coluna 'final_status'
    qs = qs.filter(
        final_status__in=['LMHub_Received', 'Return_LMHub_Received']
    )
    
    # 3. Filtra pela coluna 'count_type'
    qs = qs.filter(
        count_type='Backlog'
    )
    
    # 4. Retorna a contagem final
    return qs.count()

def get_collection_pool_divergence(data_inicio, data_fim):
    """
    Tarefa 1: Confronta ParcelSweeper (Backlog, LMHub_Received) com CollectionPool.
    (AJUSTADO: Adiciona a checagem no ManualActionLog para sobrescrever o status)
    """
    # Define o intervalo completo de datetimes.
    data_inicio_dt = datetime.combine(data_inicio, datetime.min.time())
    # O limite superior agora é o início do dia seguinte (exclusive)
    data_fim_dt_exclusiva = datetime.combine(data_fim + timedelta(days=1), datetime.min.time())
    
    # Filtros de Status Final
    status_filter = (
        Q(final_status__icontains='LMHub_Received') | 
        Q(final_status__icontains='Return_LMHub_Received')
    )
    
    # 1. Busca no ParcelSweeper. 
    # Verifica se a lista de objects não é o mock []
    if ParcelSweeper.objects == []:
        return []
        
    sweeper_parcels_qs = ParcelSweeper.objects.filter(
        status_filter, 
        count_type__iexact='backlog', 
        data_upload_sistema__gte=data_inicio_dt, 
        data_upload_sistema__lt=data_fim_dt_exclusiva
    )
    # Lista de rastreios (strings)
    sweeper_parcels = list(sweeper_parcels_qs.values_list('spx_tracking_number', flat=True))

    # 2. Busca na CollectionPool (para rastreios que estão no sweeper)
    if CollectionPool.objects == []:
        pool_set = set()
    else:
        pool_shipments = CollectionPool.objects.filter(
            shipment_id__in=sweeper_parcels,
            destination_hub='LM Hub_MG_Muriaé',
            status='LMHub_Received',
        ).values_list('shipment_id', flat=True)
        pool_set = set(pool_shipments)

    # NOVO: 3. Busca Ações Manuais
    manual_actions = {}
    if ManualActionLog.objects is not None:
        try:
            # Busca apenas os logs para os pacotes encontrados no Sweeper
            manual_actions_list = list(ManualActionLog.objects.filter(
                parcel_id__in=sweeper_parcels
            ).values('parcel_id', 'action_type'))
            
            # Transforma em um dict para acesso rápido (ex: {'BR123': 'ADD', 'BR456': 'REMOVE'})
            manual_actions = {item['parcel_id']: item['action_type'] for item in manual_actions_list}
        except Exception:
            # Ignora erros se a tabela não existir/não estiver migrada
            pass

    # 4. Confronto e Resultado (Com Sobrescrita)
    results = []
    for tracking_number in sweeper_parcels:
        is_in_pool = tracking_number in pool_set
        manual_action = manual_actions.get(tracking_number)

        # Lógica de Sobrescrita Manual
        if manual_action == 'ADD':
            status_label = STATUS_JA_ADICIONADO
            status_color = "success"
            action_text = ACTION_OK
        elif manual_action == 'REMOVE':
            status_label = STATUS_NAO_ADICIONAR
            status_color = "warning"
            action_text = ACTION_NAO_ADICIONAR
        
        # Lógica Automática (Aplica se não houver ação manual)
        elif is_in_pool:
            status_label = STATUS_JA_ADICIONADO 
            status_color = "success"
            action_text = ACTION_OK 
        else:
            status_label = STATUS_PARA_ADICIONAR 
            status_color = "danger"
            action_text = ACTION_ADICIONAR 

        results.append({
            'rastreio': tracking_number,
            'status_label': status_label,
            'status_color': status_color,
            'action': action_text,
            'location': 'Sweeper',
            'sweeper_status': 'Backlog'
        })

    return results

def get_non_routed_orders(data_inicio, data_fim):
    """
    Tarefa 2: Pedido Recebido Não Roteirizado.
    Busca em Rastreio e verifica se NÃO está em Pool e NÃO está em Sweeper.
    """
    # Define o intervalo completo de datetimes.
    data_inicio_dt = datetime.combine(data_inicio, datetime.min.time())
    # O limite superior agora é o início do dia seguinte (exclusive)
    data_fim_dt_exclusiva = datetime.combine(data_fim + timedelta(days=1), datetime.min.time())

    # Condições de status do Rastreio
    rastreio_statuses = [
        'SOC_LHTransporting', 'SOC_LHTransported', 'LMHub_Received',
        'Return_SOC_LHTransporting', 'Return_SOC_LHTransported', 'Return_LMHub_Received'
    ]

    # 1. Busca em Rastreio (Verifica mock)
    if Rastreio.objects == []:
        return []

    rastreio_parcels = Rastreio.objects.filter(
        status__in=rastreio_statuses,
        destination_hub='LM Hub_MG_Muriaé',
        # USO DO AJUSTE para DateTimeField (data_upload)
        data_upload__gte=data_inicio_dt,
        data_upload__lt=data_fim_dt_exclusiva
    ).values_list('sls_tracking_number', flat=True)

    rastreio_trackings = list(rastreio_parcels)

    # 2. Busca em Pool e Sweeper para identificar roteirizados (Verifica mock)
    # Trackings que ESTÃO na Pool
    if CollectionPool.objects == []:
        pool_trackings = []
    else:
        pool_trackings = CollectionPool.objects.filter(
            shipment_id__in=rastreio_trackings
        ).values_list('shipment_id', flat=True)

    # Trackings que ESTÃO no Sweeper
    if ParcelSweeper.objects == []:
        sweeper_trackings = []
    else:
        sweeper_trackings = ParcelSweeper.objects.filter(
            spx_tracking_number__in=rastreio_trackings
        ).values_list('spx_tracking_number', flat=True)

    # Combina todos os rastreios que já foram roteirizados/processados
    routed_set = set(pool_trackings) | set(sweeper_trackings)

    # 3. Filtrar não roteirizados
    non_routed_trackings = [
        t for t in rastreio_trackings if t not in routed_set
    ]

    # 4. Resultado
    results = []
    for tracking_number in non_routed_trackings:
        results.append({
            'rastreio': tracking_number,
            'status_label': "Não Roteirizado",
            'status_color': "warning",
            'action': "ROTEIRIZAR",
            'location': 'Rastreio',
            'sweeper_status': 'PENDENTE'
        })

    return results


def get_collection_pool_only(data_inicio, data_fim):
    """
    Tarefa 3: Pacotes que estão na CollectionPool, mas NÃO estão no ParcelSweeper.
    """
    # Verifica mock
    if CollectionPool.objects == [] or ParcelSweeper.objects == []:
        return []
        
    data_inicio_dt = datetime.combine(data_inicio, datetime.min.time())
    # O limite superior agora é o início do dia seguinte (exclusive)
    data_fim_dt_exclusiva = datetime.combine(data_fim + timedelta(days=1), datetime.min.time())

    # 1. Todos os tracking numbers do Sweeper no período
    sweeper_trackings_qs = ParcelSweeper.objects.filter(
        data_upload_sistema__gte=data_inicio_dt,
        data_upload_sistema__lt=data_fim_dt_exclusiva
    ).values('spx_tracking_number')

    # 2. Todos os registros da Pool dentro do período, EXCLUINDO os que estão no Sweeper
    collection_pool_only_qs = CollectionPool.objects.filter(
        # Ajuste para DateTimeField (data_envio_arquivo)
        data_envio_arquivo__gte=data_inicio_dt, 
        data_envio_arquivo__lt=data_fim_dt_exclusiva
    ).exclude(
        shipment_id__in=sweeper_trackings_qs
    )

    results = []
    for item in collection_pool_only_qs:
        results.append({
            'rastreio': item.shipment_id,
            'status_label': "Exclusivo Pool (Ausente no Sweeper)",
            'status_color': "info",
            'action': "VERIFICAR",
            'location': 'Collection Pool',
            'sweeper_status': 'AUSENTE',
            'pool_status': item.status # Adicionado para facilitar a verificação
        })
    return results

## ==============================================================================
# VIEWS PRINCIPAIS
# ==============================================================================

@login_required
def analysis_dashboard(request):
    """Renderiza o dashboard principal com filtros e KPIs."""

    # Inicializa o form com request.GET (filtros) ou datas de hoje
    form = DateRangeForm(request.GET or {'data_inicio': date.today(), 'data_fim': date.today()})

    kpis = {}

    if form.is_valid():
        data_inicio = form.cleaned_data.get('data_inicio')
        data_fim = form.cleaned_data.get('data_fim')

        # Executa as consultas APENAS se houver datas válidas
        if data_inicio and data_fim:
            # CHAMADAS DOS KPIS DE CONTAGEM TOTAL
            total_collection_pool = get_total_collection_pool_count(data_inicio, data_fim)
            total_parcel_sweeper = get_total_parcel_sweeper_count(data_inicio, data_fim) 
            
            # Chamadas de relatórios existentes
            report_1_results = get_collection_pool_divergence(data_inicio, data_fim)
            report_2_results = get_non_routed_orders(data_inicio, data_fim)
            report_3_results = get_collection_pool_only(data_inicio, data_fim)

            # Cálculo de KPIs
            # KPI 4: A Adicionar (Status 'danger')
            # AGORA INCLUI AÇÃO MANUAL 'REMOVE' NO CÁLCULO
            to_be_added_to_pool = len([r for r in report_1_results if r['status_color'] == 'danger'])
            
            # NOVO KPI 6: Já Adicionado (Status 'success')
            # AGORA INCLUI AÇÃO MANUAL 'ADD' NO CÁLCULO
            already_in_pool = len([r for r in report_1_results if r['status_color'] == 'success'])
            
            # Outros KPIs
            collection_pool_only_total = len(report_3_results)
            
            # CORREÇÃO APLICADA AQUI: O KPI Total Aptos p/ Roteirização agora exclui os itens 'warning' (Ignorar)
            total_aptos_roteirizacao = len([
                r for r in report_1_results if r['status_color'] != 'warning'
            ])

            kpis = {
                # NOVOS KPIS DE CONTAGEM TOTAL
                'total_collection_pool': total_collection_pool,
                'total_parcel_sweeper': total_parcel_sweeper, # <-- Agora é o Backlog Total
                
                # KPIs de Divergência e Relatórios (existentes)
                'total_divergence_1': len(report_1_results), # Total da Tarefa 1 (Encontrados no Sweeper)
                'to_be_added_to_pool': to_be_added_to_pool, # KPI 4: Total de Registros a Adicionar na Pool
                'already_in_pool': already_in_pool, # KPI 6: Total de Registros Já Adicionados na Pool
                'non_routed_total': len(report_2_results), # KPI: Total da Tarefa 2 (Não Roteirizados)
                'collection_pool_only_total': collection_pool_only_total, # KPI: Exclusivos Pool
                'total_aptos_roteirizacao': total_aptos_roteirizacao, # KPI 5 - CORRIGIDO
                
                # Dados de filtro
                'data_inicio': data_inicio,
                'data_fim': data_fim,
            }

    context = {
        'form': form,
        'kpis': kpis,
        'report_1_id': 1, # ID para Coleção Pool Divergência (TOTAL)
        'report_2_id': 2, # ID para Não Roteirizado
        'report_3_id': 3, # ID para Collection Pool Exclusivo
        'report_4_id': 4, # ID para Adicionar na Collection Pool (Ação Necessária)
        'report_5_id': 5, # ID para Aptos para Roteirização
        'report_6_id': 6, # NOVO ID para Já Adicionado na Pool
    }
    return render(request, 'inventory_analysis/analysis_dashboard.html', context)

@login_required
def action_menu(request):
    """
    Renderiza a página com o menu de ações.
    """
    # DADOS MOCKADOS para o menu
    available_actions = [
        {'name': 'Gerar Relatório de Divergência', 'url': '#'},
        {'name': 'Exportar Dados Brutos', 'url': '#'},
        {'name': 'Análise por HUB', 'url': '#'},
    ]

    context = {'actions': available_actions}
    return render(request, 'inventory_analysis/action_menu.html', context)


@login_required
def detail_list(request, report_id):
    """Renderiza a lista detalhada de itens para um relatório (report_id) específico."""

    # Note: O campo 'acao_sugerida' deve estar presente no seu forms.py para ser lido aqui.
    form = DateRangeForm(request.GET or {'data_inicio': date.today(), 'data_fim': date.today()})
    data = []
    report_title = "Relatório de Detalhes"

    if form.is_valid():
        data_inicio = form.cleaned_data.get('data_inicio')
        data_fim = form.cleaned_data.get('data_fim')
        # NOVO: Obtém o valor do filtro de Ação Sugerida
        # Se 'acao_sugerida' não estiver no forms.py, ele será None
        acao_sugerida_filter = form.cleaned_data.get('acao_sugerida') 

        if data_inicio and data_fim:
            # (Bloco de obtenção de dados por report_id inalterado, exceto pela aplicação final do filtro)
            if report_id == 1:
                data = get_collection_pool_divergence(data_inicio, data_fim)
                report_title = "Divergência: Parcel Sweeper vs Collection Pool (Total)"
            # ... (demais elifs para report_id 2, 3, 4, 5, 6) ...
            elif report_id == 2:
                data = get_non_routed_orders(data_inicio, data_fim)
                report_title = "Pedidos Recebidos Não Roteirizados"
            elif report_id == 3:
                data = get_collection_pool_only(data_inicio, data_fim)
                report_title = "Collection Pool Exclusivo (Ausente no Sweeper)"
            elif report_id == 4:
                raw_data = get_collection_pool_divergence(data_inicio, data_fim)
                data = [r for r in raw_data if r['status_color'] == 'danger']
                report_title = "Adicionar na Collection Pool (Ação Necessária)"
            elif report_id == 5:
                data = get_collection_pool_divergence(data_inicio, data_fim)
                report_title = "Total Aptos para Roteirização (Pool)"
            elif report_id == 6:
                raw_data = get_collection_pool_divergence(data_inicio, data_fim)
                # Filtra pelos que estão como 'success' (adicionado automaticamente ou ADD manual) 
                # e 'warning' (REMOVE manual / IGNORAR)
                data = [r for r in raw_data if r['status_color'] in ['success', 'warning']]
                report_title = "Já Adicionado/Ignorado (Processados Manualmente ou Automaticamente)"
            else:
                return redirect('inventory_analysis:analysis_dashboard')
                
            
            # NOVO: Aplicar o filtro de Ação Sugerida
            if acao_sugerida_filter:
                # Filtra a lista 'data' pelos itens cuja chave 'action' é igual ao valor selecionado no filtro
                data = [r for r in data if r['action'] == acao_sugerida_filter]


    # Passa a string de query atual para o template (para o botão Exportar CSV)
    query_string = request.GET.urlencode()

    context = {
        'report_title': report_title,
        'parcel_details': data,
        'report_id': report_id,
        'form': form,
        'query_string': query_string,
    }
    return render(request, 'inventory_analysis/detail_list.html', context)


@login_required
def export_detail_list_csv(request, report_id):
    """Exporta a lista de detalhes filtrada para um arquivo CSV."""

    form = DateRangeForm(request.GET)
    # A lógica de filtro do CSV também deve ler 'acao_sugerida' se estiver no form
    acao_sugerida_filter = request.GET.get('acao_sugerida') # Leitura direta para evitar revalidação do form

    if not form.is_valid():
        return redirect('inventory_analysis:analysis_dashboard')

    data_inicio = form.cleaned_data.get('data_inicio')
    data_fim = form.cleaned_data.get('data_fim')

    if not data_inicio or not data_fim:
        return redirect('inventory_analysis:analysis_dashboard')

    # Determina qual relatório gerar
    if report_id == 1:
        data = get_collection_pool_divergence(data_inicio, data_fim)
        report_name = "Divergencia_Pool_Total"
    elif report_id == 2:
        data = get_non_routed_orders(data_inicio, data_fim)
        report_name = "Nao_Roteirizado"
    elif report_id == 3:
        data = get_collection_pool_only(data_inicio, data_fim)
        report_name = "CollectionPool_Exclusivo"
    # Report ID 4 - Filtra subconjunto do Report 1 (Adicionar)
    elif report_id == 4:
        raw_data = get_collection_pool_divergence(data_inicio, data_fim)
        data = [r for r in raw_data if r['status_color'] == 'danger']
        report_name = "Adicionar_na_Pool_Acao"
    # Report ID 5
    elif report_id == 5:
        data = get_collection_pool_divergence(data_inicio, data_fim)
        report_name = "Aptos_para_Roteirizacao_Pool"
    # NOVO: Report ID 6
    elif report_id == 6:
        raw_data = get_collection_pool_divergence(data_inicio, data_fim)
        data = [r for r in raw_data if r['status_color'] in ['success', 'warning']]
        report_name = "Ja_Adicionado_ou_Ignorado"
    else:
        return HttpResponse("Relatório Inválido", status=400)

    # NOVO: Aplicar o filtro de Ação Sugerida ao CSV
    if acao_sugerida_filter:
        data = [r for r in data if r['action'] == acao_sugerida_filter]
        report_name += f"_{acao_sugerida_filter.replace(' ', '_')}"


    # Cria a resposta HTTP com tipo CSV
    response = HttpResponse(content_type='text/csv')
    filename = f'{report_name}_{data_inicio.strftime("%Y%m%d")}_a_{data_fim.strftime("%Y%m%d")}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response, delimiter=';') # Usando ';' como separador para compatibilidade com Excel

    # Escreve o cabeçalho
    header = ['N_RASTREIO', 'LOCAL_ORIGEM', 'STATUS_SWEEPER', 'ACAO_SUGERIDA', 'STATUS_CONFRONTO']
    writer.writerow(header)

    # Escreve as linhas de dados
    for item in data:
        writer.writerow([
            item['rastreio'],
            item.get('location', ''),
            item.get('sweeper_status', ''),
            item.get('action', ''),
            item.get('status_label', '')
        ])

    return response


# ==============================================================================
# VIEWS PARA AÇÕES RÁPIDAS (AGORA COM PERSISTÊNCIA CORRIGIDA)
# ==============================================================================

@login_required
def mark_as_added(request, parcel_id):
    """
    Marca um item para ser considerado "JÁ ADICIONADO" (Sobrescrevendo a lógica).
    """
    if ManualActionLog.objects is not None:
        try:
            ManualActionLog.objects.update_or_create(
                parcel_id=parcel_id,
                defaults={
                    'action_type': 'ADD',
                    # Garante que o usuário logado é usado, ou None se não autenticado
                    'user': request.user if hasattr(request, 'user') and request.user.is_authenticated else None
                }
            )
            messages.success(request, f'Rastreio **{parcel_id}** marcado manualmente para **{STATUS_JA_ADICIONADO}**.')
        except Exception as e:
            messages.error(request, f'Erro ao salvar a ação para {parcel_id}: {e}')
    else:
        messages.success(request, f'Rastreio {parcel_id} marcado como "{STATUS_JA_ADICIONADO}" com sucesso. (Lógica de persistência desativada/erro na importação do modelo.)')
        
    return redirect(request.META.get('HTTP_REFERER', 'inventory_analysis:analysis_dashboard'))


@login_required
def remove_from_pool(request, parcel_id):
    """
    Marca um item para ser considerado "NÃO ADICIONAR" (Sobrescrevendo a lógica) ou EXCLUI a ação manual.
    """
    if ManualActionLog.objects is not None:
        if request.GET.get('action') == 'delete':
            # Se for uma ação de exclusão (limpar o Log)
            try:
                # O comando delete é executado aqui, e agora deve funcionar com a importação correta
                deleted_count, _ = ManualActionLog.objects.filter(parcel_id=parcel_id).delete()
                if deleted_count > 0:
                    messages.info(request, f'Registro de ação manual para **{parcel_id}** foi **EXCLUÍDO** com sucesso. O status voltará ao cálculo automático.')
                else:
                    messages.error(request, f'Erro: Ação manual para **{parcel_id}** não encontrada para exclusão.')
            except Exception as e:
                messages.error(request, f'Erro ao excluir a ação manual para {parcel_id}: {e}')
        else:
            # Se for a ação "NÃO ADICIONAR" / "IGNORAR"
            try:
                ManualActionLog.objects.update_or_create(
                    parcel_id=parcel_id,
                    defaults={
                        'action_type': 'REMOVE',
                        'user': request.user if hasattr(request, 'user') and request.user.is_authenticated else None
                    }
                )
                messages.warning(request, f'Rastreio **{parcel_id}** marcado manualmente para **{STATUS_NAO_ADICIONAR}** (Ignorar).')
            except Exception as e:
                messages.error(request, f'Erro ao salvar a ação para {parcel_id}: {e}')
    else:
        messages.warning(request, f'Rastreio {parcel_id} marcado como "{STATUS_NAO_ADICIONAR}" com sucesso. (Lógica de persistência desativada/erro na importação do modelo.)')

    return redirect(request.META.get('HTTP_REFERER', 'inventory_analysis:analysis_dashboard'))