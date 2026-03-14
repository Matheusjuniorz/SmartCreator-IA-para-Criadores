import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

def chamar_ia(prompt):
    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash", 
            contents=prompt
        )
        return response.text
    except Exception as e:
        if "404" in str(e):
            return f"Erro 404: O modelo não foi encontrado nesta conta. Detalhes: {e}"
        
        if "429" in str(e):
            return "⚠️ Cota esgotada. Aguarde 60 segundos antes de tentar novamente."
            
        return f"Erro na IA: {str(e)}"

    for modelo in modelos:
        try:
            print(f"DEBUG COMUNIDADE: Tentando {modelo}...")
            
            response = client.models.generate_content(
                model=modelo,
                contents=prompt
            )
            
            if response.text:
                print(f"DEBUG COMUNIDADE: Sucesso com {modelo}")
                return response.text
                
        except Exception as e:
            print(f"DEBUG COMUNIDADE: Erro com {modelo}: {str(e)}")
            if "429" in str(e) or "404" in str(e):
                continue
            else:
                return f"Erro na IA: {str(e)}"

    return "⚠️ Cota esgotada em todos os modelos. Tente novamente em 1 minuto."