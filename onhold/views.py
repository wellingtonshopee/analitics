import csv
from django.http import HttpResponse 
import io
import requests
from datetime import datetime, date, timedelta 
# Mantido TruncDate no import, embora não seja mais usado em dashboard_onhold para evitar erro do SQLite
from django.db.models.functions import TruncDate 
from .models import OnHold, HUB, OnholdInicial
import json 

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q, Avg, Func, Value 
from django.core.paginator import Paginator 


# --- Funções Auxiliares ---

def parse_float(value_str):
    """Converte string para float. Retorna None se a string for vazia."""
    if value_str:
        try:
            # Substitui vírgula por ponto para garantir o formato de float americano
            return float(value_str.replace(',', '.')) 
        except ValueError:
            return None
    return None

def parse_onhold_time(time_str):
    """Converte string de data/hora para objeto date (YYYY-MM-DD)."""
    if not time_str:
        return None
    
    # Tenta o formato comum do CSV: DD-MM-YYYY HH:MM
    try:
        # 1. Cria o objeto datetime (com data e hora)
        dt_obj = datetime.strptime(time_str, '%d-%m-%Y %H:%M')
        
        # 2. RETORNA APENAS A DATA (dt_obj.date())
        return dt_obj.date()
        
    except ValueError:
        return None
    
# --- Funções de Upload (Corrigidas para UNIQUE constraint failed) ---

