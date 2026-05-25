import os
import requests
import json
from pypdf import PdfReader

def extract_text_from_pdf(pdf_path, max_chars=40000):
    """
    Extracts plain text from the given PDF file up to max_chars.
    """
    if not os.path.exists(pdf_path):
        return f"Erro: Arquivo PDF não encontrado em {pdf_path}"
        
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page_idx, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
            # Hard limit to avoid exceeding model context limits and token costs
            if len(text) > max_chars:
                text = text[:max_chars] + "\n...[Texto truncado para respeitar os limites de contexto]..."
                break
        return text.strip() or "Aviso: O PDF foi lido mas não continha texto extraível (pode ser baseado em imagens/escaneado)."
    except Exception as e:
        return f"Erro ao extrair texto do PDF: {e}"

def sanitize_prompt(prompt):
    """
    Verifies if the prompt includes the fallback phrase:
    'Se não encontrar nada parecido, retorne: Não encontrei nada parecido'
    Appends it if it's missing, maintaining clean formatting.
    """
    required_phrase = "Se não encontrar nada parecido, retorne: Não encontrei nada parecido"
    
    # Normalize strings for comparison (lowercase, alphanumeric characters only)
    def clean_str(s):
        return "".join(c for c in s.lower() if c.isalnum())
        
    normalized_prompt = clean_str(prompt)
    normalized_phrase = clean_str(required_phrase)
    
    if normalized_phrase not in normalized_prompt:
        prompt_stripped = prompt.strip()
        if not prompt_stripped:
            return required_phrase
        elif prompt_stripped[-1] in [".", "!", "?"]:
            return f"{prompt_stripped} {required_phrase}."
        else:
            return f"{prompt_stripped}. {required_phrase}."
            
    return prompt

def analyze_document(api_config, prompt, document_text, metadata=None):
    """
    Sends a request to the custom OpenAI-compatible API.
    
    :param api_config: Dict containing 'base_url', 'api_key', and 'model'.
    :param prompt: The sanitized instruction prompt.
    :param document_text: The paper content.
    :param metadata: Dict containing 'title', 'year', 'authors'.
    """
    base_url = api_config.get("base_url", "https://api.openai.com/v1").strip()
    api_key = api_config.get("api_key", "").strip()
    model = api_config.get("model", "gpt-4o-mini").strip()
    
    # Construct complete URL
    url = f"{base_url.rstrip('/')}/chat/completions"
    
    # Construct prompt messages
    title = metadata.get("title", "Título Desconhecido") if metadata else "Documento"
    year = metadata.get("year", "Ano Desconhecido") if metadata else "N/A"
    authors = metadata.get("authors", "Autores Desconhecidos") if metadata else "N/A"
    
    user_content = (
        f"Artigo Científico:\n"
        f"Título: {title}\n"
        f"Ano: {year}\n"
        f"Autores: {authors}\n"
        f"-------------------\n"
        f"Conteúdo:\n"
        f"{document_text}"
    )
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.2
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        res_data = response.json()
        
        # Extract reply text
        choices = res_data.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")
            return True, content.strip()
        else:
            return False, f"Resposta inválida da API: {json.dumps(res_data)}"
    except requests.exceptions.HTTPError as he:
        # Try to parse error details from response body
        try:
            err_details = he.response.json().get("error", {}).get("message", str(he))
        except Exception:
            err_details = str(he)
        return False, f"Erro HTTP {he.response.status_code}: {err_details}"
    except Exception as e:
        return False, f"Erro na chamada da API: {e}"
