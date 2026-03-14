from django.db import models
from django.contrib.auth.models import User


class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    foto = models.ImageField(upload_to='perfis/', null=True, blank=True, default='perfis/default.png')
    telefone = models.CharField(max_length=20, null=True, blank=True)
    nome_exibicao = models.CharField(max_length=100, null=True, blank=True)
    tema = models.CharField(max_length=20, default='dark')
    idioma_ia = models.CharField(max_length=10, default='pt')
    tom_voz_ia = models.CharField(max_length=30, default='casual')
    

    def __str__(self):
        return f"Perfil de {self.user.username}"
    
class RoteiroIA(models.Model):
    TIPOS = [('longo', 'Vídeo Longo'), ('shorts', 'Shorts')]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    tema = models.CharField(max_length=200)
    tipo = models.CharField(max_length=10, choices=TIPOS)
    conteudo_gerado = models.TextField()
    data_criacao = models.DateTimeField(auto_now_add=True)
    cortes_gerados = models.TextField(blank=True, null=True) 
    data_criacao = models.DateTimeField(auto_now_add=True)
    cortes_original = models.TextField(blank=True, null=True)
    
    STATUS_CHOICES = [
        ('pendente', 'Pendente ⚪'),
        ('gravando', 'Gravando 🎥'),
        ('editando', 'Editando ✂️'),
        ('postado', 'Postado ✅'),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')

    def __str__(self):
        return f"{self.tema} - {self.usuario.username}"
    
    
class HistoricoCanal(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    data = models.DateField(auto_now_add=True)
    inscritos = models.IntegerField()
    visualizacoes = models.BigIntegerField()

    class Meta:
        unique_together = ('usuario', 'data') 
        ordering = ['data']

    def __str__(self):
        return f"{self.data} - {self.usuario.username}: {self.inscritos} subs"
    

class ConfiguracaoCanal(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    nicho = models.CharField(max_length=50, default="Tecnologia")
    vids_dia = models.IntegerField(default=1)
    vids_semana = models.IntegerField(default=7)
    melhor_horario = models.CharField(max_length=100, default="19:00")
    dia_pico = models.CharField(max_length=20, default="Terça-feira")

    def __str__(self):
        return f"Config: {self.usuario.username} - {self.nicho}"