from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import httpx
import os
import time

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")

AVAILABLE_MODELS = {
    "llama3.2": {
        "name": "llama3.2",
        "label": "Llama 3.2",
        "description": "Modèle généraliste rapide",
        "specialty": "general"
    },
    "codellama": {
        "name": "codellama",
        "label": "Code Llama",
        "description": "Spécialisé pour le code",
        "specialty": "code"
    },
    "deepseek-coder": {
        "name": "deepseek-coder",
        "label": "DeepSeek Coder",
        "description": "Expert en analyse de code",
        "specialty": "code"
    },
}

app = FastAPI(
    title="AI Code Reviewer API",
    description="Analyse automatique de code avec Ollama — Multi-modèles",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ReviewRequest(BaseModel):
    code: str
    language: str = "python"
    model: str = "llama3.2"


class ReviewResponse(BaseModel):
    language: str
    analysis: str
    timestamp: str
    model: str
    duration_seconds: float


@app.get("/")
def root():
    return {"service": "ai-code-reviewer", "version": "2.0.0", "status": "running"}


@app.get("/health")
def health():
    return {"status": "healthy", "service": "ai-code-reviewer"}


@app.get("/languages")
def get_languages():
    return {
        "languages": ["python", "javascript", "dockerfile", "yaml", "bash", "java", "go"]
    }


@app.get("/models")
def get_models():
    return {"models": list(AVAILABLE_MODELS.values())}


@app.post("/review", response_model=ReviewResponse)
async def review_code(request: ReviewRequest):
    start_time = time.time()

    model = request.model if request.model in AVAILABLE_MODELS else "llama3.2"

    prompt = (
        f"Tu es un expert en revue de code. Analyse ce code {request.language} et fournis:\n"
        f"1. Un résumé de ce que fait le code\n"
        f"2. Les problèmes détectés (bugs, sécurité, performance)\n"
        f"3. Les bonnes pratiques manquantes\n"
        f"4. Des suggestions d'amélioration concrètes\n\n"
        f"Code à analyser:\n{request.code}\n\n"
        f"Réponds en français de façon structurée et concise."
    )

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False}
            )
            data = response.json()
            analysis = data.get("response", "Erreur lors de l'analyse")
    except Exception as e:
        analysis = f"Ollama non disponible: {str(e)}"

    duration = round(time.time() - start_time, 2)

    return ReviewResponse(
        language=request.language,
        analysis=analysis,
        timestamp=datetime.utcnow().isoformat(),
        model=model,
        duration_seconds=duration
    )