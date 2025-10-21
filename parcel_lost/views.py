# parcel_lost/views.py

import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required 
from django.contrib import messages
from django.db.models import Count, Value as V, CharField
from django.db.models.functions import ExtractDay, ExtractMonth, ExtractYear, Concat
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Q 
from django.core.paginator import Paginator 

from .forms import ParcelLostForm, LostFilterForm
from .models import ParcelLost

# ----------------------------------------------------
# VIEWS DE NAVEGAÇÃO E REGISTRO 
# ----------------------------------------------------
@login_required
def menu_actions_lost(request):
    """Tela inicial com opções de Dashboard e Cadastro para Lost & Damage."""
    return render(request, 'parcel_lost/menu_actions_lost.html')

@login_required
def register_lost(request):
    """View para registrar uma nova perda/avaria manualmente."""
    if request.method == 'POST':
        form = ParcelLostForm(request.POST)
        if form.is_valid():
            new_record = form.save(commit=False)
            new_record.usuario_registro = request.user
            new_record.save()
            messages.success(request, "Registro de Perda/Avaria criado com sucesso!")
            
            # 🔑 CORREÇÃO AQUI: Mudando o nome da URL para 'dashboard_lost' 🔑
            return redirect('parcel_lost:dashboard_lost') 
    else:
        form = ParcelLostForm()
        
    context = {
        'form': form,
        'titulo': 'Registrar Nova Ocorrência',
    }
    return render(request, 'parcel_lost/register_lost.html', context)

# ----------------------------------------------------
# DASHBOARD (KPIs e Gráficos)
# ----------------------------------------------------
@login_required
def dashboard_lost(request):
    form = LostFilterForm(request.GET)
    queryset = ParcelLost.objects.all()
    
    if form.is_valid():
        data_inicio = form.cleaned_data.get('data_inicio')
        data_fim = form.cleaned_data.get('data_fim')
        tipo_avaria = form.cleaned_data.get('tipo_avaria')

        if data_inicio and data_fim:
            data_fim_ajustada = data_fim + timedelta(days=1)
            queryset = queryset.filter(data_registro__range=[data_inicio, data_fim_ajustada])
            
        if tipo_avaria:
            queryset = queryset.filter(final_status_avaria__icontains=tipo_avaria)

    # --- Cálculo dos KPIs (Para as Cartas Clicáveis) ---
    kpis = queryset.aggregate(
        total_lost=Count('id', filter=Q(final_status_avaria__icontains='LOST')),
        total_damage=Count('id', filter=Q(final_status_avaria__icontains='DAMAGE')),
        soc_lost=Count('id', filter=Q(final_status_avaria='SOC_LOST')),
        hub_lost=Count('id', filter=Q(final_status_avaria='HUB_LOST')),
        soc_damage=Count('id', filter=Q(final_status_avaria='SOC_DAMAGE')),
        hub_damage=Count('id', filter=Q(final_status_avaria='HUB_DAMAGE')),
    )

    # --- Gráfico 1: Quantidade por Dia (Coluna) ---
    daily_chart_data = queryset.annotate(
        day=ExtractDay('data_registro'),
        month=ExtractMonth('data_registro'),
        year=ExtractYear('data_registro')
    ).values('year', 'month', 'day').annotate(
        # ✅ ALTERAÇÃO: Contagem separada por SOC/HUB
        soc_lost=Count('id', filter=Q(final_status_avaria='SOC_LOST')),
        hub_lost=Count('id', filter=Q(final_status_avaria='HUB_LOST')),
        soc_damage=Count('id', filter=Q(final_status_avaria='SOC_DAMAGE')),
        hub_damage=Count('id', filter=Q(final_status_avaria='HUB_DAMAGE')),
    ).order_by('year', 'month', 'day')
    
    # Gerando labels no formato DD/MM
    chart1_labels = [f"{item['day']:02d}/{item['month']:02d}" for item in daily_chart_data]
    # ✅ NOVOS DADOS PARA O CONTEXTO
    chart1_soc_lost_data = [item['soc_lost'] for item in daily_chart_data]
    chart1_hub_lost_data = [item['hub_lost'] for item in daily_chart_data]
    chart1_soc_damage_data = [item['soc_damage'] for item in daily_chart_data]
    chart1_hub_damage_data = [item['hub_damage'] for item in daily_chart_data]
    
    # Serializando para JSON Strings
    chart1_labels = json.dumps(chart1_labels)
    chart1_soc_lost_data = json.dumps(chart1_soc_lost_data)
    chart1_hub_lost_data = json.dumps(chart1_hub_lost_data)
    chart1_soc_damage_data = json.dumps(chart1_soc_damage_data)
    chart1_hub_damage_data = json.dumps(chart1_hub_damage_data)
    
    
    # --- Gráfico 2: Evolução Mês a Mês (Linha) ---
    monthly_data = queryset.annotate(
        year_month=Concat(ExtractYear('data_registro'), V('-'), ExtractMonth('data_registro'), output_field=CharField())
    ).values('year_month').annotate(
        total=Count('id'),
        # ✅ ALTERAÇÃO: Contagem separada por SOC/HUB
        soc_lost=Count('id', filter=Q(final_status_avaria='SOC_LOST')),
        hub_lost=Count('id', filter=Q(final_status_avaria='HUB_LOST')),
        soc_damage=Count('id', filter=Q(final_status_avaria='SOC_DAMAGE')),
        hub_damage=Count('id', filter=Q(final_status_avaria='HUB_DAMAGE')),
    ).order_by('year_month')
    
    chart2_labels = [item['year_month'] for item in monthly_data]
    # ✅ NOVOS DADOS PARA O CONTEXTO
    chart2_soc_lost_data = [item['soc_lost'] for item in monthly_data]
    chart2_hub_lost_data = [item['hub_lost'] for item in monthly_data]
    chart2_soc_damage_data = [item['soc_damage'] for item in monthly_data]
    chart2_hub_damage_data = [item['hub_damage'] for item in monthly_data]
    
    # Serializando para JSON Strings
    chart2_labels = json.dumps(chart2_labels)
    chart2_soc_lost_data = json.dumps(chart2_soc_lost_data)
    chart2_hub_lost_data = json.dumps(chart2_hub_lost_data)
    chart2_soc_damage_data = json.dumps(chart2_soc_damage_data)
    chart2_hub_damage_data = json.dumps(chart2_hub_damage_data)

    print("\n--- DEBUG: DADOS DO DASHBOARD ---")
    print(f"Total de Registros Após Filtros: {queryset.count()}")
    print("Daily Chart Labels (JSON):", chart1_labels)
    print("Monthly Chart Labels (JSON):", chart2_labels)
    print("--- FIM DEBUG ---\n")
    
    context = {
        'form': form,
        'total_registros': queryset.count(),
        'kpis': kpis,
        
        # Dados para Gráfico 1 (4 conjuntos de dados)
        'chart1_labels': chart1_labels,
        'chart1_soc_lost_data': chart1_soc_lost_data,
        'chart1_hub_lost_data': chart1_hub_lost_data,
        'chart1_soc_damage_data': chart1_soc_damage_data,
        'chart1_hub_damage_data': chart1_hub_damage_data,
        
        # Dados para Gráfico 2 (4 conjuntos de dados)
        'chart2_labels': chart2_labels,
        'chart2_soc_lost_data': chart2_soc_lost_data,
        'chart2_hub_lost_data': chart2_hub_lost_data,
        'chart2_soc_damage_data': chart2_soc_damage_data,
        'chart2_hub_damage_data': chart2_hub_damage_data,
    }
    return render(request, 'parcel_lost/dashboard_lost.html', context)

