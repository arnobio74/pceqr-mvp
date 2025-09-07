# src/app.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import os
import google.generativeai as genai
import uuid
from datetime import datetime

# Carrega variáveis do .env
load_dotenv()

# Inicializa o app
app = Flask(__name__, static_folder='../public', static_url_path='')
CORS(app)

# Configuração do Gemini
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("Chave GOOGLE_API_KEY não encontrada no .env")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Armazenamento temporário em memória (funciona no Render)
traducoes_armazenadas = {}

def traduzir_com_gemini(texto_juridico):
    try:
        prompt_path = os.path.join(os.path.dirname(__file__), 'prompt-mestre.md')
        if not os.path.exists(prompt_path):
            return "ERRO: Arquivo prompt-mestre.md não encontrado."
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_mestre = f.read().strip()
        prompt_completo = f"{prompt_mestre}\n\nTexto Jurídico para Traduzir:\n{texto_juridico}"
        response = model.generate_content(prompt_completo)
        return response.text.strip()
    except Exception as e:
        print(f"❌ Erro na API do Gemini: {e}")
        return f"ERRO ao processar a tradução: {str(e)}"

@app.route('/traduzir', methods=['POST'])
def api_traduzir():
    data = request.get_json()
    
    # Validação completa
    if not data:
        return jsonify({"error": "Nenhum dado enviado."}), 400
    if 'texto' not in data:
        return jsonify({"error": "Campo 'texto' é obrigatório."}), 400
    if not data['texto'].strip():
        return jsonify({"error": "O texto não pode estar vazio."}), 400

    # Traduz
    texto_original = data['texto'].strip()
    texto_traduzido = traduzir_com_gemini(texto_original)

    # Gera token
    token = str(uuid.uuid4())[:8]
    qr_url = f"https://pce.boasnoticiasconsultoria.com.br/ver/{token}"

    # Armazena tradução (em memória)
    traducoes_armazenadas[token] = {
        "original": texto_original,
        "traduzido": texto_traduzido,
        "created_at": datetime.now()
    }

    return jsonify({
        "traduzido": texto_traduzido,
        "qr_url": qr_url,
        "token": token
    })

@app.route('/ver/<token>')
def ver_traducao(token):
    dados = traducoes_armazenadas.get(token)
    if not dados:
        return "<h1>Documento não encontrado ou expirado</h1>", 404

    # Limpa e formata o texto
    texto = dados['traduzido']
    texto = texto.replace('```markdown', '').replace('```', '').strip()
    import re
    texto = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', texto)
    texto = re.sub(r'\n', '<br>', texto)

    # HTML da página
    html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Leia e Ouça - Cidadão Entende</title>
    <style>
        body {{
            font-family: 'Arial', sans-serif;
            padding: 20px;
            max-width: 800px;
            margin: 0 auto;
            background: #f8f9fa;
            color: #333;
        }}
        h1 {{
            color: #002b5c;
        }}
        .documento-formatado {{
            background-color: #fff;
            border: 1px solid #ddd;
            padding: 25px;
            font-size: 18px;
            line-height: 1.8;
            text-align: justify;
            white-space: normal;
            word-wrap: break-word;
            margin-top: 15px;
            border-radius: 6px;
        }}
        .documento-formatado p {{
            text-indent: 30px;
            margin: 0 0 15px 0;
        }}
        button {{
            padding: 10px 20px;
            margin: 10px 5px;
            background: #0073e6;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
        }}
        button:hover {{
            background: #005bb5;
        }}
    </style>
</head>
<body>
    <h1>🗣️ Explicação em Linguagem Simples</h1>
    <div class="documento-formatado">{texto}</div>

    <button id="btn-voz">🔊 Ouvir Explicação em Voz Alta</button>
    <button id="btn-parar" style="background: #d9534f; display: none;">⏹️ Parar Leitura</button>

    <script>
        document.getElementById('btn-voz').addEventListener('click', () => {{
            const btn = document.getElementById('btn-voz');
            const texto = document.querySelector('.documento-formatado').innerText;
            if (!texto.trim()) return;

            if (btn.textContent === '⏸️ Pausar') {{
                speechSynthesis.pause();
                return;
            }}
            if (btn.textContent === '▶️ Retomar') {{
                speechSynthesis.resume();
                return;
            }}

            if (speechSynthesis.speaking) {{
                speechSynthesis.cancel();
            }}

            const utter = new SpeechSynthesisUtterance(texto);
            utter.lang = 'pt-BR';
            utter.rate = 0.9;
            utter.pitch = 1;

            utter.onstart = () => {{
                btn.textContent = '⏸️ Pausar';
                document.getElementById('btn-parar').style.display = 'inline-block';
            }};

            utter.onpause = () => {{
                btn.textContent = '▶️ Retomar';
            }};

            utter.onend = () => {{
                btn.textContent = '🔊 Ouvir Explicação em Voz Alta';
                document.getElementById('btn-parar').style.display = 'none';
            }};

            utter.onerror = () => {{
                alert('Erro ao tentar ler o texto.');
                btn.textContent = '🔊 Ouvir Explicação em Voz Alta';
                document.getElementById('btn-parar').style.display = 'none';
            }};

            speechSynthesis.speak(utter);
        }});

        document.getElementById('btn-parar').addEventListener('click', () => {{
            speechSynthesis.cancel();
            document.getElementById('btn-voz').textContent = '🔊 Ouvir Explicação em Voz Alta';
            document.getElementById('btn-parar').style.display = 'none';
        }});
    </script>
</body>
</html>
"""
    return html

@app.route('/')
def index():
    return send_from_directory('../public', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('../public', filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=False)