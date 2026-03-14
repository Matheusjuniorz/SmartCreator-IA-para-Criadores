import re
import os
import requests
import markdown
import PIL.Image
from datetime import date
from dotenv import load_dotenv
import random


# Django Core
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.safestring import mark_safe
from django.contrib import messages

# Autenticação e Models
from django.contrib.auth.models import User
from .models import HistoricoCanal, RoteiroIA, ConfiguracaoCanal, Perfil
from allauth.socialaccount.models import SocialToken, SocialApp

# Signals (Importante para o Perfil automático)
from django.db.models.signals import post_save
from django.dispatch import receiver

# Google APIs
from google import genai
from google.genai import types
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from .utils import chamar_ia

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options={'api_version': 'v1'}
)


@login_required
def multi_post_social(request):
    posts = {
        'instagram': '',
        'whatsapp': '',
        'facebook': ''
    }
    
    if request.method == "POST":
        titulo = request.POST.get("titulo")
        link = request.POST.get("link")
        
        prompt = f"""
        Com base no vídeo "{titulo}" ({link}), gere 3 postagens diferentes.
        Use EXATAMENTE este formato de separação:
        
        [INSTAGRAM]
        (texto aqui)
        
        [WHATSAPP]
        (texto aqui)
        
        [FACEBOOK]
        (texto aqui)
        """
        
        resposta_bruta = chamar_ia(prompt)
        
        if resposta_bruta:
            import re
            def extrair(tag, texto):
                pattern = rf"\[{tag}\](.*?)(?=\[|$)"
                match = re.search(pattern, texto, re.DOTALL)
                return match.group(1).strip() if match else ""

            posts['instagram'] = extrair("INSTAGRAM", resposta_bruta)
            posts['whatsapp'] = extrair("WHATSAPP", resposta_bruta)
            posts['facebook'] = extrair("FACEBOOK", resposta_bruta)

    return render(request, 'dashboard/multi_post.html', {'posts': posts})


def chamar_ia(prompt):
    try:
        available_models = [m.name for m in client.models.list()]
        tentar_modelos = [m for m in available_models if "flash" in m or "pro" in m]
        
        response = None
        modelo_que_funcionou = None

        for modelo_nome in tentar_modelos:
            try:
                print(f"DEBUG COMUNIDADE: Tentando {modelo_nome}...")
                response = client.models.generate_content(
                    model=modelo_nome, 
                    contents=prompt
                )
                modelo_que_funcionou = modelo_nome
                break  
            except Exception as inner_e:
                if "429" in str(inner_e) or "404" in str(inner_e):
                    print(f"DEBUG COMUNIDADE: {modelo_nome} indisponível, tentando próximo...")
                    continue 
                else:
                    raise inner_e

        if response and response.text:
            print(f"DEBUG COMUNIDADE: Sucesso com {modelo_que_funcionou}")
            return response.text.strip()
        
        return "⚠️ Cota esgotada em todos os modelos. Tente novamente em breve."

    except Exception as e:
        print(f"ERRO CRÍTICO COMUNIDADE: {e}")
        return f"Erro no servidor de IA: {str(e)}"

@login_required
def gerador_comunidade(request):
    post_gerado = None
    tema = ""

    if request.method == "POST":
        tema = request.POST.get("tema")
        tipo = request.POST.get("tipo")
        
        prompt = f"Gere um post para aba comunidade do YouTube sobre o tema: {tema}. Tipo de post: {tipo}."
        
        post_gerado = chamar_ia(prompt)

    return render(request, 'dashboard/comunidade.html', {
        'post_gerado': post_gerado,
        'tema': tema
    })
@login_required
def configuracoes_sistema(request):
    perfil = request.user.perfil  

    if request.method == "POST":
        perfil.tema = request.POST.get('tema')
        perfil.idioma_ia = request.POST.get('idioma')  
        perfil.tom_voz_ia = request.POST.get('tom_voz')
        
        perfil.save()
        messages.success(request, "Configurações aplicadas com sucesso!")
        return redirect('configuracoes_sistema')

    return render(request, 'templates/dashboard/comunidade.html', {'perfil': perfil})  
    

