import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import pypdf
import requests

app = FastAPI()

# جلب مفتاح الـ API بشكل آمن ومخفي (يدعم الطريقتين بالشرطة السفلية لمنع أخطاء المسافات في السيرفر)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("Gemini_API_KEY") or ""

# نموذج مرن لاستقبال الأسئلة من واجهة المستخدم بأي صيغة أرستلها
class ChatRequest(BaseModel):
    message: str = None
    question: str = None
    prompt: str = None

def load_all_pdfs():
    """قراءة واستخراج النصوص من جميع المحاضرات الطبية في مجلد pdfs"""
    combined_text = ""
    pdf_dir = "pdfs"
    
    if os.path.exists(pdf_dir):
        for filename in sorted(os.listdir(pdf_dir)):
            if filename.endswith(".pdf"):
                file_path = os.path.join(pdf_dir, filename)
                try:
                    with open(file_path, "rb") as f:
                        reader = pypdf.PdfReader(f)
                        for page in reader.pages:
                            text = page.extract_text()
                            if text:
                                combined_text += text + "\n"
                except Exception as e:
                    print(f"Error reading {filename}: {e}")
    return combined_text

# تحميل نصوص المحاضرات في الذاكرة عند تشغيل السيرفر لتسريع الاستجابة
PDF_CONTEXT = load_all_pdfs()

@app.get("/")
async def serve_index():
    """عرض واجهة المستخدم الخاصة بالموقع"""
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"error": "index.html file not found"}

@app.post("/api/biophysique-agent")
async def biophysique_agent(request: ChatRequest):
    """المسار الرئيسي لاستقبال أسئلة الطلاب والإجابة عليها بواسطة جيميناي"""
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API Key is missing on the server configuration.")
    
    # تحديد السؤال القادم من الطلاب بغض النظر عن المسمى المرسل من الـ JavaScript
    user_query = request.message or request.question or request.prompt
    if not user_query:
        raise HTTPException(status_code=400, detail="Message content cannot be empty.")
    
    # صياغة البرومبت وتدعيمه بمحتوى المحاضرات (مع تحديد حد أقصى للنصوص لحماية حجم الطلب)
    system_prompt = (
        "أنت مساعد ذكي مخصص لمادة البيوفيزياء الطبيّة (Biophysique). "
        "استعن بالسياق العلمي التالي المستخرج من محاضرات الطلاب للإجابة على سؤال الطالب بدقة وبأسلوب طبي تعليمي واضح:\n\n"
        f"[المحاضرات الطبية]:\n{PDF_CONTEXT[:20000]}\n\n"
        f"[سؤال الطالب]: {user_query}"
    )
    
    # إرسال الطلب لـ Gemini API عبر Requests
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [{"text": system_prompt}]
            }
        ]
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()
        
        if response.status_code == 200:
            ai_response = response_data['candidates'][0]['content']['parts'][0]['text']
            return {"response": ai_response}
        else:
            error_msg = response_data.get("error", {}).get("message", "Unknown API Error")
            raise HTTPException(status_code=response.status_code, detail=f"Gemini API Error: {error_msg}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
