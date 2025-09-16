# import os
# import csv
# import requests
# from datetime import datetime
# from fastapi import FastAPI, Depends, HTTPException, Form
# from fastapi.responses import PlainTextResponse
# from pydantic import BaseModel
# from sqlalchemy.orm import Session

# from backend.db import engine, SessionLocal, Base
# from backend import models
# from backend.rag_utils import retrieve_docs  # <-- you created this in Day 2

# # Auto-create tables
# Base.metadata.create_all(bind=engine)

# app = FastAPI(title="AI Health Chatbot Backend (Prototype)")

# # ---------------------------
# # Pydantic Schemas
# # ---------------------------
# class QueryIn(BaseModel):
#     phone: str
#     message: str
#     channel: str = "whatsapp"

# class QueryOut(BaseModel):
#     query_id: int
#     status: str

# class RagQueryIn(BaseModel):
#     question: str
#     top_k: int = 3

# # ---------------------------
# # DB Dependency
# # ---------------------------
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# # ---------------------------
# # Routes
# # ---------------------------
# @app.get("/health")
# def health():
#     return {"status": "ok", "time": datetime.utcnow().isoformat() + "Z"}


# @app.post("/query", response_model=QueryOut)
# def receive_query(payload: QueryIn, db: Session = Depends(get_db)):
#     # find or create user
#     user = db.query(models.User).filter(models.User.phone == payload.phone).first()
#     if not user:
#         user = models.User(phone=payload.phone)
#         db.add(user)
#         db.commit()
#         db.refresh(user)

#     # save query
#     q = models.Query(
#         user_id=user.id,
#         channel=payload.channel,
#         message_text=payload.message,
#         status="received"
#     )
#     db.add(q)
#     db.commit()
#     db.refresh(q)

#     return {"query_id": q.id, "status": "saved"}


# # ---------------------------
# # RAG Only (for debugging)
# # ---------------------------
# @app.post("/rag-query")
# def rag_query(payload: RagQueryIn):
#     """Return top-k retrieved docs from FAISS (debug only)."""
#     results = retrieve_docs(payload.question, top_k=payload.top_k)
#     return {"question": payload.question, "results": results}


# # ---------------------------
# # RAG + MedGemma
# # ---------------------------
# @app.post("/ask-ml")
# def ask_ml(payload: RagQueryIn):
#     """Full RAG pipeline: retriever + MedGemma API call."""
#     # Step 1: retrieve docs
#     results = retrieve_docs(payload.question, top_k=payload.top_k)
#     context = "\n".join([r["text"] for r in results])

#     # Step 2: format prompt
#     prompt = f"""You are a helpful health assistant.
# Use the context below to answer the question.

# Context:
# {context}

# Question: {payload.question}
# Answer:"""

#     # Step 3: call MedGemma API (Colab or external URL)
#     MEDGEMMA_URL = os.getenv("MEDGEMMA_API_URL", "http://localhost:8001/medgemma")  
#     try:
#         resp = requests.post(MEDGEMMA_URL, json={"prompt": prompt}, timeout=30)
#         resp.raise_for_status()
#         answer = resp.json().get("answer", "⚠️ No answer from MedGemma")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"MedGemma API error: {e}")

#     return {"question": payload.question, "answer": answer, "context_used": results}


# # ---------------------------
# # FAQ Endpoint
# # ---------------------------
# @app.get("/faq")
# def get_faq():
#     faqs = []
#     FAQ_PATH = os.path.join(os.path.dirname(__file__), "..", "knowledge_base_docs", "test_queries.csv")

#     if not os.path.exists(FAQ_PATH):
#         return {"faqs": [], "error": "FAQ file not found"}

#     with open(FAQ_PATH, newline="", encoding="utf-8") as f:
#         reader = csv.DictReader(f)
#         for row in reader:
#             faqs.append({
#                 "id": row["query_id"],
#                 "category": row["category"],
#                 "question": row["question"],
#                 "answer": row["answer"]
#             })
#     return {"faqs": faqs}