@login_required
def configuracoes_sistema(request):
    perfil, created = Perfil.objects.get_or_create(user=request.user)

    if request.method == "POST":
        perfil.tema = request.POST.get('tema')
        perfil.idioma_ia = request.POST.get('idioma')
        perfil.tom_voz_ia = request.POST.get('tom_voz')
        perfil.save()
        
        messages.success(request, "Configurações aplicadas com sucesso!")
        return redirect('configuracoes_sistema')

    return render(request, 'dashboard/configuracoes.html', {'perfil': perfil})

@receiver(post_save, sender=User)
def criar_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        Perfil.objects.create(user=instance)

@receiver(post_save, sender=User)
def salvar_perfil_usuario(sender, instance, **kwargs):
    instance.perfil.save()

@login_required
def perfil_usuario(request):
    perfil, created = Perfil.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        request.user.first_name = request.POST.get('nome')
        request.user.email = request.POST.get('email')
        request.user.save()
        
        perfil.telefone = request.POST.get('telefone')
        if request.FILES.get('foto'):
            perfil.foto = request.FILES.get('foto')
        perfil.save()
        
        messages.success(request, "Perfil atualizado com sucesso!")
        return redirect('perfil')

    return render(request, 'dashboard/perfil.html', {'perfil': perfil})

@login_required
def prever_tendencias_ia(request):
    if request.method == "POST":
        config = ConfiguracaoCanal.objects.filter(usuario=request.user).first()
        nicho = config.nicho if config and config.nicho else "Conteúdo Geral"
        
        prompt = f"""
        Analise o nicho {nicho} e forneça previsões reais para as próximas 48h. 
        Responda APENAS seguindo este formato rigoroso (seja breve e use emojis):

        [ESTRATEGIA] (1 frase de ação imediata)
        [VIDEO_LONGO] (Título magnético + foco principal)
        [SHORTS] (Gancho de 3s + trilha em alta)
        [COMUNIDADE] (Enquete polêmica ou post de engajamento)

        Foco em CTR alto e resposta sem introduções.
        """
        
        resposta = chamar_ia(prompt)
        
        if resposta:
            return JsonResponse({
                'status': 'success',
                'feedback': resposta  
        })
        
        return JsonResponse({'status': 'error', 'resultado': 'IA ocupada. Tente em instantes.'})
    
    
@login_required
def atualizar_configuracoes(request):
    if request.method == "POST":
        nicho = request.POST.get('nicho')
        config, created = ConfiguracaoCanal.objects.get_or_create(usuario=request.user)
        config.nicho = nicho
        config.save()
        return JsonResponse({'status': 'success'})


@login_required
def analisar_concorrente_ia(request):
    if request.method == "POST":
        titulo_rival = request.POST.get('titulo', '')
        from .models import ConfiguracaoCanal
        config, _ = ConfiguracaoCanal.objects.get_or_create(usuario=request.user)

        prompt = f"""
        Você é um analista de dados do YouTube. 
        Um concorrente do nicho {config.nicho} postou um vídeo com o título: "{titulo_rival}".
        
        Faça uma engenharia reversa ultra-direta:
        1. **Gatilho**: Qual emoção o título explora? (Curiosidade, Medo, Ganância?)
        2. **Ponto Forte**: O que faz alguém clicar nesse vídeo em vez de outros?
        3. **Como Superar**: Uma dica para o meu usuário fazer um vídeo melhor sobre o mesmo tema.
        
        Responda em 3 tópicos curtos.
        """

        try:
            available_models = [m.name for m in client.models.list()]
            tentar_modelos = [m for m in available_models if "flash" in m or "pro" in m]
            
            response = None
            for modelo_nome in tentar_modelos:
                try:
                    response = client.models.generate_content(model=modelo_nome, contents=prompt)
                    break
                except Exception as e:
                    if "429" in str(e): continue
                    else: raise e

            if response:
                return JsonResponse({'feedback': response.text.strip()})
            return JsonResponse({'feedback': 'Cota esgotada.'}, status=429)
        except Exception as e:
            return JsonResponse({'feedback': f"Erro: {str(e)}"}, status=500)


