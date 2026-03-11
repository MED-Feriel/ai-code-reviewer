from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import httpx

app = FastAPI(
    title="AI Code Reviewer API",
    description="Analyse automatique de code avec Ollama",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = "http://host.docker.internal:11434"

class ReviewRequest(BaseModel):
    code: str
    language: str = "python"

class ReviewResponse(BaseModel):
    language: str
    analysis: str
    timestamp: str
    model: str

@app.get("/")
def root():
    return {"service": "ai-code-reviewer", "status": "running"}

@app.get("/health")
def health():
    return {"status": "healthy", "service": "ai-code-reviewer"}

@app.get("/languages")
def get_languages():
    return {
        "languages": ["python", "javascript", "dockerfile", "yaml", "bash", "java", "go"]
    }

@app.post("/review", response_model=ReviewResponse)
async def review_code(request: ReviewRequest):
    prompt = f"""Tu es un expert en revue de code. Analyse ce code {request.language} et fournis:
1. Un résumé de ce que fait le code
2. Les problèmes détectés (bugs, sécurité, performance)
3. Les bonnes pratiques manquantes
4. Des suggestions d'amélioration concrètes

Code à analyser:
```{request.language}
{request.code}
```

Réponds en français de façon structurée et concise."""

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": "llama3.2",
                    "prompt": prompt,
                    "stream": False
                }
            )
            data = response.json()
            analysis = data.get("response", "Erreur lors de l'analyse")
    except Exception as e:
        analysis = f"Ollama non disponible: {str(e)}"

    return ReviewResponse(
        language=request.language,
        analysis=analysis,
        timestamp=datetime.utcnow().isoformat(),
        model="llama3.2"
    )
```

---

## Fichier 2 — `api-ai/requirements.txt`
```
fastapi==0.110.0
uvicorn==0.29.0
pydantic==2.6.4
httpx==0.27.0
pytest==8.1.0
pytest-asyncio==0.23.6