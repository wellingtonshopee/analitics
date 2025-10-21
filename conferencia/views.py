# conferencia/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction, connection
from django.http import HttpResponse
# IMPORTAÇÃO AJUSTADA para incluir o novo formulário
from .forms import UploadArquivoForm, ChecagemRapidaForm 
from .models import RegistroConferencia, UploadConferencia
import pandas as pd
import csv
import io
import logging

logger = logging.getLogger(__name__)


# --- 2. VIEW PARA UPLOAD DE ARQUIVOS ---
def upload_arquivos(request):
    if request.method == 'POST':
        form = UploadArquivoForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # 1. Limpar registros antigos
                RegistroConferencia.objects.all().delete()
                UploadConferencia.objects.all().delete()
                
                lista_a_file = request.FILES['lista_a']
                lista_b_file = request.FILES['lista_b']
                
                # Processa e carrega a Lista A e B
                processar_e_carregar_lista(lista_a_file, 'A')
                processar_e_carregar_lista(lista_b_file, 'B')
                
                messages.success(request, "Arquivos carregados com sucesso! Você pode agora executar a conferência.")
                return redirect('conferencia:listagem_resultados')

            except Exception as e:
                # CAPTURA E REGISTRA O ERRO COMPLETO
                logger.error(f"Erro grave ao processar o upload: {e}", exc_info=True)
                messages.error(request, f"Erro ao processar os arquivos. Detalhe: {e}")
                
        else:
            messages.error(request, "Por favor, corrija os erros do formulário.")
            
    else:
        form = UploadArquivoForm()
    
    context = {'form': form}
    return render(request, 'conferencia/upload_form.html', context)


# Função auxiliar FINALMENTE AJUSTADA para processar e carregar os dados
def processar_e_carregar_lista(arquivo_uploaded, tipo_lista):
    """Lê o arquivo de upload (CSV, TXT, XLSX) e insere os códigos no banco de dados."""
    
    # 1. Salva o metadado do upload
    upload = UploadConferencia.objects.create(
        tipo_lista=tipo_lista, 
        arquivo_original=arquivo_uploaded
    )
    
    codigos_encontrados = []
    file_name = arquivo_uploaded.name.lower()
    
    # 2. Lógica de leitura eficiente (Robusta para CSV/TXT, Pandas para XLSX)
    if file_name.endswith(('.csv', '.txt')):
        conteudo_bruto = ""
        
        # --- LÓGICA ROBUSTA PARA LEITURA DE CODIFICAÇÃO ---
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            arquivo_uploaded.seek(0) # Reposiciona o ponteiro para o início antes de cada leitura
            try:
                conteudo_bruto = arquivo_uploaded.read().decode(encoding)
                break  # Se a leitura for bem sucedida, sai do loop
            except UnicodeDecodeError:
                continue # Tenta a próxima codificação
            except Exception:
                # Captura outros erros de leitura (ex: arquivo vazio ou quebrado)
                break
        
        # Se a leitura falhou em todas as codificações (conteudo_bruto vazio)
        if not conteudo_bruto:
             raise ValueError(f"O arquivo {arquivo_uploaded.name} está vazio, corrompido ou com codificação desconhecida.")


        # --- Tenta a Leitura como COLUNA ÚNICA ---
        codigos_do_upload = []
        for linha in conteudo_bruto.splitlines():
            codigo = linha.strip()
            if codigo:
                codigos_do_upload.append(codigo)

        # --- Se a Leitura de Coluna Única falhou, tenta a Leitura com DELIMITADORES (Pandas) ---
        if not codigos_do_upload:
            data_buffer = io.StringIO(conteudo_bruto)
            delimiters = [',', ';', '\t'] 
                
            for sep in delimiters:
                try:
                    data_buffer.seek(0) # Reposiciona o ponteiro do buffer interno
                    df = pd.read_csv(data_buffer, sep=sep, header=None, dtype=str, engine='python')
                    
                    if not df.empty and df.shape[1] > 0:
                        # Se encontrou, extrai a primeira coluna e sai
                        codigos = df.iloc[:, 0].fillna('').str.strip()
                        codigos_do_upload.extend([c for c in codigos if c])
                        break 
                except Exception:
                    continue 
            
        codigos_encontrados.extend(codigos_do_upload)

    elif file_name.endswith('.xlsx'):
        # Processamento para XLSX/XLS (Mantido com Pandas)
        try:
            # dtype=str para preservar zeros à esquerda
            df = pd.read_excel(arquivo_uploaded, header=None, dtype=str)
            
            if df.empty or df.shape[1] == 0:
                 raise ValueError("O arquivo Excel está vazio.")
                 
            # Seleciona todos os valores da primeira coluna (índice 0)
            codigos = df.iloc[:, 0].fillna('').str.strip()
            
            for codigo in codigos: 
                if codigo: # Ignora linhas vazias após o strip
                    codigos_encontrados.append(codigo)

        except Exception as e:
            raise ValueError(f"Erro ao ler arquivo XLSX: {e}")
            
    else:
        raise ValueError("Formato de arquivo não suportado. Use CSV, TXT ou XLSX.")

    # 3. Verificação Final
    if not codigos_encontrados:
        raise ValueError(f"O arquivo {arquivo_uploaded.name} não contém códigos válidos após a leitura.")

    # 4. Preparar objetos para inserção em massa
    registros_a_inserir = []
    
    for codigo in codigos_encontrados: 
        registros_a_inserir.append(
            RegistroConferencia(
                codigo_item=codigo[:255], 
                lista_origem=tipo_lista,
                status_conferencia='PENDENTE',
            )
        )

    # 5. Inserção em massa
    RegistroConferencia.objects.bulk_create(
        registros_a_inserir, 
        ignore_conflicts=True, 
        batch_size=2000
    )
    
    # 6. Atualiza o status do upload
    upload.status = 'CARREGADO'
    upload.save()