@login_required
def analisar_thumb_ia(request):
    if request.method == "POST":
        img_file = request.FILES.get('imagem')
        
        if not img_file:
            return JsonResponse({'feedback': 'Nenhuma imagem selecionada.'}, status=400)

        img = PIL.Image.open(img_file)

        from .models import ConfiguracaoCanal
        config, _ = ConfiguracaoCanal.objects.get_or_create(usuario=request.user)

        prompt = f"""
        Analise esta Thumbnail para o nicho de {config.nicho} de forma ultra-direta.
        Use exatamente este formato de resposta:

        🎨 **Design**: (1 frase sobre cores/contraste)
        ✍️ **Texto**: (1 frase sobre legibilidade)
        💡 **Sugestão**: (A mudança principal para gerar mais cliques)
        ⭐ **Nota**: (0/10)
        """

        try:
            available_models = [m.name for m in client.models.list()]
            tentar_modelos = [m for m in available_models if "flash" in m or "pro" in m]
            
            response = None
            modelo_que_funcionou = None

            for modelo_nome in tentar_modelos:
                try:
                    print(f"DEBUG THUMB: Tentando {modelo_nome}...")
                    response = client.models.generate_content(
                        model=modelo_nome, 
                        contents=[prompt, img] 
                    )
                    modelo_que_funcionou = modelo_nome
                    break
                except Exception as inner_e:
                    if "429" in str(inner_e):
                        continue 
                    else:
                        raise inner_e

            if response and response.text:
                return JsonResponse({'feedback': response.text.strip()})
            else:
                return JsonResponse({'feedback': 'Cota esgotada. Tente em instantes.'}, status=429)

        except Exception as e:
            print(f"ERRO CRÍTICO THUMB: {e}")
            return JsonResponse({'feedback': f"Erro no processamento visual: {str(e)}"}, status=500)

    return JsonResponse({'error': 'Método inválido'}, status=405)


@login_required
def analisar_video_ia(request):
    if request.method == "POST":
        titulo = request.POST.get('titulo', '')
        ctr = request.POST.get('ctr', 'Não informado')
        
        from .models import ConfiguracaoCanal
        config, _ = ConfiguracaoCanal.objects.get_or_create(usuario=request.user)

        prompt = f"""
        Analise o vídeo para o nicho {config.nicho} de forma ultra-direta:
        Título: "{titulo}" | CTR: {ctr}%

    Use este formato:
    📢 **Título**: (Crítica em 1 frase)
    🚀 **Sugestão**: (Novo título curto e chamativo)
    ✅ **Veredito**: (Mantenha ou Mude)
    """

        try:
            available_models = [m.name for m in client.models.list()]
            tentar_modelos = [m for m in available_models if "flash" in m or "pro" in m]
            
            response = None
            modelo_que_funcionou = None

            for modelo_nome in tentar_modelos:
                try:
                    print(f"DEBUG ANALISADOR: Tentando {modelo_nome}...")
                    response = client.models.generate_content(
                        model=modelo_nome, 
                        contents=prompt
                    )
                    modelo_que_funcionou = modelo_nome
                    break  
                except Exception as inner_e:
                    if "429" in str(inner_e):
                        print(f"DEBUG ANALISADOR: {modelo_nome} sem cota, tentando próximo...")
                        continue 
                    else:
                        raise inner_e

            if response and response.text:
                print(f"DEBUG ANALISADOR: Sucesso com {modelo_que_funcionou}")
                return JsonResponse({'feedback': response.text.strip()})
            else:
                return JsonResponse({'feedback': 'Cota esgotada no Gemini. Tente mais tarde.'}, status=429)

        except Exception as e:
            print(f"ERRO CRÍTICO ANALISADOR: {e}")
            return JsonResponse({'feedback': f"Erro no servidor: {str(e)}"}, status=500)

    return JsonResponse({'error': 'Método inválido'}, status=405)


