# apresentacao/models.py
from django.db import models

class Apresentacao(models.Model):
    data_apresentacao = models.DateField(unique=True, verbose_name="Data da Apresentação")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação do Registro") # <--- CAMPO ADICIONADO
    
    class Meta:
        verbose_name = "Apresentação"
        ordering = ['-data_apresentacao']

    def __str__(self):
        return f"Painel de {self.data_apresentacao.strftime('%d/%m/%Y')}"

class Topico(models.Model):
    apresentacao = models.ForeignKey(
        Apresentacao, 
        on_delete=models.CASCADE, 
        related_name='topicos', 
        verbose_name="Apresentação"
    )
    titulo = models.CharField(max_length=100, verbose_name="Título do Tópico")
    ordem = models.IntegerField(default=1, verbose_name="Ordem de Exibição")
    
    class Meta:
        verbose_name = "Tópico"
        ordering = ['apresentacao', 'ordem']

    def __str__(self):
        return f"{self.apresentacao} - {self.titulo}"

class Card(models.Model):
    TIPO_CORES = [
        ('primary', 'Azul (Info)'),
        ('success', 'Verde (OK)'),
        ('danger', 'Vermelho (Crítico)'),
        ('warning', 'Amarelo (Alerta)'),
        ('info', 'Ciano (Detalhe)'),
        ('secondary', 'Cinza'),
    ]

    topico = models.ForeignKey(
        Topico, 
        on_delete=models.CASCADE, 
        related_name='cards', 
        verbose_name="Tópico"
    )
    titulo = models.CharField(max_length=100, verbose_name="Título do Card")
    valor = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, verbose_name="Valor Numérico Real")
    valor_formatado = models.CharField(max_length=50, verbose_name="Valor para Exibição (Ex: R$ 50k / 98.5%)")
    cor = models.CharField(max_length=10, choices=TIPO_CORES, default='primary', verbose_name="Cor de Destaque")
    ordem = models.IntegerField(default=1, verbose_name="Ordem de Exibição")

    class Meta:
        verbose_name = "Card/KPI"
        ordering = ['topico', 'ordem']
        unique_together = ('topico', 'ordem') 
        
    def __str__(self):
        return f"{self.topico.titulo} - {self.titulo}"