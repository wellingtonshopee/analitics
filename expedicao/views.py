# views.py

from django.shortcuts import render, redirect
from django.views.generic import View, ListView 
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import transaction, models # Import 'models' para agregados (Sum, Count)
from django.utils.dateparse import parse_datetime, parse_date
from django.utils.timezone import make_aware 
from datetime import timedelta 
import csv
import io


from .forms import ExpedicaoArquivoForm 
from .models import ExpedicaoArquivo, RegistroExpedicao

class UploadExpedicaoView(LoginRequiredMixin, View):
    template_name = 'expedicao/upload.html'
    
    def get(self, request):
        form = ExpedicaoArquivoForm()
        return render(request, self.template_name, {'form': form, 'titulo': 'Upload de Arquivo de Expedição'})

    def post(self, request):
        form = ExpedicaoArquivoForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Salvar Metadados do Arquivo (ExpedicaoArquivo)
                    expedicao_arquivo = form.save(commit=False)
                    expedicao_arquivo.enviado_por = request.user
                    expedicao_arquivo.save() 

                    # 2. Ler e processar o CSV a partir do FileField
                    arquivo_obj = expedicao_arquivo.arquivo.open('rb') 
                    decoded_file = arquivo_obj.read().decode('utf-8') 
                    arquivo_obj.close() 

                    io_string = io.StringIO(decoded_file)
                    reader = csv.reader(io_string, delimiter=',')
                    header = next(reader) # Pula o cabeçalho

                    registros_para_criar = []
                    contador_registros = 0
                    
                    # Itera sobre as linhas
                    for row in reader:
                        if any(field.strip() for field in row):
                            contador_registros += 1
                            
                            try:
                                # --- TRATAMENTO DOS DATETIMES ---
                                start_time_naive = parse_datetime(row[7]) if row[7] else None
                                end_time_naive = parse_datetime(row[8]) if row[8] else None

                                validation_start_time = make_aware(start_time_naive) if start_time_naive else None
                                validation_end_time = make_aware(end_time_naive) if end_time_naive else None
                                # --------------------------------------------------------

                                registro = RegistroExpedicao(
                                    arquivo_origem=expedicao_arquivo,
                                    at_to=row[0],
                                    corridor_cage=row[1],
                                    total_initial_orders=int(row[2]) if row[2] else 0,
                                    total_final_orders=int(row[3]) if row[3] else 0,
                                    total_scanned_orders=int(row[4]) if row[4] else 0,
                                    missorted_orders=int(row[5]) if row[5] else 0,
                                    missing_orders=int(row[6]) if row[6] else 0,
                                    
                                    validation_start_time=validation_start_time, 
                                    validation_end_time=validation_end_time, 
                                    
                                    validation_operator=row[9],
                                    revalidation_operator=row[10],
                                    revalidated_count=int(row[11]) if row[11] else 0,
                                    at_to_validation_status=row[12],
                                    remark=row[13] if len(row) > 13 else None,
                                )
                                registros_para_criar.append(registro)
                            except (ValueError, IndexError) as e:
                                messages.error(request, f"Erro ao processar a linha {contador_registros} (Erro: {e}). O registro foi ignorado.")
                                continue

                    RegistroExpedicao.objects.bulk_create(registros_para_criar)
                    
                    expedicao_arquivo.num_registros = len(registros_para_criar)
                    expedicao_arquivo.save()
                    
                    messages.success(request, f"Upload e processamento concluído! {expedicao_arquivo.num_registros} registros importados e o arquivo salvo em {expedicao_arquivo.arquivo.name.split('/')[-1]}.")
                    
                    return redirect('expedicao:dashboard')

            except Exception as e:
                messages.error(request, f"Ocorreu um erro crítico durante o processamento do arquivo: {e}")
        else:
            messages.error(request, "O formulário possui erros. Verifique os campos e tente novamente.")

        return render(request, self.template_name, {'form': form, 'titulo': 'Upload de Arquivo de Expedição'})


## Dashboard Expedição (Com Filtro de Data)

class DashboardExpedicaoView(LoginRequiredMixin, ListView):
    """Exibe a lista de todos os arquivos de expedição enviados, com filtro por data de envio (data_envio)."""
    model = ExpedicaoArquivo
    template_name = 'expedicao/dashboard.html'
    context_object_name = 'arquivos'
    ordering = ['-data_envio']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Recebe os parâmetros de data do GET
        data_inicio_str = self.request.GET.get('data_inicio')
        data_fim_str = self.request.GET.get('data_fim')

        data_inicio = parse_date(data_inicio_str) if data_inicio_str else None
        data_fim = parse_date(data_fim_str) if data_fim_str else None
        
        # Filtra pela data de envio
        if data_inicio:
            # Filtra por data_envio maior ou igual à data_inicio (início do dia)
            queryset = queryset.filter(data_envio__gte=data_inicio)
        
        if data_fim:
            # Filtra por data_envio menor que o início do dia seguinte (incluindo o dia inteiro)
            data_fim_ajustada = data_fim + timedelta(days=1)
            queryset = queryset.filter(data_envio__lt=data_fim_ajustada)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Dashboard de Expedição'
        # Passa os valores atuais do filtro para o template manter os campos preenchidos
        context['data_inicio_selecionada'] = self.request.GET.get('data_inicio', '')
        context['data_fim_selecionada'] = self.request.GET.get('data_fim', '')
        return context

