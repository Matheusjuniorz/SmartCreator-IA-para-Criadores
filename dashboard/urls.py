from django.urls import path
from . import views
from .views import publicar_resposta_youtube
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Perfil 



urlpatterns = [
    path('', views.index, name='index'), 
    path('welcome/', views.welcome, name='welcome'),
    path('dashboard/', views.dashboard_home, name='dashboard_home'), 
    path('connect-youtube/', views.index, name='youtube_connect'), 
    path('gerador-ia/', views.gerador_ia, name='gerador_ia'),
    path('ferramentas/', views.ferramentas, name='ferramentas'),
    path('historico/', views.historico_roteiros, name='historico_roteiros'),
    path('roteiro/<int:id>/', views.detalhe_roteiro, name='detalhe_roteiro'),
    path('roteiro/<int:id>/cortes/', views.gerar_cortes_shorts, name='gerar_shorts'),
    path('salvar-edicao-cortes/<int:id>/', views.salvar_edicao_cortes, name='salvar_edicao_cortes'),
    path('roteiro/<int:id>/cortes/', views.gerar_cortes_shorts, name='cortes_shorts'),    
    path('roteiro/<int:id>/status/', views.atualizar_status_roteiro, name='atualizar_status_roteiro'),
    path('roteiro/<int:id>/excluir/', views.excluir_roteiro, name='excluir_roteiro'),
    path('cortes-virais/', views.cortes_virais, name='cortes_virais'),
    path('sugerir-resposta-ia/', views.sugerir_resposta_ia, name='sugerir_resposta_ia'),
    path('publicar-resposta-youtube/', publicar_resposta_youtube, name='publicar_resposta_youtube'),
    path('salvar-estrategia/', views.salvar_estrategia, name='salvar_estrategia'),
    path('analisar-video-ia/', views.analisar_video_ia, name='analisar_video_ia'),
    path('analisar-thumb-ia/', views.analisar_thumb_ia, name='analisar_thumb_ia'),
    path('analisar-concorrente-ia/', views.analisar_concorrente_ia, name='analisar_concorrente_ia'),
    path('prever-tendencias-ia/', views.prever_tendencias_ia, name='prever_tendencias_ia'),
    path('perfil/', views.perfil_usuario, name='perfil'),
    path('configuracoes-sistema/', views.configuracoes_sistema, name='configuracoes_sistema'),
    path('ferramentas/comunidade/', views.gerador_comunidade, name='gerador_comunidade'),
    path('ferramentas/multi-post/', views.multi_post_social, name='multi_post_social'),
]
