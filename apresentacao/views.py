# apresentacao/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Apresentacao, Topico
from .forms import ApresentacaoForm, TopicoFormSet, CardFormSet # Importa os Formsets

@login_required
def selecionar_apresentacao(request):
    """Exibe as apresentações existentes e permite criar uma nova por data."""
    
    apresentacoes_recentes = Apresentacao.objects.all()[:10]
    
    if request.method == 'POST':
        form = ApresentacaoForm(request.POST)
        if form.is_valid():
            apresentacao = form.save()
            # Redireciona para a página de EDIÇÃO após a criação
            return redirect('apresentacao:editar_apresentacao', pk=apresentacao.pk) 
    else:
        form = ApresentacaoForm()
        
    context = {
        'titulo': 'Selecionar/Criar Apresentação',
        'apresentacoes': apresentacoes_recentes,
        'form': form,
    }
    return render(request, 'apresentacao/selecionar_apresentacao.html', context)

@login_required
def detalhe_apresentacao(request, pk):
    """Exibe o painel de apresentação (Power BI Style)."""
    apresentacao = get_object_or_404(Apresentacao, pk=pk)
    
    # Busca os tópicos e, por meio do 'related_name', os cards de cada um
    topicos = apresentacao.topicos.prefetch_related('cards').all()
    
    context = {
        'titulo': f'Painel: {apresentacao.data_apresentacao.strftime("%d/%m/%Y")}',
        'apresentacao': apresentacao,
        'topicos': topicos,
    }
    return render(request, 'apresentacao/detalhe_apresentacao.html', context)


@login_required
def editar_apresentacao(request, pk):
    """
    Página de edição customizada (Frontend) para Tópicos e Cards
    usando Inline Formsets aninhados.
    """
    apresentacao = get_object_or_404(Apresentacao, pk=pk)
    
    # 1. Cria o Formset de Tópicos (Pai)
    topico_formset = TopicoFormSet(request.POST or None, instance=apresentacao, prefix='topico')
    
    card_formsets = []
    has_error = False

    if request.method == 'POST':
        if topico_formset.is_valid():
            
            # Processa Tópicos (salva com commit=False para ter as instâncias)
            topico_instances = topico_formset.save(commit=False)
            
            # 2. Loop para processar e validar os Formsets de Cards (Filho)
            for i, topico_form in enumerate(topico_formset):
                
                # Apenas processa se for um formulário válido e não marcado para exclusão
                if topico_form.is_valid() and not topico_form.cleaned_data.get('DELETE'):
                    
                    # Salva o tópico temporariamente para obter uma instância (PK) se for novo
                    topico_instance = topico_form.save() 
                    
                    # Recria o CardFormSet para o tópico atual
                    # Usa o PK do tópico (ou o índice 'i' se for um formulário extra novo) como parte do prefixo
                    prefix_key = topico_instance.pk if topico_instance.pk else i
                    current_card_formset = CardFormSet(
                        request.POST, 
                        instance=topico_instance, 
                        prefix=f'card-{prefix_key}'
                    )
                    card_formsets.append(current_card_formset)
                    
                    if current_card_formset.is_valid():
                        # Salva Cards, atribuindo a instância do Tópico
                        for card_form in current_card_formset.save(commit=False):
                            card_form.topico = topico_instance
                            card_form.save()
                        current_card_formset.save_m2m()
                        
                        # Processa exclusões
                        for obj in current_card_formset.deleted_objects:
                            obj.delete()

                    else:
                        # Se houver erro, setar a flag de erro e interromper
                        has_error = True
                        break 
                elif topico_form.cleaned_data.get('DELETE'):
                    # Tópico marcado para exclusão (será excluído abaixo)
                    continue


            # 3. Salva ou Deleta Tópicos (apenas se não houver erro nos Cards)
            if not has_error:
                topico_formset.save() # Salva tópicos novos/editados e deleta os marcados
                return redirect('apresentacao:detalhe_apresentacao', pk=apresentacao.pk)
            # Se houver erro, o código continua para a renderização com erros

    # 4. GET ou POST com erro: Configura Formsets para renderizar
    else:
        # Para GET, ou se houve erro no POST, preenche a lista de CardFormSets
        for topico in apresentacao.topicos.all():
            card_formsets.append(
                CardFormSet(instance=topico, prefix=f'card-{topico.pk}')
            )
            
    # O formulário vazio de Card para o template vazio de Tópico (para o JavaScript clonar)
    empty_card_formset_instance = CardFormSet(instance=Topico(), prefix='card-__prefix__')

    context = {
        'titulo': f'Editar Painel: {apresentacao.data_apresentacao.strftime("%d/%m/%Y")}',
        'apresentacao': apresentacao,
        'topico_formset': topico_formset,
        'card_formsets': card_formsets,
        # O formulário de card vazio para o JavaScript
        'empty_card_form': empty_card_formset_instance.empty_form, 
    }
    return render(request, 'apresentacao/editar_apresentacao.html', context)