# # ---------------------------
# # Twilio Webhook (WhatsApp)
# # ---------------------------
# @app.post("/webhook/twilio", response_class=PlainTextResponse)
# def twilio_webhook(
#     From: str = Form(...),  # sender's phone number
#     Body: str = Form(...),  # message text
#     To: str = Form(...),    # your Twilio number
#     db: Session = Depends(get_db)
# ):
#     phone = From.replace("whatsapp:", "").strip()

#     # Find or create user
#     user = db.query(models.User).filter(models.User.phone == phone).first()
#     if not user:
#         user = models.User(phone=phone)
#         db.add(user)
#         db.commit()
#         db.refresh(user)

#     # Save query
#     q = models.Query(
#         user_id=user.id,
#         channel="whatsapp",
#         message_text=Body,
#         status="received"
#     )
#     db.add(q)
#     db.commit()
#     db.refresh(q)

#     # Call RAG+MedGemma pipeline
#     try:
#         results = retrieve_docs(Body, top_k=3)
#         context = "\n".join([r["text"] for r in results])
#         prompt = f"Context:\n{context}\n\nQuestion: {Body}\nAnswer:"
#         MEDGEMMA_URL = os.getenv("MEDGEMMA_API_URL", "http://localhost:8001/medgemma")
#         resp = requests.post(MEDGEMMA_URL, json={"prompt": prompt}, timeout=30)
#         resp.raise_for_status()
#         answer = resp.json().get("answer", "⚠️ No answer from MedGemma")
#     except Exception:
#         answer = "⚠️ Sorry, AI is not available right now."

#     # Save AI response
#     q.response_text = answer
#     q.status = "answered"
#     db.commit()

#     return answer



# backend/main.py
# import os
# import csv
# import requests
# from datetime import datetime
# from typing import List
# from fastapi import FastAPI, Depends, HTTPException, Form
# from fastapi.responses import PlainTextResponse, JSONResponse
# from pydantic import BaseModel
# from sqlalchemy.orm import Session

# from backend.db import engine, SessionLocal, Base
# from backend import models
# from backend.rag_utils import retrieve_docs  # uses knowledge_base_docs/faiss_index.bin

# # Auto-create tables if not using migrations
# Base.metadata.create_all(bind=engine)

# app = FastAPI(title="AI Health Chatbot Backend (Prototype) - Day 3 RAG")

# # ---------------------------
# # Pydantic Schemas
# # ---------------------------
# class QueryIn(BaseModel):
#     phone: str
#     message: str
#     channel: str = "whatsapp"

# class QueryOut(BaseModel):
#     query_id: int
#     status: str

# class RagQueryIn(BaseModel):
#     question: str
#     top_k: int = 3

# # ---------------------------
# # DB Dependency
# # ---------------------------
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# # ---------------------------
# # Utilities
# # ---------------------------
# MEDGEMMA_API_URL = os.getenv("MEDGEMMA_API_URL")  # MUST be set in Render (ngrok/Colab or hosted ML service)
# DEFAULT_SYSTEM_PROMPT = (
#     "You are a helpful, cautious medical assistant. Use only the provided authoritative documents for facts. "
#     "If the answer is uncertain, advise consulting a healthcare professional."
# )

# def call_medgemma(prompt: str, system_prompt: str = DEFAULT_SYSTEM_PROMPT, timeout: int = 30):
#     """
#     Call remote MedGemma API. The remote API must accept JSON: { "question":..., "context":..., "system_prompt":... }
#     and return JSON { "answer": "..." }.
#     """
#     if not MEDGEMMA_API_URL:
#         raise RuntimeError("MEDGEMMA_API_URL not set (point it to your Colab/ngrok or ML service)")

#     payload = {"prompt": prompt, "system_prompt": system_prompt}
#     try:
#         resp = requests.post(MEDGEMMA_API_URL, json=payload, timeout=timeout)
#         resp.raise_for_status()
#         data = resp.json()
#         # support common key names
#         answer = data.get("answer") or data.get("generated_text") or data.get("text")
#         return answer
#     except requests.RequestException as e:
#         raise RuntimeError(f"MedGemma API request failed: {e}")

