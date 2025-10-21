from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import csv
import io
from django.urls import reverse 
from datetime import datetime, timedelta, date
from django.utils import timezone 
from django.db import IntegrityError 
from django.db.models import Count, Q, Sum 
from django.core.paginator import Paginator
from django.template.defaultfilters import slugify
from django.http import HttpResponse 
from django.db.models import F 
from django.db import transaction


from .forms import UploadParcelForm, ParcelFilterForm 
from .models import Parcel

# 🔑 IMPORTAÇÃO NECESSÁRIA: Importa o modelo de outro app
from parcel_lost.models import ParcelLost 


# Mapeamento das colunas do CSV para os campos do modelo
COLUNA_MODELO_MAP = {
    'SPX Tracking Number': 'spx_tracking_number',
    'Scanned Status': 'scanned_status',
    'Expedite Tag': 'expedite_tag',
    'Final Status': 'final_status',
    'Sort Code': 'sort_code',
    'Next Step Action': 'next_step_action',
    'OnHold Times': 'on_hold_times', 
    'Count Type': 'count_type',
    'Expected': 'expected',
    'Operator': 'operator',
    'Aging Time': 'aging_time',
    'Scanned Time': 'scanned_time',
}

# ----------------------------------------------------
# VIEWS DE UPLOAD (CORRIGIDA)
# ----------------------------------------------------
@login_required
def upload_parcel(request):
    """Lógica de upload de arquivos CSV, usando update_or_create com chave composta."""
    if request.method == 'POST':
        form = UploadParcelForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo_csv = form.cleaned_data['arquivo_csv']
            data_referencia = form.cleaned_data['data_referencia']
            
            # --- LEITURA DO ARQUIVO CSV (ROBUSTA) ---
            csv_file = io.TextIOWrapper(arquivo_csv.file, encoding='utf-8-sig', newline='')
            reader = csv.DictReader(csv_file, delimiter=',')
            
            # CORREÇÃO DE CABEÇALHO: Limpa nomes de colunas de espaços em branco.
            if reader.fieldnames:
                cleaned_fieldnames = [name.strip() for name in reader.fieldnames]
                reader.fieldnames = cleaned_fieldnames
            # --- FIM DA LEITURA ---
            
            registros_criados = 0
            registros_atualizados = 0
            registros_ignorados = 0 
            
            for row in reader:
                
                # Obtém o valor limpo para o campo chave
                spx_tracking_number_value = row.get('SPX Tracking Number', '').strip()
                
                # Ignora linhas sem o campo chave
                if not spx_tracking_number_value:
                    registros_ignorados += 1
                    continue
                
                try:
                    row_data = {}
                    for csv_field, model_field in COLUNA_MODELO_MAP.items():
                        
                        # OBTÉM O VALOR, GARANTE STRING E REMOVE ESPAÇOS EXTERNOS
                        value = str(row.get(csv_field, '')).strip() 
                        
                        if model_field == 'scanned_time':
                            # CORREÇÃO DO ERRO DE DATETIME: Limpeza agressiva de aspas vazias
                            if value:
                                cleaned_datetime_str = value.replace('"', '').replace('“', '').replace('”', '').strip()

                                if cleaned_datetime_str:
                                    try:
                                        naive_datetime = datetime.strptime(cleaned_datetime_str, '%Y-%m-%d %H:%M:%S')
                                        row_data[model_field] = timezone.make_aware(naive_datetime)
                                    except ValueError:
                                        row_data[model_field] = None
                                else:
                                    row_data[model_field] = None 
                            else:
                                row_data[model_field] = None 
                        
                        elif model_field == 'on_hold_times':
                            try:
                                row_data[model_field] = int(value) if value else 0
                            except ValueError:
                                row_data[model_field] = 0
                        
                        else:
                            # Atribui os demais campos
                            row_data[model_field] = value
                    
                    # Define os campos de controle antes de chamar update_or_create
                    # O campo 'data_referencia' é crucial para a chave composta.
                    row_data['data_referencia'] = data_referencia
                    row_data['usuario_upload'] = request.user
                    
                    # 🔑 CHAVE COMPOSTA: Usa spx_tracking_number e data_referencia para buscar/atualizar
                    obj, created = Parcel.objects.update_or_create(
                        spx_tracking_number=spx_tracking_number_value, # Chave 1
                        data_referencia=data_referencia,               # Chave 2 (Data do Formulário)
                        
                        # O defaults precisa receber TODOS os campos, exceto os usados acima
                        defaults={
                            k: v for k, v in row_data.items() 
                            if k not in ['spx_tracking_number', 'data_referencia']
                        }
                    )
                    
                    if created:
                        registros_criados += 1
                    else:
                        registros_atualizados += 1
                        
                except IntegrityError as e:
                    # Este erro agora só deve ocorrer se os dados forem inseridos
                    # fora do upload e violarem a nova restrição.
                    messages.error(request, f"Erro de Integridade ao processar {spx_tracking_number_value}: {e}")
                except Exception as e:
                    messages.error(request, f"Erro inesperado ao processar a encomenda {spx_tracking_number_value}: {e}")
            
            messages.success(request, 
                f"Upload concluído! "
                f"Criados: {registros_criados}, "
                f"Atualizados: {registros_atualizados}, "
                f"Linhas ignoradas (sem número de rastreio): {registros_ignorados}."
            )
            return redirect('parcel_sweeper:upload_parcel')
    
    else:
        form = UploadParcelForm()

    context = {
        'form': form,
    }
    return render(request, 'parcel_sweeper/upload_parcel.html', context)

