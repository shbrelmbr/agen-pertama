from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from crewai.project.crew_loader import load_crew

app = FastAPI(title="AI Agent API", version="1.0")

# CORS — agar Next.js nanti bisa memanggil API ini dari browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Untuk development. Nanti di produksi, batasi ke URL Next.js
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load crew sekali saja saat startup (agar tidak lambat di setiap request)
print("🔧 Memuat crew dari crew.jsonc...")
crew, _ = load_crew("crew.jsonc")
print("✅ Crew siap!")


class ChatRequest(BaseModel):
    topik: str


@app.get("/")
def root():
    return {"status": "ok", "message": "AI Agent API berjalan"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/chat")
def chat(request: ChatRequest):
    if not request.topik.strip():
        raise HTTPException(status_code=400, detail="Topik tidak boleh kosong")
    
    try:
        result = crew.kickoff(inputs={"topik": request.topik})
        return {
            "status": "success",
            "topik": request.topik,
            "hasil": str(result),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))