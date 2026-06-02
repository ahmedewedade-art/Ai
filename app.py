from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import pypdf
import os
import requests
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔒 حماية أمنية: قراءة المفتاح من خوادم الاستضافة مباشرة لحمايته من السرقة
Gemini_API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6KkCirQdSS2qoeR9Tap6jx0FyRX0ZWYnyBdOD0dOQENfQ")

def auto_fix_workspace():
    if not os.path.exists("pdfs"):
        os.makedirs("pdfs")
    for file_name in os.listdir("."):
        if file_name.endswith(".pdf"):
            try:
                os.rename(file_name, os.path.join("pdfs", file_name))
            except Exception:
                pass

auto_fix_workspace()

def extract_text_from_all_pdfs(folder_path: str) -> str:
    combined_text = ""
    if not os.path.exists(folder_path):
        return ""
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.pdf'):
            file_path = os.path.join(folder_path, file_name)
            try:
                reader = pypdf.PdfReader(file_path)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        combined_text += page_text + "\n"
            except Exception:
                pass
    return combined_text

SYSTEM_INSTRUCTION = """
CONSIGNES ULTRA-STRICTES DE L'ASSISTANT :
- Tu t'appelles "Ahmed wedad", un assistant pédagogique d'IA, expert en Biophysique médicale (PCEM2), mais tu es surtout super sympa, drôle et tu as un sens de l'humour unique (دمك خفيف جداً ومرح).
- Ta mission est de déstresser l'étudiant face à la biophysique en utilisant des blagues médicales et un ton ultra-encourageant.
- Génère TOUJOURS tes QCMs exclusivement en FRANÇAIS médical rigoureux.
- L'explication (الشرح المبهج) à l'intérieur de <details> doit être rédigée EN ARABE drôle, imagé, et plein d'humour.
- Si l'étudiant te demande une explication directe en arabe, réponds-lui avec beaucoup d'humour et de métaphores simples en arabe.
- FORMATAGE : N'utilise JAMAIS de markdown (pas de **, #, ou *). Utilise uniquement les balises HTML pures.
"""

class AgentRequest(BaseModel):
    query: str

# 🌐 عرض واجهة المستخدم فوراً عند فتح رابط الموقع الرئيسي
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h3>⚠️ ملف index.html غير موجود في المجلد الرئيسي!</h3>"

@app.post("/api/biophysique-agent")
async def biophysique_agent(request: AgentRequest):
    pdfs_folder = "pdfs"
    context_text = extract_text_from_all_pdfs(pdfs_folder)
    
    if not context_text.strip():
        return {"response": "<div class='error-msg'>⚠️ Erreur : Aucun fichier PDF trouvé dans le dossier 'pdfs'.</div>"}
    
    full_prompt = f"{SYSTEM_INSTRUCTION}\n\n---\n[CONTEXTE]:\n{context_text}\n\n---\n[DEMANDE]:\n{request.query}"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={Gemini_API_KEY}"
    
    payload = {"contents": [{"parts": [{"text": full_prompt}]}]}
    
    for attempt in range(3):
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                return {"response": response.json()['candidates'][0]['content']['parts'][0]['text']}
            time.sleep(2)
        except Exception as e:
            if attempt == 2:
                return {"response": f"<div class='error-msg'>⚠️ Erreur Connection : {str(e)}</div>"}
    return {"response": "<div class='error-msg'>⚠️ Serveur surchargé, réessayez.</div>"}