# ----------------------------------------------------
# FUNÇÕES DE SINCRONIZAÇÃO LOST/DAMAGE (NOVO)
# ----------------------------------------------------

def update_parcel_statuses_from_lost():
    """
    Sincroniza o campo 'count_type' da tabela Parcel com o status de perda/avaria 
    (final_status_avaria) da tabela ParcelLost, para os rastreios encontrados 
    em ParcelLost.
    """
    updated_count = 0
    
    # 1. Obtém todos os registros de perda/avaria e mapeia rastreio -> status mais recente
    lost_records = ParcelLost.objects.all().order_by('spx_tracking_number', '-data_registro_sistema')
    
    lost_map = {}
    for record in lost_records:
        # Garante que, para cada rastreio, o último registro (mais recente) seja usado
        if record.spx_tracking_number not in lost_map:
             lost_map[record.spx_tracking_number] = record.final_status_avaria
    
    tracking_numbers_to_update = lost_map.keys()
    
    if not tracking_numbers_to_update:
        return 0

    # 2. Lista dos valores que indicam perda/avaria
    lost_damage_values = [choice[0] for choice in ParcelLost.STATUS_CHOICES]
    
    # 3. Filtra os registros em Parcel que precisam ser atualizados
    parcels_to_update = list(Parcel.objects.filter(
        spx_tracking_number__in=tracking_numbers_to_update,
    ).exclude(
        count_type__in=lost_damage_values # Exclui registros já atualizados
    ))
    
    updates = []
    for parcel in parcels_to_update:
        new_count_type = lost_map.get(parcel.spx_tracking_number)
        
        # A atualização só ocorre se o novo valor for diferente do existente
        if new_count_type and parcel.count_type != new_count_type:
            parcel.count_type = new_count_type
            updates.append(parcel)
    
    if updates:
        # Executa a atualização em lote dos objetos modificados
        Parcel.objects.bulk_update(updates, ['count_type'])
        updated_count = len(updates)
            
    return updated_count


@login_required
def run_status_update(request):
    """View para rodar a sincronização de forma manual/on-demand."""
    
    if request.method == 'POST':
        try:
            # Chama a função de sincronização
            updated_count = update_parcel_statuses_from_lost()
            messages.success(request, f"Sincronização concluída! {updated_count} registros de Parcel Sweeper foram atualizados com o status de Perda/Avaria.")
        except Exception as e:
            messages.error(request, f"Erro ao executar a sincronização: {e}")
            
        # Redireciona de volta para a dashboard (ou de onde foi chamada)
        return redirect('parcel_sweeper:dashboard')
    
    # Se alguém tentar acessar via GET, redireciona também (ou retorna 405)
    return redirect('parcel_sweeper:dashboard')