@login_required
def salvar_estrategia(request):
    if request.method == "POST":
        nicho = request.POST.get('nicho')
        try:
            vids_dia = int(request.POST.get('vids_dia', 1))
        except:
            vids_dia = 1
            
        vids_dia = max(1, min(vids_dia, 12)) 

        janelas = {
            'Games': (13, 23),      
            'Tecnologia': (9, 19), 
            'Educação': (8, 20),   
            'Entretenimento': (11, 22)
        }
        inicio, fim = janelas.get(nicho, (10, 22))


        tempo_total = fim - inicio
        intervalo = tempo_total / vids_dia
        
        horas_calculadas = []
        for i in range(vids_dia):
            hora_base = inicio + (i * intervalo)
            minuto_variado = random.choice([0, 15, 30, 45])
            
            h_inteira = int(hora_base)
            horas_calculadas.append(f"{h_inteira:02d}:{minuto_variado:02d}")

        if len(horas_calculadas) > 3:
            string_horarios = f"{horas_calculadas[0]} até {horas_calculadas[-1]} ({vids_dia} posts)"
        else:
            string_horarios = " • ".join(horas_calculadas)

        dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
        dia_pico = random.choice(dias)

        ConfiguracaoCanal.objects.update_or_create(
            usuario=request.user,
            defaults={
                'nicho': nicho,
                'vids_dia': vids_dia,
                'melhor_horario': string_horarios,
                'dia_pico': dia_pico,
            }
        )

        return JsonResponse({'status': 'ok', 'horario': string_horarios})


@login_required
def publicar_resposta_youtube(request):
    if request.method == "POST":
        comentario_id = request.POST.get('comentario_id')
        texto_resposta = request.POST.get('texto_resposta')
        
        token_obj = SocialToken.objects.filter(account__user=request.user, account__provider='google').first()
        
        try:
            youtube = build('youtube', 'v3', credentials=creds)
            youtube.comments().insert(
                part="snippet",
                body={
                    "snippet": {
                        "parentId": comentario_id,
                        "textOriginal": texto_resposta
                    }
                }
            ).execute()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@login_required
def sugerir_resposta_ia(request):
    if request.method == "POST":
        texto = request.POST.get('texto', '')
        autor = request.POST.get('autor', 'Seguidor')
        sentimento = request.POST.get('sentimento', 'Neutro')

        prompt = f"Responda como um YouTuber amigável ao comentário de {autor}: '{texto}'. O sentimento é {sentimento}. Seja breve (1 a 2 frases)."

        try:
            available_models = [m.name for m in client.models.list()]
            
            tentar_modelos = [m for m in available_models if "flash" in m or "pro" in m]
            
            response = None
            modelo_que_funcionou = None

            for modelo_nome in tentar_modelos:
                try:
                    print(f"DEBUG: Tentando {modelo_nome}...")
                    response = client.models.generate_content(
                        model=modelo_nome, 
                        contents=prompt
                    )
                    modelo_que_funcionou = modelo_nome
                    break  
                except Exception as inner_e:
                    if "429" in str(inner_e):
                        print(f"DEBUG: {modelo_nome} esgotado, tentando o próximo da lista...")
                        continue 
                    else:
                        raise inner_e 
            if response and response.text:
                print(f"DEBUG: Sucesso com o modelo {modelo_que_funcionou}")
                return JsonResponse({'sugestao': response.text.strip()})
            else:
                return JsonResponse({'error': 'Cota esgotada em todos os modelos Gemini.'}, status=429)

        except Exception as e:
            print(f"ERRO CRÍTICO: {e}")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Método inválido'}, status=405)