# # ---------------------------
# # Routes
# # ---------------------------
# @app.get("/health")
# def health():
#     return {"status": "ok", "time": datetime.utcnow().isoformat() + "Z"}

# @app.post("/query", response_model=QueryOut)
# def receive_query(payload: QueryIn, db: Session = Depends(get_db)):
#     # find or create user
#     user = db.query(models.User).filter(models.User.phone == payload.phone).first()
#     if not user:
#         user = models.User(phone=payload.phone)
#         db.add(user)
#         db.commit()
#         db.refresh(user)

#     # save query
#     q = models.Query(
#         user_id=user.id,
#         channel=payload.channel,
#         message_text=payload.message,
#         status="received"
#     )
#     db.add(q)
#     db.commit()
#     db.refresh(q)

#     return {"query_id": q.id, "status": "saved"}

# # ---------------------------
# # RAG only endpoint (debug)
# # ---------------------------
# @app.post("/rag-query")
# def rag_query(payload: RagQueryIn):
#     """Return top-k retrieved docs/snippets from FAISS (for debug/QA)."""
#     try:
#         results = retrieve_docs(payload.question, top_k=payload.top_k)
#         return {"question": payload.question, "results": results}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# # ---------------------------
# # Full RAG -> MedGemma pipeline
# # ---------------------------
# @app.post("/ask-ml")
# def ask_ml(payload: RagQueryIn, db: Session = Depends(get_db)):
#     """
#     Full pipeline:
#       1. retrieve top-k snippets (FAISS)
#       2. build prompt (system + context + question)
#       3. send to remote MedGemma API
#       4. store answer + provenance in DB, return answer + sources
#     """
#     # 1) Retrieve
#     try:
#         snippets = retrieve_docs(payload.question, top_k=payload.top_k)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Retriever error: {e}")

#     # Build context text and provenance
#     context_texts = []
#     for s in snippets:
#         # s expected keys: 'text', 'doc', 'score', etc.
#         context_texts.append(s.get("text", ""))

#     context = "\n\n".join(context_texts) if context_texts else ""

#     # 2) Format prompt
#     system_prompt = DEFAULT_SYSTEM_PROMPT
#     full_prompt = f"{system_prompt}\n\nContext:\n{context}\n\nQuestion: {payload.question}\nAnswer:"

#     # 3) Call MedGemma
#     try:
#         answer = call_medgemma(full_prompt, system_prompt=system_prompt, timeout=60)
#         if answer is None:
#             raise RuntimeError("MedGemma returned empty answer")
#     except Exception as e:
#         raise HTTPException(status_code=502, detail=f"MedGemma call failed: {e}")

#     # 4) Optionally store query+answer+provenance in DB (create an anonymous user record if none)
#     # create an audit Query record (user_id may be null in this endpoint)
#     q = models.Query(user_id=None, channel="api", message_text=payload.question, response_text=answer, status="answered")
#     db.add(q)
#     db.commit()
#     db.refresh(q)

#     # store provenance snippets
#     for s in snippets:
#         rs = models.RAGSnippet(
#             query_id=q.id,
#             source_url=s.get("doc"),
#             snippet=s.get("text")
#         )
#         db.add(rs)
#     db.commit()

#     # 5) Respond
#     return {
#         "question": payload.question,
#         "answer": answer,
#         "provenance": [
#             {"doc": s.get("doc"), "snippet": s.get("text"), "score": s.get("score"), "rank": s.get("rank")}
#             for s in snippets
#         ],
#         "query_id": q.id
#     }

# # ---------------------------
# # FAQ (CSV) endpoint (unchanged)
# # ---------------------------
# @app.get("/faq")
# def get_faq():
#     faqs = []
#     FAQ_PATH = os.path.join(os.path.dirname(__file__), "..", "knowledge_base_docs", "test_queries.csv")