# --- NOVA: VIEW PARA FORMULÁRIO DE CHECAGEM RÁPIDA (Etapa 1: Input) ---
def checagem_rapida_form(request):
    form = ChecagemRapidaForm()
    context = {'form': form, 'titulo': 'Checagem Rápida de Listas'}
    return render(request, 'conferencia/checagem_rapida_form.html', context)


# --- NOVA: VIEW PARA PROCESSAR CHECAGEM RÁPIDA (Etapa 2: Processamento e Resultado) ---
def processar_checagem_rapida(request):
    if request.method == 'POST':
        form = ChecagemRapidaForm(request.POST)
        if form.is_valid():
            lista_a_raw = form.cleaned_data['lista_a']
            lista_b_raw = form.cleaned_data['lista_b']
            
            try:
                # 1. Processar e obter códigos únicos (remover vazios e espaços)
                codigos_a = set([c.strip() for c in lista_a_raw.splitlines() if c.strip()])
                codigos_b = set([c.strip() for c in lista_b_raw.splitlines() if c.strip()])

                # 2. Executar Lógica de Comparação (A - B, B - A, A ∩ B)
                somente_a = codigos_a - codigos_b
                somente_b = codigos_b - codigos_a
                presente_em_ambas = codigos_a.intersection(codigos_b)

                # 3. Preparar o contexto para o template de resultados
                context = {
                    'titulo': 'Resultados da Checagem Rápida',
                    # Converte para lista e ordena para exibição
                    'somente_a_list': sorted(list(somente_a)),
                    'somente_b_list': sorted(list(somente_b)),
                    'presente_em_ambas_list': sorted(list(presente_em_ambas)),
                    'count_a': len(somente_a),
                    'count_b': len(somente_b),
                    'count_ambas': len(presente_em_ambas),
                    'total_a_origem': len(codigos_a),
                    'total_b_origem': len(codigos_b),
                    'is_quick_check': True,
                }
                
                return render(request, 'conferencia/checagem_rapida_resultado.html', context)

            except Exception as e:
                logger.error(f"Erro ao processar checagem rápida: {e}", exc_info=True)
                messages.error(request, f"Erro ao processar as listas. Detalhe: {e}")
                return redirect('conferencia:checagem_rapida_form')
        else:
            # Se o formulário for inválido (ex: limite de 1000 excedido)
            context = {'form': form, 'titulo': 'Checagem Rápida de Listas'}
            return render(request, 'conferencia/checagem_rapida_form.html', context)
    
    return redirect('conferencia:checagem_rapida_form')


