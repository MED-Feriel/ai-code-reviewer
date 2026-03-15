from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import httpx
import mlflow
import os
import time

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./reviews.db")
MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")

# ── Database ──────────────────────────────────────────
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ReviewRecord(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    language = Column(String(50))
    code = Column(Text)
    analysis = Column(Text)
    model = Column(String(100))
    duration_seconds = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── MLflow ────────────────────────────────────────────
mlflow.set_tracking_uri(MLFLOW_URI)
mlflow.set_experiment("ai-code-reviewer")

# ── FastAPI ───────────────────────────────────────────
app = FastAPI(
    title="AI Code Reviewer API",
    description="Analyse automatique de code avec Ollama + PostgreSQL + MLflow",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

AVAILABLE_MODELS = {
    "llama3.2": {"name": "llama3.2", "label": "Llama 3.2", "specialty": "general"},
    "codellama": {"name": "codellama", "label": "Code Llama", "specialty": "code"},
    "deepseek-coder": {"name": "deepseek-coder", "label": "DeepSeek Coder", "specialty": "code"},
}


class ReviewRequest(BaseModel):
    code: str
    language: str = "python"
    model: str = "llama3.2"


class ReviewResponse(BaseModel):
    id: int
    language: str
    analysis: str
    timestamp: str
    model: str
    duration_seconds: float


@app.get("/")
def root():
    return {"service": "ai-code-reviewer", "version": "3.0.0", "status": "running"}


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
async def review_code(request: ReviewRequest, db: Session = Depends(get_db)):
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

    # ── Sauvegarder en PostgreSQL ──
    record = ReviewRecord(
        language=request.language,
        code=request.code,
        analysis=analysis,
        model=model,
        duration_seconds=duration
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # ── MLflow tracking ──
    try:
        with mlflow.start_run():
            mlflow.log_param("language", request.language)
            mlflow.log_param("model", model)
            mlflow.log_param("code_length", len(request.code))
            mlflow.log_metric("duration_seconds", duration)
            mlflow.log_metric("analysis_length", len(analysis))
            mlflow.log_metric("review_id", record.id)
    except Exception:
        pass

    return ReviewResponse(
        id=record.id,
        language=record.language,
        analysis=analysis,
        timestamp=record.created_at.isoformat(),
        model=model,
        duration_seconds=duration
    )


@app.get("/history")
def get_history(limit: int = 10, db: Session = Depends(get_db)):
    records = db.query(ReviewRecord).order_by(
        ReviewRecord.created_at.desc()
    ).limit(limit).all()
    return [
        {
            "id": r.id,
            "language": r.language,
            "model": r.model,
            "duration_seconds": r.duration_seconds,
            "created_at": r.created_at.isoformat()
        }
        for r in records
    ]


@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    total = db.query(ReviewRecord).count()
    return {
        "total_reviews": total,
        "service": "ai-code-reviewer",
        "version": "3.0.0"
    }