@login_required
def dashboard_home(request):
    config, created = ConfiguracaoCanal.objects.get_or_create(usuario=request.user)
    roteiros_salvos = RoteiroIA.objects.filter(usuario=request.user).order_by('-data_criacao')
    
    dados_yt = {
        'inscritos': 0, 
        'visualizacoes': 0, 
        'videos': 0, 
        'progresso_meta': 0,
        'horas_vistas': 0,
        'nome_canal': config.usuario.username, 
        'foto_perfil': '',
        'canal_conectado': False,
        'ultimos_comentarios': [],
        'membros': []  
    }

    try:
        token_obj = SocialToken.objects.filter(account__user=request.user, account__provider='google').first()
        app = SocialApp.objects.get(provider='google') 

        if token_obj:
            creds = Credentials(
                token=token_obj.token,
                refresh_token=token_obj.token_secret,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=app.client_id,
                client_secret=app.secret
            )
            
            youtube = build('youtube', 'v3', credentials=creds)
            
            request_stats = youtube.channels().list(part='statistics,snippet', mine=True)
            response = request_stats.execute()

            if response.get('items'):
                item = response['items'][0]
                canal_id = item['id']
                stats = item['statistics']
                snippet = item['snippet']
                
                inscritos_reais = int(stats.get('subscriberCount', 0))
                visualizacoes_reais = int(stats.get('viewCount', 0))
                
                membros_temp = []
                try:
                    membros_request = youtube.members().list(part="snippet").execute()
                    for m_item in membros_request.get('items', []):
                        m_snippet = m_item['snippet']['memberDetails']
                        membros_temp.append({
                            'nome': m_snippet['displayName'],
                            'foto': m_snippet['profileImageUrl'],
                            'nivel': m_item['snippet']['membershipDetails']['membershipsDurationAtLevel'][0]['levelName'],
                            'data_adesao': m_item['snippet']['membershipDetails']['memberSince']
                        })
                except Exception as e_memb:
                    print(f"ℹ️ Membros indisponíveis: {e_memb}")

                horas_reais = 0
                try:
                    analytics = build('youtubeAnalytics', 'v2', credentials=creds)
                    hoje_str = date.today().strftime('%Y-%m-%d')
                    analytics_res = analytics.reports().query(
                        ids='channel==MINE',
                        startDate='2005-01-01',
                        endDate=hoje_str,
                        metrics='estimatedMinutesWatched'
                    ).execute()

                    total_minutos = analytics_res['rows'][0][0] if 'rows' in analytics_res else 0
                    horas_reais = int(total_minutos / 60)
                except Exception as e_an:
                    print(f"⚠️ Erro Analytics: {e_an}")

                comentarios_temp = []
                try:
                    com_request = youtube.commentThreads().list(
                        part="snippet",
                        allThreadsRelatedToChannelId=canal_id,
                        maxResults=5
                    ).execute()

                    for c_item in com_request.get('items', []):
                        top_comment = c_item['snippet']['topLevelComment']['snippet']
                        texto = top_comment['textDisplay']
                        comentarios_temp.append({
                            'id': c_item['id'],
                            'autor': top_comment['authorDisplayName'],
                            'foto': top_comment['authorProfileImageUrl'],
                            'texto': texto,
                            'sentimento': analisar_sentimento(texto), 
                            'link': f"https://www.youtube.com/watch?v={top_comment['videoId']}&lc={c_item['id']}"
                        })
                except:
                    pass

                dados_yt.update({
                    'inscritos': inscritos_reais,
                    'visualizacoes': visualizacoes_reais,
                    'videos': stats.get('videoCount', "0"),
                    'progresso_meta': min((( (inscritos_reais/1000)*100 + (horas_reais/4000)*100 ) / 2), 100),
                    'horas_vistas': horas_reais,
                    'nome_canal': snippet.get('title'), 
                    'foto_perfil': snippet.get('thumbnails', {}).get('default', {}).get('url'),
                    'canal_conectado': True,
                    'ultimos_comentarios': comentarios_temp,
                    'membros': membros_temp
                })

                HistoricoCanal.objects.update_or_create(
                    usuario=request.user,
                    data=date.today(),
                    defaults={'inscritos': inscritos_reais, 'visualizacoes': visualizacoes_reais}
                )

    except Exception as e:
        print(f"❌ ERRO GERAL API: {e}")

    historico_db = HistoricoCanal.objects.filter(usuario=request.user).order_by('-data')[:7]
    historico_lista = list(historico_db)[::-1] 
    
    labels_grafico = [h.data.strftime('%d/%m') for h in historico_lista]
    dados_grafico = [h.visualizacoes for h in historico_lista]

    context = {
        'configuracao': config,
        'roteiros': roteiros_salvos,
        'labels_grafico': labels_grafico,
        'dados_grafico': dados_grafico,
        **dados_yt 
    }

    return render(request, 'dashboard/dashboard.html', context)