# ----------------------------------------------------
# TELA DE DETALHES 
# ----------------------------------------------------
@login_required
def lost_detail_list(request, type_slug):
    
    # 1. Obter Queryset Base e Parâmetros de Filtro
    queryset = ParcelLost.objects.all()
    filter_params = request.GET.urlencode()
    
    # 2. Aplicar Filtros da URL (Dashboard)
    data_inicio_str = request.GET.get('data_inicio')
    data_fim_str = request.GET.get('data_fim')
    
    if data_inicio_str and data_fim_str:
        try:
            data_inicio_date = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            # Ajusta para incluir o último dia
            data_fim_date = datetime.strptime(data_fim_str, '%Y-%m-%d').date() + timedelta(days=1)
            queryset = queryset.filter(data_registro__range=[data_inicio_date, data_fim_date])
        except ValueError:
            pass # Ignora o filtro de data se a conversão falhar
    
    # 3. Aplicar Filtro do Slug (Tipo de Ocorrência)
    if type_slug == 'total-lost':
        queryset = queryset.filter(final_status_avaria__icontains='LOST')
        detail_name = "Todas as Perdas (Lost)"
    elif type_slug == 'total-damage':
        queryset = queryset.filter(final_status_avaria__icontains='DAMAGE')
        detail_name = "Todas as Avarias (Damage)"
    else:
        # Tenta filtrar pelo valor exato (SOC_LOST, HUB_DAMAGE, etc.)
        status_name = type_slug.replace('-', '_').upper()
        queryset = queryset.filter(final_status_avaria=status_name)
        detail_name = status_name.replace('_', ' - ')

    # 4. Paginação
    paginator = Paginator(queryset.order_by('-data_registro', '-data_registro_sistema'), 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'titulo': f'Detalhes: {detail_name}',
        'page_obj': page_obj,
        'total_registros': queryset.count(),
        'filter_params': filter_params,
        'count_type_name': detail_name,
        'export_url': '', 
    }
    return render(request, 'parcel_lost/lost_detail_list.html', context)