#     if not os.path.exists(FAQ_PATH):
#         return {"faqs": [], "error": "FAQ file not found"}

#     with open(FAQ_PATH, newline="", encoding="utf-8") as f:
#         reader = csv.DictReader(f)
#         for row in reader:
#             faqs.append({
#                 "id": row.get("query_id"),
#                 "category": row.get("category"),
#                 "question": row.get("question"),
#                 "answer": row.get("answer")
#             })
#     return {"faqs": faqs}

# # ---------------------------
# # Twilio Webhook (WhatsApp)
# # ---------------------------
# @app.post("/webhook/twilio", response_class=PlainTextResponse)
# def twilio_webhook(
#     From: str = Form(...),
#     Body: str = Form(...),
#     To: str = Form(...),
#     db: Session = Depends(get_db)
# ):
#     phone = From.replace("whatsapp:", "").strip()

#     # Find or create user
#     user = db.query(models.User).filter(models.User.phone == phone).first()
#     if not user:
#         user = models.User(phone=phone)
#         db.add(user)
#         db.commit()
#         db.refresh(user)

#     # Save incoming message
#     q = models.Query(user_id=user.id, channel="whatsapp", message_text=Body, status="received")
#     db.add(q)
#     db.commit()
#     db.refresh(q)

#     # Try to answer via RAG+MedGemma (best-effort)
#     try:
#         # retrieve
#         snippets = retrieve_docs(Body, top_k=3)
#         context = "\n\n".join([s.get("text", "") for s in snippets])
#         system_prompt = DEFAULT_SYSTEM_PROMPT
#         prompt = f"{system_prompt}\n\nContext:\n{context}\n\nQuestion: {Body}\nAnswer:"
#         answer = call_medgemma(prompt, system_prompt=system_prompt, timeout=45)
#         if not answer:
#             answer = "⚠️ AI did not return an answer. Please try again later."
#     except Exception:
#         answer = "⚠️ Sorry, the AI service is temporarily unavailable."

#     # save response & provenance
#     q.response_text = answer
#     q.status = "answered"
#     db.commit()

#     # save snippets as provenance
#     for s in snippets:
#         rs = models.RAGSnippet(query_id=q.id, source_url=s.get("doc"), snippet=s.get("text"))
#         db.add(rs)
#     db.commit()

#     return answer

# backend/main.py
# import os
# import csv
# from datetime import datetime
# from fastapi import FastAPI, Depends, HTTPException, Form
# from fastapi.responses import PlainTextResponse
# from pydantic import BaseModel
# from sqlalchemy.orm import Session

# from backend.db import engine, SessionLocal, Base
# from backend import models
# from backend.rag_utils import retrieve_docs, ask_medgemma

# # Auto-create tables
# Base.metadata.create_all(bind=engine)

# app = FastAPI(title="AI Health Chatbot Backend (Prototype)")

# # ---------------------------
# # Pydantic Schemas
# # ---------------------------
# class QueryIn(BaseModel):
#     phone: str
#     message: str
#     channel: str = "whatsapp"

# class QueryOut(BaseModel):
#     query_id: int
#     status: str

# class RAGIn(BaseModel):
#     question: str
#     top_k: int = 3

# # ---------------------------
# # DB Dependency
# # ---------------------------
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# # ---------------------------
# # Routes
# # ---------------------------
# @app.get("/health")
# def health():
#     return {"status": "ok", "time": datetime.utcnow().isoformat() + "Z"}


# @app.post("/query", response_model=QueryOut)
# def receive_query(payload: QueryIn, db: Session = Depends(get_db)):
#     # find or create user
#     user = db.query(models.User).filter(models.User.phone == payload.phone).first()
#     if not user:
#         user = models.User(phone=payload.phone)
#         db.add(user)
#         db.commit()
#         db.refresh(user)

#     # save query
#     q = models.Query(
#         user_id=user.id,
#         channel=payload.channel,
#         message_text=payload.message,
#         status="received"
#     )
#     db.add(q)
#     db.commit()
#     db.refresh(q)

