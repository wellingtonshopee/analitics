# core/views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# View protegida - só acessa se estiver logado
@login_required 
def dashboard(request):
    # Passamos o HUB do usuário para o template
    context = {
        'titulo': 'Dashboard Principal',
        'usuario_hub': request.user.hub.nome if request.user.hub else 'Não Vinculado',
        'usuario': request.user,
    }
    return render(request, 'core/dashboard.html', context)