# ----------------------------------------------------
# VIEWS DE DASHBOARD (COM NOVO KPI)
# ----------------------------------------------------
@login_required
def dashboard_parcel(request):
    
    # 1. Inicializa o formulário
    form = ParcelFilterForm(request.GET)
    
    # 🔑 AJUSTE CRUCIAL 1: Inicializa variáveis com None
    data_inicio_obj = None
    data_fim_obj = None
    final_status_list = []
    sort_code = None


    # Lógica para obter as datas e filtros de forma robusta
    if form.is_valid():
        # Usa os dados limpos (date object ou None se o campo foi esvaziado)
        data_inicio_obj = form.cleaned_data.get('data_inicio')
        data_fim_obj = form.cleaned_data.get('data_fim')
        final_status_list = form.cleaned_data.get('final_status') # LISTA DE STATUS
        sort_code = form.cleaned_data.get('sort_code')
    
    # 🔑 AJUSTE CRUCIAL 2: Se o formulário NÃO FOI submetido (primeiro acesso), 
    #    usa os valores iniciais definidos em forms.py
    if not request.GET:
        data_inicio_obj = form.fields['data_inicio'].initial
        data_fim_obj = form.fields['data_fim'].initial


    # Queryset base
    queryset = Parcel.objects.all()
    
    # 1b. Aplicar filtros de Seleção
    
    # Filtra apenas se as duas datas existirem
    if data_inicio_obj and data_fim_obj: 
        queryset = queryset.filter(
            data_referencia__range=[data_inicio_obj, data_fim_obj]
        )
        
    if final_status_list:
        # Usa __in para filtrar por múltiplos status
        queryset = queryset.filter(final_status__in=final_status_list)
        
    if sort_code:
        queryset = queryset.filter(sort_code__iexact=sort_code)
        
    base_queryset = queryset # Renomeado para clareza no cálculo dos KPIs
        
    # String de filtro para persistência (data e seleções)
    filter_params_list = []
    
    # 🔑 AJUSTE CRUCIAL 3: Checa se o objeto date não é None antes de chamar strftime()
    if data_inicio_obj:
        filter_params_list.append(f"data_inicio={data_inicio_obj.strftime('%Y-%m-%d')}")
    # Não precisa adicionar o parâmetro vazio, pois o Django Form handle o campo vazio 
    # se ele não for adicionado à lista.

    if data_fim_obj:
        filter_params_list.append(f"data_fim={data_fim_obj.strftime('%Y-%m-%d')}")
    
    # Persistindo os filtros de seleção
    if final_status_list:
        # Adicionar cada item da lista como um parâmetro de URL separado
        for status in final_status_list:
            filter_params_list.append(f"final_status={status}")
        
    if sort_code:
        filter_params_list.append(f"sort_code={sort_code}")
        
    filter_params = "&".join(filter_params_list)

    
    # 2. Cálculo dos KPIs
    
    # KPI 1: Total de Registros
    total_registros = base_queryset.count()

    # KPI 2: Total por Final Status (Estático)
    kpis_final_status = base_queryset.values('final_status').annotate(total=Count('final_status')).order_by('-total')

    # NOVO KPI: Total de Perdas e Avarias (Lost/Damage) sincronizadas 🔑
    # Valores de Count Type usados pela função de sincronização (ParcelLost.STATUS_CHOICES)
    lost_damage_kpi_values = [
        'SOC_LOST', 'SOC_DAMAGE', 'HUB_LOST', 'HUB_DAMAGE'
    ]
    lost_parcels_count = base_queryset.filter(
        count_type__in=lost_damage_kpi_values
    ).count()


    # NOVO KPI: Missing no HUB (Count Type = Missing E Final Status = LMHub_Received) -> Amarelo
    kpi_missing_hub = base_queryset.filter(
        Q(count_type__iexact='Missing') & Q(final_status__iexact='LMHub_Received')
    ).count()

    # KPI Modificado: Missing (Não recebidos no HUB) - Count Type = Missing E Final Status != LMHub_Received
    missing_nao_hub_count = base_queryset.filter(
        Q(count_type__iexact='Missing') & ~Q(final_status__iexact='LMHub_Received')
    ).count()
    
    # 🔑 NOVO KPI 1: Backlog diferente de "Process for delivery" (em count_type)
    # CORREÇÃO LÓGICA: Conta registros em BACKLOG onde a ação NÃO é 'Process for delivery'.
    kpi_not_process_for_delivery = base_queryset.filter(
        count_type__iexact='Backlog'
    ).exclude(
        next_step_action__iexact='Process for delivery'
    ).count()

    # 🔑 NOVO KPI 2: Quantidade de registros onde OnHold Times > 0 (KPI GERAL, usa base_queryset)
    kpi_onhold_gt_zero = base_queryset.filter(
        on_hold_times__gt=0
    ).count()

    # Queryset principal para Count Type, EXCLUINDO 'Missing' E Lost/Damage para não duplicar os novos cards 🔑
    # O Count Type deve conter tudo que não é 'Missing' E não é um status de Lost/Damage
    kpis_count_type = base_queryset.exclude(
        Q(count_type__iexact='Missing') | Q(count_type__in=lost_damage_kpi_values)
    ).values('count_type').annotate(total=Count('count_type')).order_by('-total')


    # KPI 4: KPI Específico de Backlog (Lógica de cor condicional)
    backlog_queryset = base_queryset.filter(count_type__iexact='Backlog')
    
    # Backlog Total
    backlog_total = backlog_queryset.count()
    
    # Cor de Fundo VERDE: Backlog: Process for delivery (CORRIGIDO)
    # Lógica: Count Type = 'Backlog' E Next Step Action = 'Process for delivery' E 
    #         (Final Status = 'LMHub_Received' OU Final Status = 'Return_LMHub_Received')
    backlog_green_count = backlog_queryset.filter(
        Q(next_step_action__iexact='Process for delivery'),
        Q(final_status__iexact='LMHub_Received') | Q(final_status__iexact='Return_LMHub_Received')
    ).count()

    # Cor de Fundo VERMELHO: On Hold Times > 3
    backlog_red_count = backlog_queryset.filter(
        on_hold_times__gt=3
    ).count()

    # Soma de On Hold Times (útil para métricas) - Usa a mesma lógica do KPI 'verde'
    backlog_onhold_sum_queryset = backlog_queryset.filter(
        Q(next_step_action__iexact='Process for delivery'),
        Q(final_status__iexact='LMHub_Received') | Q(final_status__iexact='Return_LMHub_Received')
    )
    backlog_onhold_sum = backlog_onhold_sum_queryset.aggregate(total_onhold=Sum('on_hold_times'))['total_onhold'] or 0
    
    # Pacotes Roteirizados mais de uma Vez (On Hold Times > 0)
    backlog_onhold_nonzero_count = base_queryset.filter(on_hold_times__gt=0).count()


    # KPI 5: Total por Expedite Tag
    kpis_expedite_tag = base_queryset.values('expedite_tag').annotate(total=Count('expedite_tag')).order_by('-total')

    context = {
        'form': form,
        'total_registros': total_registros,
        'kpis_final_status': kpis_final_status,
        
        # Lista dos Count Types (sem o Missing e Lost/Damage)
        'kpis_count_type': kpis_count_type,
        
        # Novo KPI: Total de Perdas/Avarias 🔑
        'lost_parcels_count': lost_parcels_count, 

        # Novos KPIs de Missing adicionados
        'kpi_missing_hub': kpi_missing_hub,
        'missing_nao_hub_count': missing_nao_hub_count,
        
        # INCLUSÃO DOS NOVOS KPIS
        'kpi_not_process_for_delivery': kpi_not_process_for_delivery,
        'kpi_onhold_gt_zero': kpi_onhold_gt_zero,
        
        'backlog_total': backlog_total,
        'backlog_onhold_sum': backlog_onhold_sum,
        'backlog_green_count': backlog_green_count, # AGORA CORRETO
        'backlog_red_count': backlog_red_count,
        'backlog_onhold_nonzero_count': backlog_onhold_nonzero_count, # Adicionado
        
        'kpis_expedite_tag': kpis_expedite_tag,
        
        # Parâmetros de filtro para persistência no template
        'filter_params': filter_params,
        
        # 🔑 AJUSTE CRUCIAL 4: Checa se o objeto date existe antes de chamar strftime() para o contexto
        'data_inicio_str': data_inicio_obj.strftime('%Y-%m-%d') if data_inicio_obj else '',
        'data_fim_str': data_fim_obj.strftime('%Y-%m-%d') if data_fim_obj else '',
    }
    return render(request, 'parcel_sweeper/dashboard.html', context)