@transaction.atomic 
def processar_upload_onhold(request):
    if request.method == 'POST':
        # 1. VALIDAÇÃO E CONVERSÃO DA DATA
        data_referencia_str = request.POST.get('data_referencia')
        if not data_referencia_str:
            messages.error(request, "A Data de Referência é obrigatória para a sobrescrita.")
            return redirect('upload_onhold')
            
        try:
            # data_referencia é a data selecionada no formulário (objeto date)
            data_referencia = datetime.strptime(data_referencia_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Formato de data inválido. Use AAAA-MM-DD.")
            return redirect('upload_onhold')

        if 'csv_file' not in request.FILES:
            messages.error(request, "Nenhum arquivo CSV enviado.")
            return redirect('upload_onhold')

        csv_file = request.FILES['csv_file']
        
        # 2. OBTENÇÃO DOS OBJETOS DE CHAVE ESTRANGEIRA
        try:
            usuario_do_upload = request.user 
            hub_do_upload = HUB.objects.first() # AJUSTE ISTO para refletir seu modelo
        except Exception as e:
            messages.error(request, f"Erro ao obter informações do usuário/HUB: {e}")
            return redirect('upload_onhold')


        # ----------------------------------------------------
        # --- LÓGICA DE SOBRESCRITA (A CHAVE É data_envio) ---
        # ----------------------------------------------------
        
        # PASSO 1: Limpeza de dados antigos com data de envio nula ou vazia (Ação de emergência)
        OnHold.objects.filter(Q(data_envio__isnull=True) | Q(data_envio__exact='')).delete()
        
        # PASSO 2: FILTRO E EXCLUSÃO (Usa a data selecionada para filtrar o campo data_envio)
        registros_para_excluir = OnHold.objects.filter(data_envio=data_referencia)
        total_excluidos = registros_para_excluir.count()
        registros_para_excluir.delete() # EXCLUSÃO EFETIVA
        
        # ----------------------------------------------------
        
        # Leitura e processamento do arquivo
        try:
            file_data = csv_file.read().decode('utf-8')
            csv_data = csv.reader(io.StringIO(file_data))
            header = next(csv_data) # Pula o cabeçalho
            
            novos_registros = []
            
            # 3. CRIAÇÃO DOS NOVOS REGISTROS
            for i, row in enumerate(csv_data):
                # O CSV deve ter pelo menos 36 colunas para 'payment_method'
                if len(row) < 36:
                    messages.warning(request, f"Linha {i+2} ignorada: A linha tem menos colunas do que o esperado (36).")
                    continue
                    
                # Conversão de valores
                try:
                    onhold_time_parsed = parse_onhold_time(row[16]) # Data OnHold (do CSV)
                    
                    # Ignora linhas sem data de OnHold válida (melhoria de consistência)
                    if not onhold_time_parsed:
                         messages.warning(request, f"Linha {i+2} ignorada: Data OnHold (coluna 16) inválida ou vazia.")
                         continue
                            
                    peso = parse_float(row[23])
                    comprimento = parse_float(row[25])
                    largura = parse_float(row[26])
                    altura = parse_float(row[27])
                except Exception as e:
                    messages.warning(request, f"Linha {i+2} ignorada devido a erro de conversão de dados: {e}")
                    continue

                # Mapeamento e criação do registro
                data = {
                    # Chaves Estrangeiras
                    'hub_upload': hub_do_upload, 
                    'usuario_upload': usuario_do_upload,
                    
                    # ✅ CAMPO DATA_ENVIO: Recebe a data de referência para fins de controle/sobrescrita
                    'data_envio': data_referencia, 
                    
                    # onhold_time: Usa a data PARSEADA da coluna 16 do CSV
                    'onhold_time': onhold_time_parsed, 
                    
                    # Campos do CSV
                    'order_id': row[0],
                    'sls_tracking_number': row[1],
                    'shopee_order_sn': row[3], 
                    'driver_name': row[11],
                    'sort_code_name': row[4],
                    'buyer_name': row[5],
                    'buyer_phone': row[6],
                    'postal_code': row[9],
                    'onhold_reason': row[17],
                    'status': row[19],
                    'manifest_number': row[21],
                    'payment_method': row[35],
                    
                    # Campos numéricos
                    'parcel_weight': peso, 
                    'length': comprimento, 
                    'width': largura, 
                    'height': altura,
                }
                
                novos_registros.append(OnHold(**data))

            # Criação em massa para performance
            # ✅ CORREÇÃO: Adicionado ignore_conflicts=True para lidar com a chave única
            OnHold.objects.bulk_create(novos_registros, ignore_conflicts=True)

            messages.success(request, f"Sucesso! {total_excluidos} registros antigos da data {data_referencia.strftime('%d/%m/%Y')} foram excluídos e {len(novos_registros)} novos registros foram carregados (duplicatas ignoradas).")
            
        except Exception as e:
            messages.error(request, f"Erro fatal ao processar o arquivo: {e}")
            
        return redirect('pagina_de_visualizacao')

    return render(request, 'seu_template_de_upload.html')
    

# onhold/views.py

@login_required
@transaction.atomic # Garante que ou todas as linhas são salvas, ou nenhuma
def upload_csv_onhold(request):
    if request.method == 'POST':
        # 0. CAPTURA E VALIDAÇÃO DA DATA DE REFERÊNCIA
        data_referencia_str = request.POST.get('data_referencia')
        if not data_referencia_str:
            messages.error(request, "A Data de Referência é obrigatória para a importação.")
            return redirect('upload_onhold')

        try:
            data_referencia = datetime.strptime(data_referencia_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Formato de Data de Referência inválido.")
            return redirect('upload_onhold')
        
        # 1. Validação de Arquivo (sem alterações)
        if 'csv_file' not in request.FILES:
            messages.error(request, 'Nenhum arquivo foi selecionado.')
            return redirect('upload_onhold')

        csv_file = request.FILES['csv_file']
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'O arquivo deve ser do tipo CSV.')
            return redirect('upload_onhold')

        # 2. Configuração e Leitura (sem alterações)
        dataset = csv_file.read().decode('utf-8')
        io_string = io.StringIO(dataset)
        
        try:
            next(io_string) 
        except StopIteration:
            messages.error(request, 'O arquivo CSV está vazio ou não possui cabeçalho.')
            return redirect('upload_onhold')
            
        reader = csv.reader(io_string, delimiter=',')
        
        # Dados do usuário para vinculação
        hub_do_usuario = request.user.hub if request.user.hub else None
        usuario_obj = request.user 
        
        registros_a_criar = []
        linhas_processadas = 0
        
        # NOVOS CONTADORES PARA AUDITORIA DETALHADA
        linhas_vazias_ignoradas = 0
        linhas_rejeitadas_colunas = 0
        linhas_onhold_time_nulas = 0 

        # 3. Processamento Linha por Linha
        try:
            # Captura o total antes para auditoria de duplicação (Duplicação é o Motivo 1)
            total_registros_antes = OnHold.objects.count()

            for i, row in enumerate(reader):
                linhas_processadas += 1
                
                # Pula linhas vazias (Motivo 4 - Permanece, pois não há o que salvar)
                if not row or not row[0]:
                    linhas_vazias_ignoradas += 1
                    continue
                
                # O CSV deve ter pelo menos 36 colunas (Motivo 3 - Permanece para evitar IndexError)
                if len(row) < 36:
                    # Manter o 'continue' para evitar crash na linha seguinte.
                    # A solução é corrigir o CSV original, mas o sistema conta a rejeição.
                    messages.warning(request, f"Linha {i+2} ignorada: A linha tem menos colunas do que o esperado (36).")
                    linhas_rejeitadas_colunas += 1
                    continue 
                
                # --- CAMPOS AUDITÁVEIS ---
                onhold_time_parsed = parse_onhold_time(row[16]) 
                
                # ALTERAÇÃO CHAVE: Não ignora mais a linha, apenas conta a ocorrência
                # O registro será criado com onhold_time=None (espera-se que o model permita nulo)
                if not onhold_time_parsed:
                    linhas_onhold_time_nulas += 1
                    
                # --- CAMPOS NUMÉRICOS (Conversão para Float) ---
                parcel_weight_parsed = parse_float(row[23])
                length_parsed = parse_float(row[25])
                width_parsed = parse_float(row[26])
                height_parsed = parse_float(row[27])
                
                # Adiciona à lista
                registros_a_criar.append(OnHold(
                    hub_upload=hub_do_usuario,
                    usuario_upload=usuario_obj,
                    data_envio=data_referencia, 
                    # Mapeamento dos índices (sem alterações)
                    order_id=row[0],
                    sls_tracking_number=row[1],
                    shopee_order_sn=row[3],
                    sort_code_name=row[4],
                    buyer_name=row[5],
                    buyer_phone=row[6],
                    postal_code=row[9],
                    driver_name=row[11],
                    onhold_time=onhold_time_parsed, # Pode ser None
                    onhold_reason=row[17],
                    status=row[19],
                    manifest_number=row[21],
                    payment_method=row[35],
                    parcel_weight=parcel_weight_parsed, 
                    length=length_parsed,
                    width=width_parsed,
                    height=height_parsed,
                ))

            # Criação em massa com ignore_conflicts=True
            total_tentativas_insercao = len(registros_a_criar)
            OnHold.objects.bulk_create(registros_a_criar, ignore_conflicts=True)
            
            # Contar depois
            total_registros_depois = OnHold.objects.count()
            
            # O número de registros NOVOS criados
            registros_criados_novos = total_registros_depois - total_registros_antes
            
            # O número de conflitos ignorados
            conflitos_ignorados = total_tentativas_insercao - registros_criados_novos

            # 4. Mensagens de Feedback
            if total_tentativas_insercao > 0:
                messages.success(request, f'Sucesso! **{registros_criados_novos}** registros ONHold NOVOS foram salvos no total.')
                
                # Informar sobre perdas
                if conflitos_ignorados > 0:
                     # ESTE É O MOTIVO MAIS PROVÁVEL DOS 63 REGISTROS FALTANTES
                     messages.info(request, f'**{conflitos_ignorados}** registros foram ignorados por serem duplicatas (Conflito de Chave Única).')
                
                total_rejeitados = linhas_vazias_ignoradas + linhas_rejeitadas_colunas
                if total_rejeitados > 0:
                     messages.warning(request, f'**{total_rejeitados}** linhas foram rejeitadas na leitura e não entraram na lista de importação.')
                
                # Informar sobre registros com campo OnHold Time nulo
                if linhas_onhold_time_nulas > 0:
                     messages.warning(request, f'**{linhas_onhold_time_nulas}** registros foram salvos, mas a data de Retenção (`onhold_time`) estava nula/inválida no CSV.')

            else:
                messages.warning(request, 'O arquivo foi processado, mas nenhuma linha válida foi encontrada para importação.')

        except IndexError as e:
            messages.error(request, f'Erro de formato na linha {linhas_processadas+1}. O arquivo CSV parece ter menos colunas do que o esperado. A importação foi cancelada.')
            return redirect('upload_onhold')
            
        except Exception as e:
            messages.error(request, f'Erro grave durante o processamento do arquivo: {e}. A importação foi cancelada.')
            return redirect('upload_onhold')

        # Redireciona para evitar reenvio do formulário
        return redirect('dashboard') 

    return render(request, 'onhold/upload_onhold.html', {'titulo': 'Upload de Dados ONHold'})

# --- Funções de Consulta e Dashboard ---

@login_required
def consulta_onhold(request):
    # Começa com todos os registros
    registros = OnHold.objects.all().select_related('hub_upload').order_by('-data_envio')
    
    # Obtém todos os HUBs para o filtro
    hubs = HUB.objects.all().order_by('nome')
    
    # --- Lógica de Filtro ---
    filtros_aplicados = False
    
    # Filtro por SLS Tracking Number ou Order ID
    busca_tracking = request.GET.get('tracking')
    if busca_tracking:
        registros = registros.filter(
            sls_tracking_number__icontains=busca_tracking
        ) | registros.filter(
            order_id__icontains=busca_tracking
        )
        filtros_aplicados = True

    # Filtro por Motivo de OnHold
    motivo = request.GET.get('motivo')
    if motivo:
        registros = registros.filter(onhold_reason=motivo)
        filtros_aplicados = True
        
    # Filtro por HUB
    hub_id = request.GET.get('hub')
    if hub_id and hub_id != 'all':
        registros = registros.filter(hub_upload_id=hub_id)
        filtros_aplicados = True

    # Filtro por Data OnHold (Inicial e Final)
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    if data_inicio:
        registros = registros.filter(data_envio__gte=data_inicio) # Maior ou igual (>=)
        filtros_aplicados = True
    if data_fim:
        registros = registros.filter(data_envio__lte=data_fim) # Menor ou igual (<=)
        filtros_aplicados = True
        
    # --- Paginação ---
    paginator = Paginator(registros, 25) # 25 registros por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Obtém motivos únicos (para o filtro dinâmico)
    motivos_unicos = OnHold.objects.values_list('onhold_reason', flat=True).distinct().exclude(onhold_reason__isnull=True).exclude(onhold_reason__exact='').order_by('onhold_reason')

    context = {
        'page_obj': page_obj,
        'hubs': hubs,
        'motivos_unicos': motivos_unicos,
        'filtros_aplicados': filtros_aplicados,
        
        # Mantém os valores de filtro no template
        'tracking_value': busca_tracking or '',
        'motivo_selecionado': motivo or '',
        'hub_selecionado': hub_id or '',
        'data_inicio_value': data_inicio or '',
        'data_fim_value': data_fim or '',
    }

    return render(request, 'onhold/consulta_onhold.html', context)

@login_required
def dashboard_onhold(request):
    from datetime import datetime, date, timedelta
    from django.db.models import Count, Q, Avg
    from .models import OnHold # Certifique-se de que está importado
    
    # --- 1. Lógica de Filtro de Data (De/Até) ---
    data_fim_str = request.GET.get('data_fim')
    data_inicio_str = request.GET.get('data_inicio')
    
    # Define a data final (default: hoje)
    try:
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date() if data_fim_str else date.today()
    except ValueError:
        data_fim = date.today()

    # Define a data inicial (default: 7 dias antes da data final)
    try:
        data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date() if data_inicio_str else data_fim - timedelta(days=7)
    except ValueError:
        data_inicio = data_fim - timedelta(days=7)

    # Garante que a data de início não é maior que a data final
    if data_inicio > data_fim:
        data_inicio = data_fim


    # --- 2. Consulta de Dados Filtrada (USANDO data_envio) ---
    registros_filtrados = OnHold.objects.filter(
        data_envio__range=[data_inicio, data_fim]
    )

    # 3. Agregações para os Cards 
    total_onhold_periodo = registros_filtrados.count()
    
    # Se não houver registros, inicializa as variáveis dos gráficos como vazias e sai
    if total_onhold_periodo == 0:
        context = {
            'data_inicio_value': data_inicio.strftime('%Y-%m-%d'),
            'data_fim_value': data_fim.strftime('%Y-%m-%d'),
            'total_onhold_periodo': 0,
            'rastreios_unicos': 0, 'total_a_devolver': 0, 'total_devolvidos': 0,
            'motivos_contagem': [], 'hubs_contagem': [], 'media_peso': 0.0,
            'total_ausente': 0, 
            'registros_por_motorista': [],
            'grafico_linha_datas': [], 
            'grafico_linha_totais': [], 'grafico_pizza_labels': [], 
            'grafico_pizza_valores': [],
            # Adiciona os novos KPIs
            'total_volumosos': 0,
            'total_perdidos': 0, # NOVO
            'total_wrongly_assigned': 0, # NOVO
        }
        return render(request, 'onhold/dashboard_onhold.html', context)
    

    # --- 4. Continua com as agregações se houver dados ---
    
    # CÁLCULO DOS KPIS
    # ----------------------------------------------------
    
    # 💥 KPI 1: VOLUMOSOS (Já existente)
    total_volumosos = registros_filtrados.filter(
        onhold_reason='Insufficient Vehicle Capacity',
        status='LMHub_Received'
    ).count()

    # 💥 KPI 2: PERDIDOS (NOVO)
    total_perdidos = registros_filtrados.filter(
        onhold_reason='Parcel lost',
        status='OnHold' # No status OnHold
    ).count()
    
    # 💥 KPI 3: ATRIBUIÇÃO ERRADA (NOVO)
    total_wrongly_assigned = registros_filtrados.filter(
        onhold_reason='Wrongly assigned',
        status='OnHold' # No status OnHold
    ).count()
    
    # ----------------------------------------------------
    
    # 4.1. Totais e Rastreios Únicos no Período (restante do código...)
    rastreios_unicos = registros_filtrados.values('sls_tracking_number').distinct().count()

    # 4.2. Pacotes a Devolver
    total_a_devolver = registros_filtrados.filter(status='OnHold').count()
    
    # 4.3. Pacotes Devolvidos
    total_devolvidos = registros_filtrados.filter(status='LMHub_Received').count()
    
    # 4.4. Contagem de Motivos (AGORA TODOS)
    motivos_contagem = registros_filtrados.values('onhold_reason').annotate(
        total=Count('onhold_reason')
    ).order_by('-total')
    
    # 4.5. Contagem de HUBs
    hubs_contagem = registros_filtrados.values('hub_upload__nome').annotate(
        total=Count('hub_upload__nome')
    ).order_by('-total')

    # 4.6. Média de Peso
    metricas_dimensoes = registros_filtrados.aggregate(
        media_peso=Avg('parcel_weight'),
        media_comprimento=Avg('length'),
    )
    
    # 4.7. Contagem de Motivos Chave (Ausente/Recusa)
    total_ausente = registros_filtrados.filter(
        Q(onhold_reason__icontains='recipient unavailable') | 
        Q(onhold_reason__icontains='destinatário ausente') | 
        Q(onhold_reason__icontains='recusa de recebimento') | 
        Q(onhold_reason__icontains='refused to accept')
    ).count()

    # 4.8. Contagem de Registros OnHold por Motorista
    registros_por_motorista = registros_filtrados.filter(
        status__iexact='OnHold' 
    ).values('driver_name').annotate(
        total=Count('driver_name')
    ).order_by('-total')


    # --- 5. Agregações para Gráficos (USANDO data_envio) ---

    # 5.1. GRÁFICO DE LINHA (Total de Registros por Dia)
    MIN_DATE_FILTER = date(2000, 1, 1) 
    
    dados_linha_queryset = registros_filtrados.filter(
        data_envio__isnull=False,
        data_envio__gte=MIN_DATE_FILTER
    ).values('data_envio').annotate(
        total=Count('id')
    ).order_by('data_envio')

    grafico_linha_datas = [item['data_envio'].strftime('%d/%m') for item in dados_linha_queryset]
    grafico_linha_totais = [item['total'] for item in dados_linha_queryset]


    # 5.2. GRÁFICO DE PIZZA (Distribuição de Status)
    contagem_status = registros_filtrados.aggregate(
        total_onhold=Count('id', filter=Q(status='OnHold')),
        total_devolvido=Count('id', filter=Q(status='LMHub_Received')),
        total_outros=Count('id', filter=~Q(status='OnHold') & ~Q(status='LMHub_Received'))
    )

    grafico_pizza_labels = ['A Devolver (OnHold)', 'Devolvidos (LMHub_Received)', 'Outros Status']
    grafico_pizza_valores = [
        contagem_status['total_onhold'],
        contagem_status['total_devolvido'],
        contagem_status['total_outros'],
    ]

    
    # --- 6. Contexto Final ---
    context = {
        # Dados para Filtros e Visualização
        'data_inicio_value': data_inicio.strftime('%Y-%m-%d'),
        'data_fim_value': data_fim.strftime('%Y-%m-%d'),
        
        # Dados para Cards
        'total_onhold_periodo': total_onhold_periodo,
        'rastreios_unicos': rastreios_unicos,
        'total_a_devolver': total_a_devolver,
        'total_devolvidos': total_devolvidos,
        'motivos_contagem': motivos_contagem,
        'hubs_contagem': hubs_contagem,
        'media_peso': round(metricas_dimensoes['media_peso'] or 0.0, 2), 
        'total_ausente': total_ausente,
        
        # ✅ KPIs Adicionados
        'total_volumosos': total_volumosos, 
        'total_perdidos': total_perdidos, # NOVO KPI
        'total_wrongly_assigned': total_wrongly_assigned, # NOVO KPI

        # Dados para a lista de motoristas
        'registros_por_motorista': registros_por_motorista,

        # DADOS PARA GRÁFICOS
        'grafico_linha_datas': grafico_linha_datas,
        'grafico_linha_totais': grafico_linha_totais,
        'grafico_pizza_labels': grafico_pizza_labels,
        'grafico_pizza_valores': grafico_pizza_valores,
    }

    return render(request, 'onhold/dashboard_onhold.html', context)

@login_required
def consulta_onhold_por_motorista(request):
    
    # 1. Filtra apenas os pacotes com status 'OnHold' e que possuem Driver Name
    pacotes_onhold = OnHold.objects.filter(
        status='OnHold'
    ).exclude(
        # Exclui pacotes onde o Driver Name é vazio ou nulo (ajustado para campo charfield)
        Q(driver_name__exact='') | Q(driver_name__isnull=True)
    )
    
    # 2. Agrega os pacotes pelo Driver Name e conta
    contagem_por_motorista = pacotes_onhold.values('driver_name').annotate(
        total_onhold=Count('driver_name') 
    ).order_by('-total_onhold')

    # 3. Calcula o total geral de pacotes 'OnHold' com motorista
    total_onhold_com_motorista = pacotes_onhold.count() 

    context = {
        'titulo': f'Pacotes OnHold por Motorista ({total_onhold_com_motorista} no Total)',
        'contagem_motoristas': contagem_por_motorista,
        'total_geral_onhold': total_onhold_com_motorista, 
    }
    
    return render(request, 'onhold/detalhe_motorista.html', context)


@login_required
def consulta_por_motivo(request, motivo):
    from datetime import datetime
    from django.core.paginator import Paginator 
    from django.db.models import Func # Garante que Func está importado para o TRIM

    # --- 1. Recuperação e validação das datas (De/Até) ---
    data_inicio_str = request.GET.get('data_inicio')
    data_fim_str = request.GET.get('data_fim')
    
    data_inicio = None
    data_fim = None
    data_inicio_formatada = ""
    data_fim_formatada = ""
    
    try:
        if data_inicio_str:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_inicio_formatada = data_inicio.strftime('%d/%m/%Y')
        if data_fim_str:
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
            data_fim_formatada = data_fim.strftime('%d/%m/%Y')
    except ValueError:
        pass 

    
    # --- 2. Filtros e Consulta ---
    pacotes_detalhe = OnHold.objects.all()

    # Filtro por Data (data_envio)
    if data_inicio and data_fim:
        pacotes_detalhe = pacotes_detalhe.filter(data_envio__range=[data_inicio, data_fim])

    # 💥 LÓGICA DE FILTRO POR STATUS OU MOTIVO (CORREÇÃO DO KPI)
    
    # Verifica se o 'motivo' passado é um dos status gerais (vindo dos KPIs)
    if motivo in ['OnHold', 'LMHub_Received']:
        pacotes_detalhe = pacotes_detalhe.filter(status=motivo)
        titulo_pagina = f"Detalhe: Pacotes com Status '{motivo}'"
        
    else:
        # Padrão: filtra pelo campo 'onhold_reason'
        pacotes_detalhe = pacotes_detalhe.filter(onhold_reason__exact=motivo)
        titulo_pagina = f"Detalhe: Pacotes Retidos por '{motivo}'"


    # --- 3. Ordenação e Contagem ---
    # ✅ NOVO: ORDENAÇÃO POR DRIVER NAME ALFABÉTICO (A-Z)
    # Usamos o TRIM para limpar espaços e garantir a ordem correta antes de ordenar
    pacotes_detalhe = pacotes_detalhe.annotate(
        driver_name_clean=Func('driver_name', function='TRIM') 
    ).order_by('driver_name_clean', '-data_envio') # Ordena por Motorista A-Z, depois por data mais recente
    
    total_pacotes = pacotes_detalhe.count()
    
    # --- 4. Paginação ---
    paginator = Paginator(pacotes_detalhe, 50) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # --- 5. Contexto ---
    context = {
        'page_obj': page_obj,
        'total_pacotes': total_pacotes,
        'selected_reason': motivo,
        'data_inicio_str': data_inicio_str,
        'data_fim_str': data_fim_str,
        'data_inicio_formatada': data_inicio_formatada,
        'data_fim_formatada': data_fim_formatada,
        'titulo_pagina': titulo_pagina,
        'tipo_filtro': 'Status/Motivo',
        'valor_filtro': motivo, 
    }

    # 🚨 NOTA: Renderizando o template 'onhold/consulta_detalhe.html'
    return render(request, 'onhold/consulta_detalhe.html', context)

@login_required
def export_por_motivo_csv(request, motivo):
    # 1. Filtro de Status (o mesmo usado em consulta_por_motivo)
    status_selecionado = request.GET.get('status', 'Todos')
    
    # 2. Filtragem no QuerySet
    registros = OnHold.objects.filter(onhold_reason__exact=motivo)
    
    if status_selecionado != 'Todos':
        registros = registros.filter(status=status_selecionado)
        
    # --- 3. Configuração da Resposta CSV ---
    response = HttpResponse(content_type='text/csv')
    
    # Cria o nome do arquivo dinamicamente (removendo espaços/caracteres para URL/filename)
    filename = f'pacotes_{motivo.replace(" ", "_").replace("/", "-")}_status_{status_selecionado}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    
    # 4. Cabeçalho do CSV
    headers = [
        'SLS Tracking Number', 
        'Status Atual', 
        'Motivo Retencao', 
        'Data Retencao', 
        'HUB Upload',
        'Driver Name',
    ]
    writer.writerow(headers)

    # 5. Escrita dos dados
    for registro in registros.iterator(): 
        writer.writerow([
            registro.sls_tracking_number, 
            registro.status, 
            registro.onhold_reason, 
            # Mantendo onhold_time no export para o dado do evento ser correto
            registro.onhold_time.strftime('%d/%m/%Y') if registro.onhold_time else '', 
            registro.hub_upload.nome if registro.hub_upload else '', 
            registro.driver_name, 
        ])

    return response

def menu_acoes_onhold(request):
    """Renderiza a tela de menu para ações do módulo OnHold."""
    return render(request, 'onhold/menu_acoes_onhold.html', {})

def exportar_onhold_motorista_csv(request):
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    # Filtro por data_envio
    dados_motorista = OnHold.objects \
        .filter(
            data_envio__range=[data_inicio, data_fim], # Usando data_envio
            status='OnHold'
        ) \
        .values('driver_name') \
        .annotate(total_registros=Count('id')) \
        .order_by('-total_registros')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="OnHold_devolver.csv"'

    writer = csv.writer(response)
    
    writer.writerow(['Nome do Motorista', 'Total de Registros OnHold'])

    for item in dados_motorista:
        driver_name = item['driver_name'] if item['driver_name'] else "Motorista Não Informado"
        writer.writerow([driver_name, item['total_registros']])

    return response

def consulta_por_motorista(request):
    selected_driver = request.GET.get('driver_name', 'all')
    data_inicio_str = request.GET.get('data_inicio')
    data_fim_str = request.GET.get('data_fim')
    
    # 1. Obter nomes de motoristas Limpos (para o dropdown)
    all_drivers = (
        OnHold.objects
        .annotate(
            # Cria um campo temporário 'driver_name_clean' com o TRIM aplicado
            driver_name_clean=Func('driver_name', function='TRIM') 
        )
        .values_list('driver_name_clean', flat=True)
        .exclude(driver_name_clean__isnull=True)
        .exclude(driver_name_clean='')
        .distinct()
        .order_by('driver_name_clean')
    )
    
    # 2. QuerySet Inicial: Todos os pacotes
    pacotes_detalhe = OnHold.objects.all()
    
    # 3. Aplicar Filtros
    
    # Filtro por Nome do Motorista
    if selected_driver and selected_driver != 'all':
        # Filtra usando o nome limpo
        pacotes_detalhe = pacotes_detalhe.annotate(
            driver_name_clean=Func('driver_name', function='TRIM') 
        ).filter(driver_name_clean__iexact=selected_driver)
        
    # Filtro por Intervalo de Data 
    data_inicio_formatada = "N/A"
    data_fim_formatada = "N/A"
    
    if data_inicio_str and data_fim_str:
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
            
            # Correto: Usando data_envio para filtrar
            pacotes_detalhe = pacotes_detalhe.filter(data_envio__range=[data_inicio, data_fim])

            data_inicio_formatada = data_inicio.strftime('%d/%m/%Y')
            data_fim_formatada = data_fim.strftime('%d/%m/%Y')
            
        except ValueError:
            pass

    # 4. Ordenação Final
    # Ordenação por data_envio (Data de Envio)
    pacotes_detalhe = pacotes_detalhe.order_by('driver_name', '-data_envio') 

    # 5. Contexto
    context = {
        'all_drivers': all_drivers, 
        'selected_driver': selected_driver, 
        'pacotes': pacotes_detalhe, 
        'total_pacotes': pacotes_detalhe.count(),
        'data_inicio_str': data_inicio_str, 
        'data_fim_str': data_fim_str, 
        'data_inicio_formatada': data_inicio_formatada,
        'data_fim_formatada': data_fim_formatada,
    }

    return render(request, 'onhold/detalhe_motorista.html', context)

@login_required
@transaction.atomic # Garante que ou todas as linhas são salvas, ou nenhuma
def upload_csv_onhold_inicial(request):
    if request.method == 'POST':
        # 0. CAPTURA E VALIDAÇÃO DA DATA DE REFERÊNCIA (Data de Envio)
        data_referencia_str = request.POST.get('data_referencia')
        if not data_referencia_str:
            messages.error(request, "A Data de Referência é obrigatória para a importação.")
            return redirect('upload_onhold_inicial') # <--- MUDANÇA AQUI!

        try:
            data_referencia = datetime.strptime(data_referencia_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Formato de Data de Referência inválido.")
            return redirect('upload_onhold_inicial') # <--- MUDANÇA AQUI!
        
        # 1. Validação de Arquivo
        if 'csv_file' not in request.FILES:
            messages.error(request, 'Nenhum arquivo foi selecionado.')
            return redirect('upload_onhold_inicial') # <--- MUDANÇA AQUI!

        csv_file = request.FILES['csv_file']
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'O arquivo deve ser do tipo CSV.')
            return redirect('upload_onhold_inicial') # <--- MUDANÇA AQUI!

        # 2. Configuração e Leitura
        dataset = csv_file.read().decode('utf-8')
        io_string = io.StringIO(dataset)
        
        try:
            next(io_string) # Pula o cabeçalho
        except StopIteration:
            messages.error(request, 'O arquivo CSV está vazio ou não possui cabeçalho.')
            return redirect('upload_onhold_inicial') # <--- MUDANÇA AQUI!
            
        reader = csv.reader(io_string, delimiter=',')
        
        hub_do_usuario = request.user.hub if request.user.hub else None
        usuario_obj = request.user 
        
        registros_a_criar = []
        linhas_processadas = 0
        
        # O total de colunas esperado é 47 (índice 0 a 46)
        COLUNAS_ESPERADAS = 47

        # 3. Processamento Linha por Linha
        try:
            total_registros_antes = OnholdInicial.objects.count() # <--- MUDANÇA AQUI!

            for i, row in enumerate(reader):
                linhas_processadas += 1
                
                if not row or not row[0]:
                    continue
                
                # Validação para 47 colunas
                if len(row) < COLUNAS_ESPERADAS:
                    messages.warning(request, f"Linha {i+2} ignorada: A linha tem menos colunas do que o esperado ({COLUNAS_ESPERADAS}).")
                    continue
                
                # --- CONVERSÃO DE TIPOS (Flutuantes e Inteiro) ---
                parcel_weight_parsed = parse_float(row[23])
                sls_weight_parsed = parse_float(row[24])
                length_parsed = parse_float(row[25])
                width_parsed = parse_float(row[26])
                height_parsed = parse_float(row[27])
                original_asf_parsed = parse_float(row[28])
                rounding_asf_parsed = parse_float(row[29])
                cod_fee_parsed = parse_float(row[30])
                
                # Delivery Attempts (Inteiro)
                try:
                    delivery_attempts_parsed = int(row[31]) if row[31] else None
                except ValueError:
                    delivery_attempts_parsed = None

                # Adiciona à lista (Usando o novo modelo e mapeamento)
                registros_a_criar.append(OnholdInicial( # <--- MUDANÇA AQUI!
                    hub_upload=hub_do_usuario,
                    usuario_upload=usuario_obj,
                    data_envio=data_referencia, # Usa a data selecionada

                    # Mapeamento (47 colunas)
                    order_id=row[0], sls_tracking_number=row[1], # row[2] 3PL Tracking Number
                    shopee_order_sn=row[3], sort_code_name=row[4], buyer_name=row[5], 
                    buyer_phone=row[6], buyer_address=row[7], location_type=row[8], 
                    postal_code=row[9], driver_id=row[10], driver_name=row[11], 
                    driver_phone=row[12], pick_up_time=row[13], soc_received_time=row[14], 
                    delivered_time=row[15], onhold_time=row[16], onhold_reason=row[17], 
                    reschedule_time=row[18], status=row[19], reject_remark=row[20], 
                    manifest_number=row[21], order_account=row[22], 
                    
                    parcel_weight=parcel_weight_parsed, sls_weight=sls_weight_parsed, 
                    length=length_parsed, width=width_parsed, height=height_parsed, 
                    original_asf=original_asf_parsed, rounding_asf=rounding_asf_parsed, 
                    cod_fee=cod_fee_parsed, 
                    
                    delivery_attempts=delivery_attempts_parsed, bulky_type=row[32], 
                    sla_target_date=row[33], time_to_sla=row[34], payment_method=row[35], 
                    pickup_station=row[36], destination_station=row[37], next_station=row[38], 
                    current_station=row[39], channel=row[40], previous_3pl=row[41], 
                    next_3pl=row[42], shop_id=row[43], shop_category=row[44], 
                    inbound_3pl=row[45], outbound_3pl=row[46],
                ))

            # Execução e Auditoria
            total_tentativas_insercao = len(registros_a_criar)
            OnholdInicial.objects.bulk_create(registros_a_criar, ignore_conflicts=False) # Mantemos False para permitir duplicatas
            
            total_registros_depois = OnholdInicial.objects.count()
            registros_criados_novos = total_registros_depois - total_registros_antes
            
            messages.success(request, f'Sucesso! **{registros_criados_novos}** registros iniciais salvos com Data de Referência: {data_referencia.strftime("%d/%m/%Y")}.')

        except IndexError as e:
            messages.error(request, f'Erro de formato na linha {linhas_processadas+1}. O arquivo CSV parece ter menos colunas do que o esperado. A importação foi cancelada.')
            return redirect('upload_onhold_inicial') # <--- MUDANÇA AQUI!
            
        except Exception as e:
            messages.error(request, f'Erro grave durante o processamento do arquivo: {e}. A importação foi cancelada.')
            return redirect('upload_onhold_inicial') # <--- MUDANÇA AQUI!

        return redirect('dashboard') 

    # Caso seja um GET, apenas renderiza o template
    return render(request, 'onhold/upload_onhold_inicial.html', {'titulo': 'Upload de Dados ONHold Inicial'}) # <--- MUDANÇA AQUI!

@login_required
def dashboard_onhold_inicial_dia(request):
    # 1. Obter Parâmetros de Filtro
    data_inicio_str = request.GET.get('data_inicio')
    data_fim_str = request.GET.get('data_fim')

    # Queryset Base: Assume que o modelo OnholdInicial existe
    pacotes = OnholdInicial.objects.all()

    # 2. Aplicar Filtro de Data
    if data_inicio_str and data_fim_str:
        try:
            # Converte strings para objetos date
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
            
            # Filtra o queryset
            pacotes = pacotes.filter(data_envio__range=[data_inicio, data_fim])
        except ValueError:
            # Caso de erro de formato, ignora o filtro e usa todos os dados
            data_inicio_str = None
            data_fim_str = None
            
    # 3. Cálculos e Agregações
    total_registros = pacotes.count()

    # Contagem por Motorista (TRIM para limpar espaços)
    motoristas_contagem = pacotes.annotate(
        driver_name_clean=Func('driver_name', function='TRIM') 
    ).values('driver_name_clean').annotate(
        total=Count('driver_name_clean')
    ).order_by('-total')
    
    # Contagem por Motivo de Retenção
    motivos_contagem = pacotes.values('onhold_reason').annotate(
        total=Count('onhold_reason')
    ).order_by('-total')

    # 4. Preparar Dados para Gráfico (Chart.js)
    # Pegamos apenas o Top 10 para o gráfico, mas a lista completa para o template
    motoristas_labels = [item['driver_name_clean'] if item['driver_name_clean'] else "(Motorista Não Informado)" for item in motoristas_contagem[:10]]
    motoristas_data = [item['total'] for item in motoristas_contagem[:10]]
    
    motivos_labels = [item['onhold_reason'] if item['onhold_reason'] else "(Motivo Não Informado)" for item in motivos_contagem[:10]]
    motivos_data = [item['total'] for item in motivos_contagem[:10]]
    
    # 5. Contexto Final
    context = {
        'total_registros': total_registros,
        'data_inicio_str': data_inicio_str, # Mantém string para preencher o formulário
        'data_fim_str': data_fim_str,       # Mantém string para preencher o formulário
        
        # Listas para as tabelas e links de detalhe
        'motoristas_contagem': motoristas_contagem,
        'motivos_contagem': motivos_contagem,
        
        # Dados para Chart.js (JSON formatado)
        'motoristas_labels': json.dumps(motoristas_labels),
        'motoristas_data': json.dumps(motoristas_data),
        'motivos_labels': json.dumps(motivos_labels),
        'motivos_data': json.dumps(motivos_data),
    }

    return render(request, 'onhold/dashboard_onhold_inicial_dia.html', context)


@login_required
def detalhe_pacotes_inicial(request):
    # 1. Obter Filtros da URL
    selected_driver = request.GET.get('driver', None)
    selected_reason = request.GET.get('reason', None)
    data_inicio_str = request.GET.get('data_inicio')
    data_fim_str = request.GET.get('data_fim')
    
    # Queryset Base: Assume que o modelo OnholdInicial existe
    pacotes_detalhe = OnholdInicial.objects.all()
    
    # 2. Aplicar Filtros
    
    # Filtro de Driver: Limpa espaços em branco e compara (case-insensitive)
    if selected_driver:
        pacotes_detalhe = pacotes_detalhe.annotate(
            driver_name_clean=Func('driver_name', function='TRIM') 
        ).filter(driver_name_clean__iexact=selected_driver)
        
    # Filtro de Motivo
    if selected_reason:
        pacotes_detalhe = pacotes_detalhe.filter(onhold_reason__iexact=selected_reason)
        
    # Filtro de Intervalo de Data (CRUCIAL: mantém o filtro da dashboard)
    data_inicio_formatada = "N/A"
    data_fim_formatada = "N/A"
    
    if data_inicio_str and data_fim_str:
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
            
            pacotes_detalhe = pacotes_detalhe.filter(data_envio__range=[data_inicio, data_fim])

            data_inicio_formatada = data_inicio.strftime('%d/%m/%Y')
            data_fim_formatada = data_fim.strftime('%d/%m/%Y')
            
        except ValueError:
            pass # Ignora filtros de data inválidos

    # 3. Ordenação e Contagem
    pacotes_detalhe = pacotes_detalhe.order_by('-data_envio')
    total_pacotes = pacotes_detalhe.count()
    
    # 4. Paginação (50 por página é um bom padrão)
    paginator = Paginator(pacotes_detalhe, 50) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # 5. Contexto
    context = {
        'page_obj': page_obj,
        'total_pacotes': total_pacotes,
        'selected_driver': selected_driver,
        'selected_reason': selected_reason,
        'data_inicio_str': data_inicio_str,
        'data_fim_str': data_fim_str,
        'data_inicio_formatada': data_inicio_formatada,
        'data_fim_formatada': data_fim_formatada,
        # Variáveis para o Título na página de detalhe
        'tipo_filtro': 'Motorista' if selected_driver else ('Motivo' if selected_reason else 'Geral'),
        'valor_filtro': selected_driver if selected_driver else selected_reason if selected_reason else 'Todos',
    }

    # 🚨 PONTO DE TESTE: Alterar o nome para forçar um erro de template
    # Se esta view for a correta, um erro 'TemplateDoesNotExist' deve ocorrer.
    return render(request, 'onhold/TESTE_NAO_EXISTE.html', context)

def get_city_from_cep(cep):
    """
    Consulta a API do ViaCEP para obter a cidade a partir do CEP.
    """
    if not cep:
        return "CEP Não Informado"
        
    # Remove caracteres não numéricos
    cep_limpo = ''.join(filter(str.isdigit, cep))
    if len(cep_limpo) != 8:
        return "CEP Inválido"

    # API ViaCEP (retorna JSON com o campo 'localidade')
    url = f"https://viacep.com.br/ws/{cep_limpo}/json/"
    
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            # Se não houver erro no retorno da API
            if not data.get('erro'):
                return data.get('localidade', 'Cidade Não Encontrada')
        return "Cidade Não Encontrada"
    except requests.exceptions.RequestException:
        # Lidar com erros de conexão/timeout
        return "Erro de Conexão/API"
    except Exception:
        # Erros diversos
        return "Erro Desconhecido"
    
@login_required
def detalhe_volumosos(request):
    """
    Exibe a lista de pacotes On Hold classificados como 'Volumosos' (KPI),
    com filtros adicionais por Sort Code Name (bairro) e Cidade.
    """
    # 1. Recuperação e validação das datas (De/Até)
    data_inicio_str = request.GET.get('data_inicio')
    data_fim_str = request.GET.get('data_fim')
    
    # NOVOS FILTROS DE TEXTO (Aqui, eles vêm como o valor selecionado do dropdown)
    filtro_sort_code_name = request.GET.get('sort_code_name')
    filtro_cidade = request.GET.get('cidade')
    
    data_inicio = None
    data_fim = None
    
    try:
        if data_inicio_str:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        if data_fim_str:
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, "Formato de data inválido.")
        return redirect('dashboard_onhold')

    # 2. Query Principal: Filtragem dos "Volumosos" + Filtro por Data
    pacotes_volumosos_base_qs = OnHold.objects.filter(
        onhold_reason='Insufficient Vehicle Capacity',
        status='LMHub_Received'
    )
    
    if data_inicio and data_fim:
         pacotes_volumosos_base_qs = pacotes_volumosos_base_qs.filter(data_envio__range=[data_inicio, data_fim])
         
    # 4. PRÉ-CÁLCULO DOS VALORES ÚNICOS PARA OS DROPDOWNS
    
    # 4.1. LISTA DE BAIRROS (Sort Code Name)
    sort_code_options = pacotes_volumosos_base_qs.values_list(
        'sort_code_name', flat=True
    ).distinct().exclude(sort_code_name__isnull=True).order_by('sort_code_name')
    
    
    # 4.2. LISTA DE CIDADES
    cep_options_qs = pacotes_volumosos_base_qs.values_list(
        'postal_code', flat=True
    ).distinct().exclude(postal_code__isnull=True)
    
    cidades_unicas = set()
    for cep in cep_options_qs:
        cidade = get_city_from_cep(cep)
        if cidade and cidade != 'Não Encontrada':
            cidades_unicas.add(cidade)
            
    cidades_options = sorted(list(cidades_unicas)) 

    # 5. Aplicação do filtro nativo (Sort Code Name / Bairro)
    pacotes_volumosos_final_qs = pacotes_volumosos_base_qs
    
    if filtro_sort_code_name:
         pacotes_volumosos_final_qs = pacotes_volumosos_final_qs.filter(
             sort_code_name=filtro_sort_code_name
         )


    # 6. Paginação
    # 💥 REMOVIDA A ORDENAÇÃO POR DATA_ENVIO AQUI, POIS SERÁ FEITA EM MEMÓRIA POR CIDADE
    paginator = Paginator(pacotes_volumosos_final_qs, 100) 
    page_number = request.GET.get('page')
    page_obj_queryset = paginator.get_page(page_number)
    
    # 7. Adicionar a Cidade e Ordenar
    page_pacotes_resolved = []
    
    # Constrói a lista com o campo 'cidade' resolvido pela API
    for pacote in page_obj_queryset:
        cidade_resolvida = get_city_from_cep(pacote.postal_code) # CHAMA A FUNÇÃO DE CEP/CIDADE
        
        page_pacotes_resolved.append({
            'sls_tracking_number': pacote.sls_tracking_number,
            'onhold_reason': pacote.onhold_reason,
            'sort_code_name': pacote.sort_code_name,
            'postal_code': pacote.postal_code,
            'cidade': cidade_resolvida, 
        })
        
    # 💥 NOVA ORDENAÇÃO: Ordenar em memória por Cidade (ordem alfabética)
    # A ordenação é feita na lista de objetos da página atual
    page_pacotes_resolved.sort(key=lambda item: item['cidade'])


    # 8. Aplicação do filtro de CIDADE (Feito na memória)
    pacotes_com_cidade = []
    
    if filtro_cidade:
        # Se houver filtro, filtra a lista já resolvida e ordenada
        pacotes_com_cidade = [
            item for item in page_pacotes_resolved
            if item['cidade'] == filtro_cidade # Usamos igualdade, pois é um valor selecionado do dropdown
        ]
    else:
        # Se não houver filtro, usa a lista resolvida e ordenada completa da página atual
        pacotes_com_cidade = page_pacotes_resolved
        
    # 9. Estrutura o Contexto
    
    class CustomPageObject:
        def __init__(self, page_obj, items):
            self.__dict__ = page_obj.__dict__.copy()
            self.object_list = items
            # Se a lista foi filtrada na memória (filtro_cidade ativo), a paginação padrão é "desligada"
            self.has_previous = lambda: self.__dict__.get('has_previous') and not filtro_cidade
            self.has_next = lambda: self.__dict__.get('has_next') and not filtro_cidade

    page_obj_final = CustomPageObject(page_obj_queryset, pacotes_com_cidade)


    context = {
        'page_obj': page_obj_final,
        'total_pacotes': pacotes_volumosos_base_qs.count(),
        'data_inicio_str': data_inicio_str,
        'data_fim_str': data_fim_str,
        'titulo': "Pacotes Retidos por Insufficient Vehicle Capacity",
        'subtitulo': "LMHub Received",
        
        'filtro_sort_code_name_value': filtro_sort_code_name or '',
        'filtro_cidade_value': filtro_cidade or '',
        
        'sort_code_options': sort_code_options,
        'cidades_options': cidades_options,
        
        'colunas_selecionadas': ['SLS Tracking Number', 'OnHoldReason', 'Sort Code Name', 'Postal Code', 'Cidade'] 
    }

    return render(request, 'onhold/detalhe_volumosos.html', context)