def analisar_sentimento(texto):
    if not texto:
        return 'Neutro'
    texto = texto.lower()
    positivas = ['amei', 'top', 'bom', 'otimo', 'parabens', 'legal', 'show', 'ajudou', 'obrigado', 'vlw', 'excelente']
    negativas = ['ruim', 'bosta', 'pessimo', 'merda', 'odiei', 'errado', 'fake', 'deslike', 'horrivel']
    
    if any(word in texto for word in positivas):
        return 'Positivo'
    elif any(word in texto for word in negativas):
        return 'Negativo'
    return 'Neutro'

@login_required
def cortes_virais(request):
    roteiros_com_cortes = RoteiroIA.objects.filter(
        usuario=request.user
    ).exclude(cortes_gerados__isnull=True).exclude(cortes_gerados="").order_by('-data_criacao')
    
    return render(request, 'dashboard/cortes_virais.html', {
        'roteiros': roteiros_com_cortes
    })


@login_required
def excluir_roteiro(request, id):
    if request.method == "POST":
        roteiro = RoteiroIA.objects.filter(id=id, usuario=request.user).first()
        
        if roteiro:
            roteiro.delete()
            
    return redirect('dashboard_home')


@login_required
def atualizar_status_roteiro(request, id):
    if request.method == "POST":
        roteiro = get_object_or_404(RoteiroIA, id=id, usuario=request.user)
        novo_status = request.POST.get('status')
        roteiro.status = novo_status
        roteiro.save()
        return JsonResponse({'status': 'sucesso'})


@login_required
def salvar_edicao_cortes(request, id):
    if request.method == "POST":
        roteiro = get_object_or_404(RoteiroIA, id=id, usuario=request.user)
        novo_conteudo = request.POST.get('conteudo')
        
        if not roteiro.cortes_original:
            roteiro.cortes_original = roteiro.cortes_gerados
            
        roteiro.cortes_gerados = novo_conteudo
        roteiro.save()
        return JsonResponse({'status': 'sucesso'})


@login_required
def checklist_gravacao(request, id):
    roteiro = get_object_or_404(RoteiroIA, id=id, usuario=request.user)
    
    payload = {
    "contents": [{"parts": [{"text": f"Baseado neste roteiro: {roteiro_pai.conteudo_gerado}. Primeiro, gere os 3 shorts virais. Depois, crie uma seção final chamada 'CHECKLIST DE GRAVAÇÃO' com os equipamentos e cenas necessárias."}]}]
}
    

    
    return render(request, 'dashboard/checklist.html', {'roteiro': roteiro})