#     return {"query_id": q.id, "status": "saved"}


# @app.post("/ask-ml")
# def ask_ml(question: str):
#     # 🚧 Legacy stub (kept for testing only)
#     return {"answer": f"Stub response for: {question}"}


# @app.get("/faq")
# def get_faq():
#     faqs = []
#     FAQ_PATH = os.path.join(os.path.dirname(__file__), "..", "knowledge_base_docs", "test_queries.csv")

#     if not os.path.exists(FAQ_PATH):
#         return {"faqs": [], "error": "FAQ file not found"}

#     with open(FAQ_PATH, newline="", encoding="utf-8") as f:
#         reader = csv.DictReader(f)
#         for row in reader:
#             faqs.append({
#                 "id": row["query_id"],
#                 "category": row["category"],
#                 "question": row["question"],
#                 "answer": row["answer"]
#             })
#     return {"faqs": faqs}


# @app.post("/webhook/twilio", response_class=PlainTextResponse)
# def twilio_webhook(
#     From: str = Form(...),  # sender's phone number
#     Body: str = Form(...),  # message text
#     To: str = Form(...),    # your Twilio number
#     db: Session = Depends(get_db)
# ):
#     phone = From.replace("whatsapp:", "").strip()

#     # Find or create user
#     user = db.query(models.User).filter(models.User.phone == phone).first()
#     if not user:
#         user = models.User(phone=phone)
#         db.add(user)
#         db.commit()
#         db.refresh(user)

#     # Save query
#     q = models.Query(
#         user_id=user.id,
#         channel="whatsapp",
#         message_text=Body,
#         status="received"
#     )
#     db.add(q)
#     db.commit()
#     db.refresh(q)

#     # --- Call RAG pipeline (retrieve + MedGemma) ---
#     retrieved = retrieve_docs(Body, top_k=3)
#     rag_result = ask_medgemma(Body, retrieved)

#     answer = rag_result.get("answer", "Sorry, AI could not answer.")

#     # Save AI response
#     q.response_text = answer
#     q.status = "answered"
#     db.commit()

#     # Respond to Twilio (plain text)
#     return answer


# @app.post("/rag-ask")
# def rag_ask(payload: RAGIn):
#     """Full RAG endpoint: retrieve docs + MedGemma response"""
#     retrieved = retrieve_docs(payload.question, top_k=payload.top_k)
#     rag_result = ask_medgemma(payload.question, retrieved)
#     return {
#         "question": payload.question,
#         "retrieved": retrieved,
#         "answer": rag_result.get("answer"),
#         "debug": rag_result
#     }


# backend/main.py
import os
import csv
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Form
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db import engine, SessionLocal, Base
from backend import models
from backend.rag_utils import retrieve_docs, ask_medgemma

# Auto-create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Health Chatbot Backend (Prototype)")

# ---------------------------
# Pydantic Schemas
# ---------------------------
class QueryIn(BaseModel):
    phone: str
    message: str
    channel: str = "whatsapp"

class QueryOut(BaseModel):
    query_id: int
    status: str

class RAGIn(BaseModel):
    question: str
    top_k: int = 3

# NEW: Reminder Schema
class ReminderIn(BaseModel):
    user_id: int
    vaccine_name: str
    due_date: str   # ISO format: YYYY-MM-DD

# ---------------------------
# DB Dependency
# ---------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------
# Routes
# ---------------------------
@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat() + "Z"}


@app.post("/query", response_model=QueryOut)
def receive_query(payload: QueryIn, db: Session = Depends(get_db)):
    # find or create user
    user = db.query(models.User).filter(models.User.phone == payload.phone).first()
    if not user:
        user = models.User(phone=payload.phone)
        db.add(user)
        db.commit()
        db.refresh(user)

    # save query
    q = models.Query(
        user_id=user.id,
        channel=payload.channel,
        message_text=payload.message,
        status="received"
    )
    db.add(q)
    db.commit()
    db.refresh(q)

    return {"query_id": q.id, "status": "saved"}