# ----------------------------------------------------
# NOVO: View para Exportação CSV (Ajustada)
# ----------------------------------------------------
@login_required
def export_parcel_csv(request):
    """View para exportar dados filtrados para CSV."""
    # 1. Recupera parâmetros de filtro (os mesmos de parcel_detail_list/dashboard)
    data_inicio_str = request.GET.get('data_inicio')
    data_fim_str = request.GET.get('data_fim')
    final_status_list = request.GET.getlist('final_status') # 🔑 AJUSTE AQUI: getlist para múltiplos
    sort_code = request.GET.get('sort_code')
    count_type_slug = request.GET.get('count_type_slug') # Parâmetro do KPI de detalhe
    status_detail_slug = request.GET.get('status_detail_slug') # Parâmetro do Final Status de detalhe
    
    queryset = Parcel.objects.all()

    # 2. Aplicar Filtros de Data
    if data_inicio_str and data_fim_str:
        try:
            # Converte a data de início para um objeto date (inclusivo)
            data_inicio_date = datetime.strptime(data_inicio_str, '%Y-%m-%d').date() 
            # Converte a data de fim para um objeto date e adiciona 1 dia para incluir o último dia
            data_fim_date = datetime.strptime(data_fim_str, '%Y-%m-%d').date() 
            
            queryset = queryset.filter(
                data_referencia__range=[data_inicio_date, data_fim_date]
            )
        except ValueError:
            # Ignora o filtro de data se a conversão falhar
            pass
            
    # 3. Aplicar filtro de Final Status (AJUSTE NO FILTRO)
    if final_status_list:
        # Usa __in para filtrar por múltiplos status
        queryset = queryset.filter(final_status__in=final_status_list)
        
    # 4. Aplicar filtro de Sort Code
    if sort_code:
        queryset = queryset.filter(sort_code__iexact=sort_code)

    # 5. Aplicar Filtro de Detalhe por Count Type
    if count_type_slug:
        # A lógica detalhada (que está em views.py) deve ser copiada aqui para garantir que 
        # o queryset de exportação seja o mesmo do detalhe da lista.
        
        # NOVO: Filtro para o KPI Total de Registros (Nenhum filtro adicional)
        if count_type_slug == 'total-registros':
            pass # Já está filtrado por data/sort_code
            
        # NOVO: Filtro para o KPI Backlog Total
        elif count_type_slug == 'backlog-total':
            queryset = queryset.filter(count_type__iexact='Backlog')
            
        # NOVO: Filtro para Backlog (Process for Delivery) - CORRIGIDO
        elif count_type_slug == 'backlog-process-for-delivery' or count_type_slug == 'backlog-green':
            queryset = queryset.filter(
                Q(count_type__iexact='Backlog'),
                Q(next_step_action__iexact='Process for delivery'),
                # Filtro OU (OR) para LMHub_Received e Return_LMHub_Received
                Q(final_status__iexact='LMHub_Received') | Q(final_status__iexact='Return_LMHub_Received')
            )
            
        # NOVO: Filtro para Backlog Agarrado no HUB (Red Count)
        elif count_type_slug == 'backlog-stuck-hub' or count_type_slug == 'backlog-red':
            queryset = queryset.filter(
                count_type__iexact='Backlog',
                on_hold_times__gt=3
            )
        
        # NOVO: Filtro para Pacotes Roteirizados mais de uma Vez
        elif count_type_slug == 'backlog-onhold-times-0':
             queryset = queryset.filter(on_hold_times__gt=0)
            
        # Filtro para o KPI de Perdas/Avarias (Lost/Damage)
        elif count_type_slug == 'lost-damage':
            lost_damage_kpi_values = ['SOC_LOST', 'SOC_DAMAGE', 'HUB_LOST', 'HUB_DAMAGE']
            queryset = queryset.filter(count_type__in=lost_damage_kpi_values)

        # Filtro para Missing no HUB
        elif count_type_slug == 'missing-no-hub':
            queryset = queryset.filter(
                Q(count_type__iexact='Missing') & Q(final_status__iexact='LMHub_Received')
            )

        # Filtro para Missing Não Recebido no HUB
        elif count_type_slug == 'missing-nao-recebidos-no-hub':
            queryset = queryset.filter(
                Q(count_type__iexact='Missing') & ~Q(final_status__iexact='LMHub_Received')
            )

        # Filtro para Backlog (Not Process for Delivery)
        elif count_type_slug == 'backlog-not-process':
            queryset = queryset.filter(
                count_type__iexact='Backlog'
            ).exclude(
                next_step_action__iexact='Process for delivery'
            )

        # Filtro para On Hold Times > 0
        elif count_type_slug == 'onhold-gt-zero':
            queryset = queryset.filter(on_hold_times__gt=0)

        # Filtro para Backlog (Soma OnHold times > 0)
        elif count_type_slug == 'backlog-onhold-sum':
            queryset = queryset.filter(
                Q(count_type__iexact='Backlog'),
                Q(next_step_action__iexact='Process for delivery'),
                Q(final_status__iexact='LMHub_Received') | Q(final_status__iexact='Return_LMHub_Received')
            )
            
        # Filtro padrão para outros Count Types
        else: 
            # Tenta filtrar pelo Count Type exato
            count_type_name = count_type_slug.replace('-', ' ').title().replace(' ', '')
            queryset = queryset.filter(count_type__iexact=count_type_name)
            
    # 6. Aplicar Filtro de Detalhe por Final Status (se houver um slug de final status)
    if status_detail_slug:
        # Final Status
        final_status_name = status_detail_slug.replace('-', ' ').title()
        queryset = queryset.filter(final_status__iexact=final_status_name)
            
    # 7. Prepara o arquivo CSV
    # Cria o objeto HttpResponse do tipo csv
    nome_arquivo = f"parcel_sweeper_export_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'

    writer = csv.writer(response)

    # Cabeçalho: Usa os nomes das colunas originais do CSV
    csv_header = list(COLUNA_MODELO_MAP.keys())
    writer.writerow(csv_header)

    # Cria o inverso do mapeamento para usar os nomes das colunas do CSV
    MODELO_COLUNA_MAP = {v: k for k, v in COLUNA_MODELO_MAP.items()}
    model_fields = list(MODELO_COLUNA_MAP.keys())

    # Escreve os dados
    for parcel in queryset.values_list(*model_fields):
        # Converte datetime para string amigável para o CSV
        row_list = list(parcel)
        
        # Encontra o índice de 'scanned_time'
        try:
            scanned_time_index = model_fields.index('scanned_time')
            scanned_time_value = row_list[scanned_time_index]
            if scanned_time_value and isinstance(scanned_time_value, datetime):
                # Converte o objeto datetime (com fuso horário) para string no formato correto
                row_list[scanned_time_index] = timezone.localtime(scanned_time_value).strftime('%Y-%m-%d %H:%M:%S')
            else:
                row_list[scanned_time_index] = '' # Garante que não apareça 'None'
        except ValueError:
            pass # Campo não encontrado ou não incluído

        writer.writerow(row_list)
        
    return response