@login_required
def gerar_cortes_shorts(request, id):
    roteiro_pai = get_object_or_404(RoteiroIA, id=id, usuario=request.user)
    chave = os.getenv("GEMINI_API_KEY")
    
    try:
        url_lista = f"https://generativelanguage.googleapis.com/v1beta/models?key={chave}"
        res_lista = requests.get(url_lista)
        
        modelo_escolhido = None
        if res_lista.status_code == 200:
            modelos = res_lista.json().get('models', [])
            for m in modelos:
                if "generateContent" in m.get('supportedGenerationMethods', []):
                    nome_modelo = m['name'] 
                    if "1.5-flash" in nome_modelo:
                        modelo_escolhido = nome_modelo
                        break
            
            if not modelo_escolhido and modelos:
                modelo_escolhido = modelos[0]['name']

        if not modelo_escolhido:
            return render(request, 'dashboard/cortes_shorts.html', {'cortes_html': "Nenhum modelo disponível para sua chave."})

        url_api = f"https://generativelanguage.googleapis.com/v1beta/{modelo_escolhido}:generateContent?key={chave}"
        
        payload = {
            "contents": [{"parts": [{"text": f"Gere 3 shorts baseados nisso: {roteiro_pai.conteudo_gerado}"}]}]
        }

        response = requests.post(url_api, json=payload, timeout=30)
        data = response.json()

        if response.status_code == 200:
            texto_puro = data['candidates'][0]['content']['parts'][0]['text']
            
            roteiro_pai.cortes_gerados = texto_puro
            roteiro_pai.save()

            conteudo_html = mark_safe(markdown.markdown(texto_puro))
        else:
            conteudo_html = mark_safe(f"<div class='alert alert-danger'>Erro {response.status_code}: {data.get('error', {}).get('message')}</div>")

    except Exception as e:
        conteudo_html = mark_safe(f"<div class='alert alert-danger'>Erro crítico: {str(e)}</div>")

    return render(request, 'dashboard/cortes_shorts.html', {
        'roteiro_pai': roteiro_pai,
        'cortes_html': conteudo_html
    })
    
    
@login_required
def historico_roteiros(request):
    roteiros = RoteiroIA.objects.filter(usuario=request.user).order_by('-data_criacao')
    return render(request, 'dashboard/historico.html', {'roteiros': roteiros})


@login_required
def detalhe_roteiro(request, id):
    roteiro_obj = get_object_or_404(RoteiroIA, id=id, usuario=request.user)
    
    conteudo_html = mark_safe(markdown.markdown(roteiro_obj.conteudo_gerado))
    
    return render(request, 'dashboard/detalhe_roteiro.html', {
        'roteiro_obj': roteiro_obj,
        'conteudo_html': conteudo_html
    })


@login_required
def gerador_ia(request):
    roteiro = ""
    if request.method == "POST":
        tema = request.POST.get("tema")
        formato = request.POST.get("formato") 
        chave = os.getenv("GEMINI_API_KEY")
        
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={chave}"
        
        if formato == "shorts":
            instrucao = f"Crie um roteiro VIRAL e DINÂMICO de até 60 segundos para YouTube Shorts sobre: {tema}."
        else:
            instrucao = f"Crie um roteiro DETALHADO e estruturado para um vídeo longo de YouTube sobre: {tema}."

        prompt_final = f"""
        {instrucao}
        
        ...
        Ao final, adicione estas seções EXATAMENTE com estes nomes para o sistema identificar:
        [TITULOS] (Liste 3 opções)
        [DESCRICAO] (Texto da descrição)
        [TAGS] (Apenas as tags separadas por vírgula)
        """

        payload = {
            "contents": [{"parts": [{"text": prompt_final}]}]
        }

        try:
            response = requests.post(url, json=payload)
            data = response.json()
            if response.status_code == 200:
                texto_puro = data['candidates'][0]['content']['parts'][0]['text']
                roteiro = mark_safe(markdown.markdown(texto_puro))
                
                from .models import RoteiroIA
                RoteiroIA.objects.create(
                    usuario=request.user,
                    tema=tema,
                    tipo=formato, 
                    conteudo_gerado=texto_puro
                )
            else:
                roteiro = "Erro na API do Google."
        except Exception as e:
            roteiro = f"Erro técnico: {e}"

    return render(request, 'dashboard/gerador_ia.html', {'roteiro': roteiro})

def index(request):
    if request.user.is_authenticated:
        return redirect('dashboard_home') 
    return render(request, 'dashboard/index.html')

def welcome(request):
    return render(request, 'dashboard/welcome.html')


@login_required
def ferramentas(request):
    return render(request, 'dashboard/ferramentas.html')