## Detalhes Expedição (View de KPI)
class DetalhesExpedicaoView(LoginRequiredMixin, View):
    """Exibe os detalhes e KPIs de um arquivo de expedição específico (ExpedicaoArquivo)."""
    template_name = 'expedicao/detalhes.html'
    LIMIAR_MISSORTED_PERCENTUAL = 0.67 # Limiar de 0.67% para Missorted Orders

    def get(self, request, pk):
        try:
            arquivo = ExpedicaoArquivo.objects.get(pk=pk)
            
            # FILTRO E ORDENAÇÃO: Ordena os registros por nome do operador (validation_operator)
            registros = RegistroExpedicao.objects.filter(arquivo_origem=arquivo).order_by('validation_operator')
            
            # 1. Cálculo dos KPIs Gerais (Agregações)
            kpi_agregados = registros.aggregate(
                total_iniciais=models.Sum('total_initial_orders'),
                total_finais=models.Sum('total_final_orders'),
                total_escaneados=models.Sum('total_scanned_orders'),
                total_missorted=models.Sum('missorted_orders'), # <-- Usado aqui
                total_missing=models.Sum('missing_orders')
            )
            
            # KPI: Total de Rotas (Contagem de valores únicos na coluna at_to)
            total_rotas = registros.values('at_to').distinct().count()

            # 2. Cálculo dos Operadores com Erros e Produtividade
            
            # Anota o total de erros, os erros individuais (Missorted e Missing) E a produtividade
            erros_e_produtividade_por_operador = registros.values('validation_operator').annotate(
                total_erros=models.Sum('missorted_orders') + models.Sum('missing_orders'),
                missorted_orders=models.Sum('missorted_orders'),
                missing_orders=models.Sum('missing_orders'),
                total_registros=models.Count('id') # Conta a quantidade de registros por operador
            ).filter(
                validation_operator__isnull=False
            ).exclude(
                validation_operator__exact=''
            )

            # Operador com MAIS Erros (Critério: Mais erros, desempata por mais registros)
            operador_mais_erros = erros_e_produtividade_por_operador.order_by('-total_erros', '-total_registros').first()
            
            # Operador MAIS PRODUTIVO (Critério: Foca apenas em registros)
            operador_mais_produtivo = erros_e_produtividade_por_operador.order_by('-total_registros').first()

            # 3. Organização do Contexto
            total_iniciais = kpi_agregados.get('total_iniciais') or 0
            total_escaneados = kpi_agregados.get('total_escaneados') or 0
            total_missorted = kpi_agregados.get('total_missorted') or 0 # <-- Corrigido
            
            percentual_escaneado = (total_escaneados / total_iniciais) * 100 if total_iniciais > 0 else 0
            
            # 4. NOVO CÁLCULO DE KPI DE MISSORTED (Corrigido)
            
            # Porcentagem de Missorted Orders
            if total_iniciais > 0:
                percentual_missorted = (total_missorted / total_iniciais) * 100
            else:
                percentual_missorted = 0
            
            # Status e cor baseados no limiar
            if percentual_missorted > self.LIMIAR_MISSORTED_PERCENTUAL:
                status_missorted = {'cor': 'danger', 'texto': 'ACIMA DO LIMIAR (RUIM)', 'status_ok': False}
            else:
                status_missorted = {'cor': 'success', 'texto': 'ABAIXO DO LIMIAR (OK)', 'status_ok': True}

            context = {
                'titulo': f"Detalhes do Arquivo: {arquivo.data_referencia.strftime('%d/%m/%Y')}",
                'arquivo': arquivo,
                'registros': registros[:50], # Amostra: Exibe os primeiros 50 registros ordenados
                'kpis': {
                    # KPIs GERAIS
                    'total_rotas': total_rotas,
                    'total_iniciais': total_iniciais,
                    'total_finais': kpi_agregados.get('total_finais') or 0,
                    'total_escaneados': total_escaneados,
                    'total_missorted': total_missorted, # <-- Corrigido
                    'total_missing': kpi_agregados.get('total_missing') or 0,
                    'percentual_escaneado': f"{percentual_escaneado:.2f}%",

                    # NOVO KPI DE GRÁFICO (Renomeado)
                    'kpi_missorted': {
                        'limiar': self.LIMIAR_MISSORTED_PERCENTUAL,
                        'percentual': percentual_missorted,
                        'status': status_missorted,
                    },

                    # KPIs DE OPERADOR
                    'operador_mais_erros': operador_mais_erros,
                    'operador_mais_produtivo': operador_mais_produtivo,
                }
            }
            return render(request, self.template_name, context)

        except ExpedicaoArquivo.DoesNotExist:
            messages.error(request, "Arquivo de Expedição não encontrado.")
            return redirect('expedicao:dashboard')