@app.post("/ask-ml")
def ask_ml(question: str):
    return {"answer": f"Stub response for: {question}"}


@app.get("/faq")
def get_faq():
    faqs = []
    FAQ_PATH = os.path.join(os.path.dirname(__file__), "..", "knowledge_base_docs", "test_queries.csv")

    if not os.path.exists(FAQ_PATH):
        return {"faqs": [], "error": "FAQ file not found"}

    with open(FAQ_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            faqs.append({
                "id": row["query_id"],
                "category": row["category"],
                "question": row["question"],
                "answer": row["answer"]
            })
    return {"faqs": faqs}


@app.post("/webhook/twilio", response_class=PlainTextResponse)
def twilio_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    To: str = Form(...),
    db: Session = Depends(get_db)
):
    phone = From.replace("whatsapp:", "").strip()

    user = db.query(models.User).filter(models.User.phone == phone).first()
    if not user:
        user = models.User(phone=phone)
        db.add(user)
        db.commit()
        db.refresh(user)

    q = models.Query(
        user_id=user.id,
        channel="whatsapp",
        message_text=Body,
        status="received"
    )
    db.add(q)
    db.commit()
    db.refresh(q)

    retrieved = retrieve_docs(Body, top_k=3)
    rag_result = ask_medgemma(Body, retrieved)
    answer = rag_result.get("answer", "Sorry, AI could not answer.")

    q.response_text = answer
    q.status = "answered"
    db.commit()

    return answer


@app.post("/rag-ask")
def rag_ask(payload: RAGIn):
    retrieved = retrieve_docs(payload.question, top_k=payload.top_k)
    rag_result = ask_medgemma(payload.question, retrieved)
    return {
        "question": payload.question,
        "retrieved": retrieved,
        "answer": rag_result.get("answer"),
        "debug": rag_result
    }

# ---------------------------
# NEW: Vaccination Mock Endpoint
# ---------------------------
@app.get("/vaccination/mock")
def mock_vaccination():
    return {
        "status": "ok",
        "slots": [
            {"date": "2025-09-20", "vaccine": "COVID-19", "center": "Community Clinic"},
            {"date": "2025-09-21", "vaccine": "Hepatitis B", "center": "City Hospital"}
        ]
    }

# ---------------------------
# NEW: Create Reminder Endpoint
# ---------------------------
@app.post("/reminder")
def create_reminder(payload: ReminderIn, db: Session = Depends(get_db)):
    reminder = models.Reminder(
        user_id=payload.user_id,
        vaccine_name=payload.vaccine_name,
        due_date=payload.due_date,
        status="pending"
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return {"id": reminder.id, "status": reminder.status}


# --- NEW: Day 5 Task Endpoints ---
@app.get("/alerts")
def get_alerts(db: Session = Depends(get_db)):
    """
    Endpoint to serve alert data to the frontend.
    It now uses a SQLAlchemy session to query the 'alerts' table.
    """
    try:
        # Use the session to query the Alert model, order by date, and get all results
        alerts = db.query(models.Alert).order_by(models.Alert.created_at.desc()).all()
        return alerts
    except Exception as e:
        print(f"Database error in /alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts.")


# backend/main.py

@app.get("/education")
def get_education_topics():
    """
    This updated endpoint now searches through all subdirectories
    for valid document files.
    """
    docs_path = os.path.join('knowledge_base_docs', 'documents')
    topics = set()  # Use a set to automatically handle duplicate filenames

    if not os.path.isdir(docs_path):
        raise HTTPException(status_code=404, detail="Education documents directory not found.")

    # Use os.walk to go through all folders and subfolders
    for root, dirs, files in os.walk(docs_path):
        for filename in files:
            # Check for valid file extensions
            if filename.endswith(('.pdf', '.txt', '.md')):
                topic_name = os.path.splitext(filename)[0]
                topic_name = topic_name.replace('_', ' ').replace('-', ' ').title()
                topics.add(topic_name)

    return {"topics": sorted(list(topics))}