# --- 3. VIEW PARA EXECUÇÃO DA CONFERÊNCIA ---
def executar_conferencia(request):
    # Usamos uma transação para garantir que a atualização seja atômica
    with transaction.atomic():
        # 1. Encontrar todos os códigos únicos (conjunto de Lista A)
        codigos_a = set(
            RegistroConferencia.objects.filter(lista_origem='A')
            .values_list('codigo_item', flat=True)
        )
        
        # 2. Encontrar todos os códigos únicos (conjunto de Lista B)
        codigos_b = set(
            RegistroConferencia.objects.filter(lista_origem='B')
            .values_list('codigo_item', flat=True)
        )

        # --- LÓGICA DE COMPARAÇÃO DE CONJUNTOS (A - B, B - A, A ∩ B) ---
        
        # Somente na Lista A (Azul) - A - B
        somente_a = codigos_a - codigos_b
        RegistroConferencia.objects.filter(
            codigo_item__in=somente_a,
            lista_origem='A'
        ).update(status_conferencia='SOMENTE_A')

        # Somente na Lista B (Vermelho) - B - A
        somente_b = codigos_b - codigos_a
        RegistroConferencia.objects.filter(
            codigo_item__in=somente_b,
            lista_origem='B'
        ).update(status_conferencia='SOMENTE_B')

        # Presente em Ambas (Verde) - A ∩ B
        presente_em_ambas = codigos_a.intersection(codigos_b)
        RegistroConferencia.objects.filter(
            codigo_item__in=presente_em_ambas
        ).update(status_conferencia='PRESENTE')
        
        # Atualiza o status do upload
        UploadConferencia.objects.update(status='CONFERIDO')

    messages.success(request, "Conferência de dados concluída com sucesso! Os resultados foram atualizados.")
    return redirect('conferencia:listagem_resultados')

# --- 4. VIEW PARA APAGAR REGISTROS ---
def apagar_registros(request):
    if request.method == 'POST':
        RegistroConferencia.objects.all().delete()
        UploadConferencia.objects.all().delete()
        messages.success(request, "Todos os registros de conferência foram apagados do banco de dados.")
        return redirect('conferencia:listagem_resultados')
        
    messages.info(request, "Use o botão 'Apagar Registros' via POST para confirmar a exclusão.")
    return redirect('conferencia:listagem_resultados')

# --- 5. VIEW PARA EXPORTAÇÃO DE RESULTADOS (CSV) ---
def exportar_resultados(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="resultados_conferencia.csv"'

    writer = csv.writer(response)
    
    writer.writerow(['Codigo do Item', 'Lista de Origem', 'Resultado da Conferencia', 'Descricao do Status'])

    resultados = RegistroConferencia.objects.all().order_by('status_conferencia')
    
    status_map = dict(RegistroConferencia.STATUS_CHOICES)

    for registro in resultados:
        writer.writerow([
            registro.codigo_item, 
            registro.lista_origem, 
            status_map.get(registro.status_conferencia, 'Status Desconhecido'),
            registro.get_status_conferencia_display()
        ])

    return response

# --- 6. VIEW PARA LISTAGEM E CONTEXTO ---
def listagem_resultados(request):
    somente_a = RegistroConferencia.objects.filter(status_conferencia='SOMENTE_A').order_by('codigo_item')
    somente_b = RegistroConferencia.objects.filter(status_conferencia='SOMENTE_B').order_by('codigo_item')
    presente_em_ambas = RegistroConferencia.objects.filter(status_conferencia='PRESENTE').order_by('codigo_item')
    
    status_upload = 'NENHUM_UPLOAD'
    if UploadConferencia.objects.exists():
          # Pega o status do upload mais recente (ou qualquer um, para o contexto)
          status_upload = UploadConferencia.objects.latest('data_upload').status 
    
    context = {
        'somente_a': somente_a,
        'somente_b': somente_b,
        'presente_em_ambas': presente_em_ambas,
        
        'count_a': somente_a.count(),
        'count_b': somente_b.count(),
        'count_ambas': presente_em_ambas.count(),
        'status_conferencia': status_upload,
    }
    
    return render(request, 'conferencia/listagem_resultados.html', context)