@login_required
def parcel_detail_list(request, count_type_slug):
    """ View para listar os detalhes de um Count Type específico (ou KPI). """
    # 1. Recupera parâmetros de filtro (data) e inicia o formulário
    # Inicializa o formulário com todos os parâmetros GET
    form = ParcelFilterForm(request.GET)
    data_inicio_str = request.GET.get('data_inicio')
    data_fim_str = request.GET.get('data_fim')
    sort_code = request.GET.get('sort_code')
    
    # Obtém a lista de status
    final_status_list = []
    if form.is_valid():
        final_status_list = form.cleaned_data.get('final_status')
    else:
        # Fallback para o caso de erro de validação (ex: data inválida)
        final_status_list = request.GET.getlist('final_status')
    
    # Queryset base
    queryset = Parcel.objects.all()
    count_type_name = ''

    # 2. Aplicar filtros de data (Se forem válidos)
    if data_inicio_str and data_fim_str:
        try:
            data_inicio_date = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_fim_date = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
            queryset = queryset.filter(
                data_referencia__range=[data_inicio_date, data_fim_date]
            )
        except ValueError:
            pass
            
    # 3. Aplicar filtro adicional de Sort Code
    if sort_code:
        queryset = queryset.filter(sort_code__iexact=sort_code)

    # Aplicar filtro adicional de Final Status
    if final_status_list:
        # Usa __in para filtrar por múltiplos status
        queryset = queryset.filter(final_status__in=final_status_list)


    # 4. Aplicar Filtro do Slug (Count Type / KPI)

    # Lista de Count Types que representam Lost/Damage (Valores do DB)
    lost_damage_kpi_values = ['SOC_LOST', 'SOC_DAMAGE', 'HUB_LOST', 'HUB_DAMAGE']
    
    # --- FILTROS DE KPIS GERAIS E BACKLOG AJUSTADOS ---
    
    # NOVO: Total de Registros (SLUG: total-registros)
    if count_type_slug == 'total-registros':
        # Não aplica filtro adicional, retorna o queryset base filtrado por data/sort_code
        count_type_name = request.GET.get('name', "Total de Registros")
        
    # Corrigido/Ajustado: Backlog Total (SLUG: backlog-total)
    elif count_type_slug == 'backlog-total': 
        # Filtra por todos os itens classificados como 'Backlog'
        queryset = queryset.filter(count_type__iexact='Backlog')
        count_type_name = request.GET.get('name', "Backlog Total Registrado")
        
    # **CORRIGIDO** Filtro: Backlog - Status Process for delivery (SLUG: backlog-process-for-delivery)
    elif count_type_slug == 'backlog-process-for-delivery':
        # AJUSTADO: Inclui a condição de Final Status para LMHub_Received OU Return_LMHub_Received
        queryset = queryset.filter(
            Q(count_type__iexact='Backlog'),
            Q(next_step_action__iexact='Process for delivery'),
            Q(final_status__iexact='LMHub_Received') | Q(final_status__iexact='Return_LMHub_Received')
        )
        count_type_name = request.GET.get('name', "Backlog - Status Process for delivery")

    # **CORRIGIDO** Filtro: Backlog Agarrado no HUB - Vários dias (SLUG: backlog-stuck-hub)
    elif count_type_slug == 'backlog-stuck-hub':
        queryset = queryset.filter(
            count_type__iexact='Backlog',
            on_hold_times__gt=3
        )
        count_type_name = request.GET.get('name', "Backlog Agarrado no HUB - Vários dias")
        
    # **NOVO/CORRIGIDO** Filtro: Pacotes Roteirizados mais de uma Vez (SLUG: backlog-onhold-times-0)
    elif count_type_slug == 'backlog-onhold-times-0':
        # Lógica: Pacotes com OnHold Times > 0 (Roteirizados mais de uma vez)
        queryset = queryset.filter(on_hold_times__gt=0)
        count_type_name = request.GET.get('name', "Pacotes Roteirizados mais de uma Vez")
        
    # --- LOST/DAMAGE & MISSING (Mantidos no fluxo original) ---

    # Filtro 4.1: Lost & Damage Total (SLUG: lost-damage)
    elif count_type_slug == 'lost-damage': 
        queryset = queryset.filter(count_type__in=lost_damage_kpi_values)
        count_type_name = request.GET.get('name', "Perdas e Avarias (Lost/Damage)")
            
    # Filtro 4.2: Missing no HUB (SLUG: missing-no-hub)
    elif count_type_slug == 'missing-no-hub':
        queryset = queryset.filter(
            Q(count_type__iexact='Missing') & Q(final_status__iexact='LMHub_Received')
        )
        count_type_name = request.GET.get('name', "Missing no HUB")
        
    # Filtro 4.3: Missing Não Recebido no HUB (SLUG: missing-nao-recebidos-no-hub)
    elif count_type_slug == 'missing-nao-recebidos-no-hub':
        queryset = queryset.filter(
            Q(count_type__iexact='Missing') & 
            ~Q(final_status__iexact='LMHub_Received') &
            ~Q(count_type__in=lost_damage_kpi_values) 
        )
        count_type_name = request.GET.get('name', "Missing Não Recebidos no HUB")
            
    
    # --- EXPEDITE TAG ---
    # 🔑 NOVO FILTRO 4.4: Expedite Tag Total (SLUG: expedite-tag-total) 🔑
    elif count_type_slug == 'expedite-tag-total': 
        # Filtra por pacotes que possuem Expedite Tag (não nula e não vazia)
        queryset = queryset.filter(expedite_tag__isnull=False).exclude(expedite_tag__exact='')
        count_type_name = request.GET.get('name', "Expedite Tag Total")

    # Filtro 4.5: Expedite Tag SIM (SLUG: expedite-tag-sim)
    elif count_type_slug == 'expedite-tag-sim':
        queryset = queryset.filter(expedite_tag__iexact='SIM')
        count_type_name = request.GET.get('name', "Expedite Tag (SIM)")

    # Filtro 4.6: Expedite Tag NÃO (SLUG: expedite-tag-nao)
    elif count_type_slug == 'expedite-tag-nao':
        # Exclui os que são 'SIM' (incluindo Nulo, vazio, ou outros valores)
        queryset = queryset.exclude(expedite_tag__iexact='SIM')
        count_type_name = request.GET.get('name', "Expedite Tag (NÃO)")

    # --- BACKLOG (Slugs Antigos Mantidos por compatibilidade, apontam para a mesma lógica) ---
    
    # Filtro 4.8: Backlog (Not Process for Delivery) (SLUG: backlog-not-process)
    elif count_type_slug == 'backlog-not-process':
        queryset = queryset.filter(
            count_type__iexact='Backlog'
        ).exclude(
            next_step_action__iexact='Process for delivery'
        )
        count_type_name = "Backlog (Ação não é 'Process for delivery')"
            
    # Filtro 4.9: On Hold Times > 0 (SLUG: onhold-gt-zero)
    elif count_type_slug == 'onhold-gt-zero':
        # Usa a mesma lógica que "Pacotes Roteirizados mais de uma Vez"
        queryset = queryset.filter(on_hold_times__gt=0)
        count_type_name = "Encomendas com On Hold Times > 0"
        
    # Filtro 4.10: Backlog (Green Count) (SLUG: backlog-green)
    elif count_type_slug == 'backlog-green':
        # Usa a mesma lógica que 'backlog-process-for-delivery' - AGORA CORRETO
        queryset = queryset.filter(
            Q(count_type__iexact='Backlog'),
            Q(next_step_action__iexact='Process for delivery'),
            Q(final_status__iexact='LMHub_Received') | Q(final_status__iexact='Return_LMHub_Received')
        )
        count_type_name = "Backlog (Pronto para entrega)"
        
    # Filtro 4.11: Backlog (Red Count) (SLUG: backlog-red)
    elif count_type_slug == 'backlog-red':
        # Usa a mesma lógica que 'backlog-stuck-hub'
        queryset = queryset.filter(
            count_type__iexact='Backlog',
            on_hold_times__gt=3
        )
        count_type_name = "Backlog (On Hold Times > 3)"
        
    # Filtro 4.12: Backlog (Soma OnHold times > 0) (SLUG: backlog-onhold-sum)
    elif count_type_slug == 'backlog-onhold-sum':
        queryset = queryset.filter(
            Q(count_type__iexact='Backlog'),
            Q(next_step_action__iexact='Process for delivery'),
            Q(final_status__iexact='LMHub_Received') | Q(final_status__iexact='Return_LMHub_Received')
        )
        count_type_name = "Backlog (Itens com On Hold Times para Somatório)"

    # Filtro padrão para outros Count Types (e.g., 'Backlog')
    else:
        # Converte o slug de volta para o nome do Count Type
        db_name = count_type_slug.replace('-', '_').upper()
        # Tenta pegar o nome de exibição da URL
        if not count_type_name:
             count_type_name = request.GET.get('name', count_type_slug.replace('-', ' ').title())
        
        queryset = queryset.filter(count_type__iexact=db_name)
    
    
    # 5. Paginação
    paginator = Paginator(queryset.order_by('-data_referencia'), 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 6. Parâmetros de filtro para persistência na paginação e botão Voltar
    # 🔑 Adiciona o slug obrigatório para o botão Voltar e Paginação
    get_params_copy = request.GET.copy()
    get_params_copy['count_type_slug'] = count_type_slug
    
    filter_params = get_params_copy.urlencode()
    
    # URL de exportação para o botão
    export_url = reverse('parcel_sweeper:export_csv') + '?' + filter_params # Adiciona os filtros
    
    # 🔑 Determina se o filtro de final_status deve ser exibido (aqui sim)
    is_status_detail = False 

    context = {
        'titulo': f'Detalhes: {count_type_name}',
        'page_obj': page_obj,
        'total_registros': queryset.count(),
        'filter_params': filter_params,
        'count_type_name': count_type_name, 
        'export_url': export_url,
        # 🔑 NOVO: Passando o formulário para o template
        'form': form, 
        # Parâmetros para o form action no template
        'detail_url_name': 'parcel_sweeper:detail_list', # Nome da URL atual
        'detail_slug': count_type_slug, # O slug que a URL espera
        'is_status_detail': is_status_detail, # Flag para esconder o filtro desnecessário (Final Status)
    }
    
    return render(request, 'parcel_sweeper/parcel_detail_list.html', context)


@login_required
def parcel_status_detail_list(request, final_status_slug):
    """
    View para listar os detalhes de um Final Status específico.
    """
    from django.urls import reverse
    
    # 1. Recupera parâmetros de filtro (data) e inicia o formulário
    
    # 🔑 NOVO: Inicializa o formulário com todos os parâmetros GET
    form = ParcelFilterForm(request.GET)
    
    data_inicio_str = request.GET.get('data_inicio')
    data_fim_str = request.GET.get('data_fim')
    sort_code = request.GET.get('sort_code')
    
    # Converte o slug para o nome do status
    final_status_name = final_status_slug.replace('-', ' ').title()
    
    # Queryset base filtrado pelo Final Status (Filtro obrigatório)
    queryset = Parcel.objects.filter(final_status__iexact=final_status_name)
    
    # 2. Aplicar filtros de data (Se forem válidos)
    if data_inicio_str and data_fim_str:
        try:
            data_inicio_date = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_fim_date = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
            
            queryset = queryset.filter(
                data_referencia__range=[data_inicio_date, data_fim_date]
            )
        except ValueError:
            # Ignora o filtro de data se a conversão falhar
            pass
            
    # 3. Aplicar filtro adicional de Sort Code
    if sort_code:
        queryset = queryset.filter(sort_code__iexact=sort_code)
        
    
    # 4. Paginação
    paginator = Paginator(queryset.order_by('-data_referencia'), 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 5. Parâmetros de filtro para persistência na paginação e botão Voltar
    # 🔑 Adiciona o slug obrigatório para o botão Voltar e Paginação
    get_params_copy = request.GET.copy()
    get_params_copy['status_detail_slug'] = final_status_slug
    
    filter_params = get_params_copy.urlencode()
    
    # URL de exportação para o botão
    export_url = reverse('parcel_sweeper:export_csv') + '?' + filter_params # Adiciona os filtros
    
    # 🔑 Determina se o filtro de final_status deve ser exibido (aqui não)
    is_status_detail = True

    context = {
        'titulo': f'Detalhes: {final_status_name}',
        'page_obj': page_obj,
        'total_registros': queryset.count(),
        'filter_params': filter_params,
        'count_type_name': final_status_name, # Renomeado para manter compatibilidade com o template
        'export_url': export_url, # Passa a URL de exportação
        # 🔑 NOVO: Passando o formulário para o template
        'form': form, 
        # Parâmetros para o form action no template
        'detail_url_name': 'parcel_sweeper:status_detail_list', # Nome da URL atual
        'detail_slug': final_status_slug, # O slug que a URL espera
        'is_status_detail': is_status_detail, # Flag para esconder o filtro desnecessário (Final Status)
    }
    
    # O template `parcel_detail_list.html` será usado, pois tem a mesma estrutura de tabela
    return render(request, 'parcel_sweeper/parcel_detail_list.html', context)

@login_required
def parcel_status_detail_list(request, final_status_slug):
    """
    View para listar os detalhes de um Final Status específico.
    """
    from django.urls import reverse
    
    # 1. Recupera parâmetros de filtro (data)
    data_inicio_str = request.GET.get('data_inicio')
    data_fim_str = request.GET.get('data_fim')
    sort_code = request.GET.get('sort_code')
    
    # Converte o slug para o nome do status
    final_status_name = final_status_slug.replace('-', ' ').title()
    
    # Queryset base filtrado pelo Final Status
    queryset = Parcel.objects.filter(final_status__iexact=final_status_name)
    
    # 2. Aplicar filtros de data (Se forem válidos)
    if data_inicio_str and data_fim_str:
        try:
            data_inicio_date = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_fim_date = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
            
            queryset = queryset.filter(
                data_referencia__range=[data_inicio_date, data_fim_date]
            )
        except ValueError:
            # Ignora o filtro de data se a conversão falhar
            pass
            
    # 4. Aplicar filtro adicional de Sort Code
    if sort_code:
        queryset = queryset.filter(sort_code__iexact=sort_code)
        
    
    # 5. Paginação
    paginator = Paginator(queryset.order_by('-data_referencia'), 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 6. Parâmetros de filtro para persistência na paginação e botão Voltar
    filter_params = request.GET.urlencode()
    
    # URL de exportação para o botão
    export_url = reverse('parcel_sweeper:export_csv')

    context = {
        'titulo': f'Detalhes: {final_status_name}',
        'page_obj': page_obj,
        'total_registros': queryset.count(),
        'filter_params': filter_params,
        'count_type_name': final_status_name, # Renomeado para manter compatibilidade com o template
        'export_url': export_url, # Passa a URL de exportação
        # Passar os parâmetros de filtro para o template de detalhe para exibição ou uso futuro
        'data_inicio_str': data_inicio_str, 
        'data_fim_str': data_fim_str,
        'sort_code_filtro': sort_code,
        # O slug original é passado para ser usado como parâmetro na exportação
        'status_detail_slug': final_status_slug, # Passa o slug de final status
    }
    
    # O template `parcel_detail_list.html` será usado, pois tem a mesma estrutura de tabela
    return render(request, 'parcel_sweeper/parcel_detail_list.html', context)

@login_required
def menu_actions_sweeper(request):
    """
    Rota principal do app que exibe o menu de ações do Parcel Sweeper.
    """
    return render(request, 'parcel_sweeper/menu_actions_sweeper.html')