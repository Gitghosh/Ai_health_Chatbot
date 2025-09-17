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

# # NEW: Reminder Schema
# class ReminderIn(BaseModel):
#     user_id: int
#     vaccine_name: str
#     due_date: str   # ISO format: YYYY-MM-DD

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


# # @app.post("/query", response_model=QueryOut)
# # def receive_query(payload: QueryIn, db: Session = Depends(get_db)):
# #     # find or create user
# #     user = db.query(models.User).filter(models.User.phone == payload.phone).first()
# #     if not user:
# #         user = models.User(phone=payload.phone)
# #         db.add(user)
# #         db.commit()
# #         db.refresh(user)

# #     # save query
# #     q = models.Query(
# #         user_id=user.id,
# #         channel=payload.channel,
# #         message_text=payload.message,
# #         status="received"
# #     )
# #     db.add(q)
# #     db.commit()
# #     db.refresh(q)

# #     return {"query_id": q.id, "status": "saved"}
# @app.post("/query", response_model=QueryOut)+++++++++++++++++++++++
# def receive_query(payload: QueryIn, db: Session = Depends(get_db)):
#     # Find or create user
#     user = db.query(models.User).filter(models.User.phone == payload.phone).first()
#     if not user:
#         user = models.User(phone=payload.phone)
#         db.add(user)
#         db.commit()
#         db.refresh(user)

#     # Save query
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
#     return {"faqs": faqs}-----------------------------


# # @app.post("/webhook/twilio", response_class=PlainTextResponse)
# # def twilio_webhook(
# #     From: str = Form(...),
# #     Body: str = Form(...),
# #     To: str = Form(...),
# #     db: Session = Depends(get_db)
# # ):
# #     phone = From.replace("whatsapp:", "").strip()

# #     user = db.query(models.User).filter(models.User.phone == phone).first()
# #     if not user:
# #         user = models.User(phone=phone)
# #         db.add(user)
# #         db.commit()
# #         db.refresh(user)

# #     q = models.Query(
# #         user_id=user.id,
# #         channel="whatsapp",
# #         message_text=Body,
# #         status="received"
# #     )
# #     db.add(q)
# #     db.commit()
# #     db.refresh(q)

# #     retrieved = retrieve_docs(Body, top_k=3)
# #     rag_result = ask_medgemma(Body, retrieved)
# #     answer = rag_result.get("answer", "Sorry, AI could not answer.")

# #     q.response_text = answer
# #     q.status = "answered"
# #     db.commit()

# #     return answer
# @app.post("/webhook/twilio", response_class=PlainTextResponse)++++++++++++++++++++++++
# def twilio_webhook(
#     From: str = Form(...),
#     Body: str = Form(...),
#     db: Session = Depends(get_db)
# ):
#     phone = From.replace("whatsapp:", "").strip()
#     text = Body.lower().strip()
#     answer = "" # Initialize answer variable

#     # 1. Find or create the user
#     user = db.query(models.User).filter(models.User.phone == phone).first()
#     if not user:
#         user = models.User(phone=phone)
#         db.add(user)
#         db.commit()
#         db.refresh(user)

#     # 2. **[FIX]** Store the incoming message in the 'queries' table immediately
#     q = models.Query(
#         user_id=user.id,
#         channel="whatsapp",
#         message_text=Body,
#         status="received"
#     )
#     db.add(q)
#     db.commit()
#     db.refresh(q)

#     # 3. Route the query to the correct flow
#     # ---- MSG-04: Vaccination Chat Flow ----
#     if "schedule" in text or "check vaccination" in text:
#         schedule = [
#             "20 Sep 2025 - COVID-19 @ Community Clinic",
#             "21 Sep 2025 - Hepatitis B @ City Hospital",
#             "25 Sep 2025 - Polio @ Primary Health Center"
#         ]
#         answer = "📅 Upcoming vaccination slots:\n" + "\n".join(schedule)
    
#     elif "reminder" in text or "set reminder" in text:
#         # Example: "Set reminder for Polio on 2025-09-25"
#         try:
#             parts = Body.split("for")[1].strip().split("on")
#             vaccine_name = parts[0].strip()
#             due_date_str = parts[1].strip()
            
#             # Convert string to date object for the database
#             due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()

#             reminder = models.Reminder(
#                 user_id=user.id,
#                 vaccine_name=vaccine_name,
#                 due_date=due_date,
#                 status="pending"
#             )
#             db.add(reminder)
#             db.commit()
#             answer = f"✅ Reminder set for {vaccine_name} on {due_date_str}."
#         except Exception:
#             answer = "⚠️ Please use format: 'Set reminder for <vaccine> on YYYY-MM-DD'"

#     else:
#         # ---- MSG-03: Fallback to RAG pipeline ----
#         try:
#             retrieved = retrieve_docs(Body, top_k=3)
#             rag_result = ask_medgemma(Body, retrieved)
#             answer = rag_result.get("answer", "⚠️ Sorry, I could not find an answer for that.")
#         except Exception as e:
#             print(f"RAG pipeline failed: {e}")
#             answer = "⚠️ Sorry, an error occurred while processing your request."

#     # 4. **[FIX]** Update the query with the final answer
#     q.response_text = answer
#     q.status = "answered"
#     db.commit()

#     # 5. Send the reply
#     return answer


# @app.post("/rag-ask")
# def rag_ask(payload: RAGIn):
#     retrieved = retrieve_docs(payload.question, top_k=payload.top_k)
#     rag_result = ask_medgemma(payload.question, retrieved)
#     return {
#         "question": payload.question,
#         "retrieved": retrieved,
#         "answer": rag_result.get("answer"),
#         "debug": rag_result
#     }

# @app.post("/rag-query")
# def rag_query(payload: RAGIn, db: Session = Depends(get_db)):
#     """This endpoint is for direct testing of the RAG pipeline."""
#     try:
#         retrieved = retrieve_docs(payload.question, top_k=payload.top_k)
#         rag_result = ask_medgemma(payload.question, retrieved)
#         answer = rag_result.get("answer", "⚠️ Sorry, AI could not answer.")
        
#         return {
#             "question": payload.question,
#             "retrieved": retrieved,
#             "answer": answer
#         }
#     except Exception as e:
#         print(f"/rag-query failed: {e}")
#         raise HTTPException(status_code=500, detail="RAG pipeline error")
# # ---------------------------
# # NEW: Vaccination Mock Endpoint
# # ---------------------------
# @app.get("/vaccination/mock")
# def mock_vaccination():
#     return {
#         "status": "ok",
#         "slots": [
#             {"date": "2025-09-20", "vaccine": "COVID-19", "center": "Community Clinic"},
#             {"date": "2025-09-21", "vaccine": "Hepatitis B", "center": "City Hospital"}
#         ]
#     }

# # ---------------------------
# # NEW: Create Reminder Endpoint
# # ---------------------------
# @app.post("/reminder")
# def create_reminder(payload: ReminderIn, db: Session = Depends(get_db)):
#     reminder = models.Reminder(
#         user_id=payload.user_id,
#         vaccine_name=payload.vaccine_name,
#         due_date=payload.due_date,
#         status="pending"
#     )
#     db.add(reminder)
#     db.commit()
#     db.refresh(reminder)
#     return {"id": reminder.id, "status": reminder.status}---------------------


# # --- NEW: Day 5 Task Endpoints ---
# # @app.get("/alerts")
# # def get_alerts(db: Session = Depends(get_db)):
# #     """
# #     Endpoint to serve alert data to the frontend.
# #     It now uses a SQLAlchemy session to query the 'alerts' table.
# #     """
# #     try:
# #         # Use the session to query the Alert model, order by date, and get all results
# #         alerts = db.query(models.Alert).order_by(models.Alert.created_at.desc()).all()
# #         return alerts
# #     except Exception as e:
# #         print(f"Database error in /alerts: {e}")
# #         raise HTTPException(status_code=500, detail="Failed to retrieve alerts.")


# # # backend/main.py

# # @app.get("/education")
# # def get_education_topics():
# #     """
# #     This updated endpoint now searches through all subdirectories
# #     for valid document files.
# #     """
# #     docs_path = os.path.join('knowledge_base_docs', 'documents')
# #     topics = set()  # Use a set to automatically handle duplicate filenames

# #     if not os.path.isdir(docs_path):
# #         raise HTTPException(status_code=404, detail="Education documents directory not found.")

# #     # Use os.walk to go through all folders and subfolders
# #     for root, dirs, files in os.walk(docs_path):
# #         for filename in files:
# #             # Check for valid file extensions
# #             if filename.endswith(('.pdf', '.txt', '.md')):
# #                 topic_name = os.path.splitext(filename)[0]
# #                 topic_name = topic_name.replace('_', ' ').replace('-', ' ').title()
# #                 topics.add(topic_name)

# #     return {"topics": sorted(list(topics))}
# # ---------------------------
# # Day 5 Task Endpoints
# # ---------------------------
# @app.get("/alerts")+++++++++++++++++++++++++++++++++
# def get_alerts(db: Session = Depends(get_db)):
#     """Serves ingested alert data to the frontend."""
#     try:
#         alerts = db.query(models.Alert).order_by(models.Alert.created_at.desc()).all()
#         return alerts
#     except Exception as e:
#         print(f"Database error in /alerts: {e}")
#         raise HTTPException(status_code=500, detail="Failed to retrieve alerts.")

# @app.get("/education")
# def get_education_topics():
#     """Searches subdirectories for document files and returns a list of topics."""
#     docs_path = os.path.join('knowledge_base_docs', 'documents')
#     topics = set()  # Use a set to automatically handle duplicate filenames

#     if not os.path.isdir(docs_path):
#         raise HTTPException(status_code=404, detail="Education documents directory not found.")

#     for root, dirs, files in os.walk(docs_path):
#         for filename in files:
#             if filename.endswith(('.pdf', '.txt', '.md')):
#                 topic_name = os.path.splitext(filename)[0]
#                 topic_name = topic_name.replace('_', ' ').replace('-', ' ').title()
#                 topics.add(topic_name)

#     return {"topics": sorted(list(topics))}---------------------


#Code edited for twilio
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
# from backend.utils import get_message
# from backend.utils import send_whatsapp_message

# import os
# from gtts import gTTS
# from uuid import uuid4
# from fastapi.staticfiles import StaticFiles
# from twilio.rest import Client
# import logging

# # ensure static folder exists (add near startup)
# STATIC_DIR = os.path.join(os.path.dirname(_file_), "..", "static")
# TTS_DIR = os.path.join(STATIC_DIR, "tts")
# os.makedirs(TTS_DIR, exist_ok=True)

# # mount static files so generated audio is publicly accessible
# # place this right after creating the FastAPI app
# app.mount("/static", StaticFiles(directory=os.path.abspath(STATIC_DIR)), name="static")

# # load env vars for Twilio and base url
# TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
# TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
# TWILIO_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")  # e.g. whatsapp:+1415...
# BASE_URL = os.getenv("BASE_URL")  # e.g. https://ai-health-chatbot-6jaw.onrender.com

# twilio_client = None
# if TWILIO_SID and TWILIO_TOKEN:
#     twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)

# # utility to generate TTS file path and url
# def generate_tts_file(text: str, lang: str = "en"):
#     """
#     Generates an MP3 with gTTS and returns (file_path, public_url).
#     """
#     # sanitize + unique filename
#     filename = f"tts_{uuid4().hex}.mp3"
#     filepath = os.path.join(TTS_DIR, filename)

#     # create TTS
#     tts = gTTS(text=text, lang=lang, slow=False)
#     tts.save(filepath)

#     # build public url to file
#     if not BASE_URL:
#         # attempt to build from request host would be better, but BASE_URL env is recommended
#         public_url = f"/static/tts/{filename}"
#     else:
#         public_url = f"{BASE_URL.rstrip('/')}/static/tts/{filename}"

#     return filepath, public_url

# # ---------------------------
# # API: Generate TTS and return link (no Twilio send)
# # ---------------------------
# from pydantic import BaseModel
# class TTSIn(BaseModel):
#     text: str
#     lang: str = "en"   # e.g. 'hi' for Hindi, 'bn' for Bengali, 'ta' for Tamil

# @app.post("/tts")
# def tts_generate(payload: TTSIn):
#     """
#     Generate TTS MP3 for the given text and language.
#     Returns public URL to the file.
#     """
#     try:
#         _, url = generate_tts_file(payload.text, payload.lang)
#         return {"status": "ok", "url": url}
#     except Exception as e:
#         logging.exception("TTS generation failed")
#         raise HTTPException(status_code=500, detail=str(e))

# # ---------------------------
# # API: Generate TTS and send as WhatsApp media via Twilio
# # ---------------------------
# class TTSSendIn(BaseModel):
#     to_phone: str       # recipient phone in whatsapp:+91xxxx...
#     text: str
#     lang: str = "en"
#     caption: str = None  # optional caption text to send with media

# @app.post("/tts/send")
# def tts_generate_and_send(payload: TTSSendIn):
#     """
#     Generates TTS audio, hosts it on /static, and sends it via Twilio WhatsApp as a media message.
#     Returns Twilio message SID and public URL.
#     """
#     if not twilio_client:
#         raise HTTPException(status_code=500, detail="Twilio client not configured. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN.")

#     if not BASE_URL:
#         raise HTTPException(status_code=500, detail="BASE_URL env var must be set to public URL of this app.")

#     # Generate TTS file and build URL
#     try:
#         _, media_url = generate_tts_file(payload.text, payload.lang)
#     except Exception as e:
#         logging.exception("TTS generation failed")
#         raise HTTPException(status_code=500, detail=f"TTS generation failed: {e}")

#     # Send via Twilio
#     try:
#         msg = twilio_client.messages.create(
#             from_=TWILIO_NUMBER,
#             to=payload.to_phone,
#             body=payload.caption or "",            # caption as text message (optional)
#             media_url=[media_url]                  # Twilio accepts list of media URLs
#         )
#         return {"status": "sent", "sid": msg.sid, "media_url": media_url}
#     except Exception as e:
#         logging.exception("Twilio send failed")
#         raise HTTPException(status_code=500, detail=f"Twilio send failed: {e}")

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

# # NEW: Reminder Schema
# class ReminderIn(BaseModel):
#     user_id: int
#     vaccine_name: str
#     due_date: str   # ISO format: YYYY-MM-DD

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
#     From: str = Form(...),
#     Body: str = Form(...),
#     To: str = Form(...),
#     db: Session = Depends(get_db)
# ):
#     # --- Detect channel (WhatsApp vs SMS) ---
#     if "whatsapp:" in From:
#         phone = From.replace("whatsapp:", "").strip()
#         channel = "whatsapp"
#     else:
#         phone = From.strip()
#         channel = "sms"

#     # --- Language setup (later: auto-detect or user profile) ---
#     lang = "hi"

#     # --- Find or create user ---
#     user = db.query(models.User).filter(models.User.phone == phone).first()
#     if not user:
#         user = models.User(phone=phone)
#         db.add(user)
#         db.commit()
#         db.refresh(user)

#     # --- Save incoming query ---
#     q = models.Query(
#         user_id=user.id,
#         channel=channel,
#         message_text=Body,
#         status="received"
#     )
#     db.add(q)
#     db.commit()
#     db.refresh(q)

#     # --- Intent handling ---
#     text = Body.lower().strip()

#     if "schedule" in text or "check vaccination" in text:
#         # Upcoming slots
#         answer = (
#             "📅 Upcoming vaccination slots:\n"
#             "20 Sep 2025 - COVID-19 @ Community Clinic\n"
#             "21 Sep 2025 - Hepatitis B @ City Hospital\n"
#             "25 Sep 2025 - Polio @ Primary Health Center"
#         )

#     elif "reminder" in text or "set reminder" in text:
#         try:
#             # Example: "Set reminder for Polio on 2025-09-25"
#             parts = Body.split("for")[1].strip().split("on")
#             vaccine_name = parts[0].strip()
#             due_date = parts[1].strip()

#             reminder = models.Reminder(
#                 user_id=user.id,
#                 vaccine_name=vaccine_name,
#                 due_date=due_date,
#                 status="pending"
#             )
#             db.add(reminder)
#             db.commit()
#             db.refresh(reminder)

#             answer = f"✅ Reminder set for {vaccine_name} on {due_date}."
#         except Exception as e:
#             print("Reminder parsing error:", e)  # Debug in Render logs
#             answer = "⚠️ Please use format: 'Set reminder for <vaccine> on YYYY-MM-DD'"

#     elif text == "1" and channel == "sms":
#         # Escalation option for SMS
#         answer = get_message("chw_followup", lang)

#     else:
#         # Fallback → RAG pipeline
#         try:
#             payload = RAGIn(question=Body, top_k=3)
#             rag_response = rag_query(payload, db)
#             answer = rag_response["answer"]
#         except Exception as e:
#             print("RAG error:", e)
#             answer = get_message("default", lang)

#     # --- SMS-specific rule: keep short ---
#     if channel == "sms" and len(answer) > 160:
#         answer = "Query too long. CHW will follow up."

#     # --- Save response ---
#     q.response_text = answer
#     q.status = "answered"
#     db.commit()

#     return answer

#     # # ---- Vaccination Chat Flow ----
#     # def process_user_message(text: str, db: Session, user: models.User) -> str:
#     # """Decide how to respond based on user message."""
#     # text_lower = text.lower()

#     # if "schedule" in text_lower or "check vaccination" in text_lower:
#     #     schedule = [
#     #         "20 Sep 2025 - COVID-19 @ Community Clinic",
#     #         "21 Sep 2025 - Hepatitis B @ City Hospital",
#     #         "25 Sep 2025 - Polio @ Primary Health Center"
#     #     ]
#     #     answer = "📅 Upcoming vaccination slots:\n" + "\n".join(schedule)

#     # elif "reminder" in text_lower or "set reminder" in text_lower:
#     #     try:
#     #         # Example input: "Set reminder for Polio on 2025-09-25"
#     #         parts = text.split("for")[1].strip().split("on")
#     #         vaccine_name = parts[0].strip()
#     #         due_date = parts[1].strip()

#     #         reminder = models.Reminder(
#     #             user_id=user.id,
#     #             vaccine_name=vaccine_name,
#     #             due_date=due_date,
#     #             status="pending"
#     #         )
#     #         db.add(reminder)
#     #         db.commit()
#     #         db.refresh(reminder)

#     #         answer = f"✅ Reminder set for {vaccine_name} on {due_date}."
#     #     except Exception as e:
#     #         print("Reminder parsing error:", e)  # Debug log
#     #         answer = "⚠️ Please use format: 'Set reminder for <vaccine> on YYYY-MM-DD'"

#     # else:
#     #     # Fallback → RAG pipeline
#     #     payload = RAGIn(question=text, top_k=3)
#     #     rag_response = rag_query(payload, db)
#     #     answer = rag_response["answer"]

#     # return answer




# @app.post("/rag-ask")
# def rag_ask(payload: RAGIn):
#     retrieved = retrieve_docs(payload.question, top_k=payload.top_k)
#     rag_result = ask_medgemma(payload.question, retrieved)
#     return {
#         "question": payload.question,
#         "retrieved": retrieved,
#         "answer": rag_result.get("answer"),
#         "debug": rag_result
#     }

# @app.post("/rag-query")
# def rag_query(payload: RAGIn, db: Session = Depends(get_db)):
#     try:
#         # Store query in DB (optional if already handled)
#         user = db.query(models.User).filter(models.User.phone == "test_user").first()
#         if not user:
#             user = models.User(phone="test_user")
#             db.add(user)
#             db.commit()
#             db.refresh(user)

#         q = models.Query(
#             user_id=user.id,
#             channel="internal",
#             message_text=payload.question,
#             status="received"
#         )
#         db.add(q)
#         db.commit()
#         db.refresh(q)

#         # Run RAG pipeline
#         retrieved = retrieve_docs(payload.question, top_k=payload.top_k)
#         rag_result = ask_medgemma(payload.question, retrieved)
#         answer = rag_result.get("answer", "⚠️ Sorry, AI could not answer.")

#         # Update DB with answer
#         q.response_text = answer
#         q.status = "answered"
#         db.commit()

#         return {
#             "query_id": q.id,
#             "question": payload.question,
#             "retrieved": retrieved,
#             "answer": answer,
#             "status": q.status
#         }

#     except Exception as e:
#         import logging
#         logging.error(f"/rag-query failed: {e}")
#         raise HTTPException(status_code=500, detail="RAG pipeline error")


# # ---------------------------
# # NEW: Vaccination Mock Endpoint
# # ---------------------------
# @app.get("/vaccination/mock")
# def vaccination_schedule():
#     return {
#         "status": "ok",
#         "schedule": [
#             {"date": "2025-09-20", "vaccine": "COVID-19", "center": "Community Clinic"},
#             {"date": "2025-09-21", "vaccine": "Hepatitis B", "center": "City Hospital"},
#             {"date": "2025-09-25", "vaccine": "Polio", "center": "Primary Health Center"}
#         ]
#     }


# # ---------------------------
# # NEW: Create Reminder Endpoint
# # ---------------------------
# @app.post("/reminder")
# def set_reminder(payload: ReminderIn, db: Session = Depends(get_db)):
#     reminder = models.Reminder(
#         user_id=payload.user_id,
#         vaccine_name=payload.vaccine_name,
#         due_date=payload.due_date,
#         status="pending"
#     )
#     db.add(reminder)
#     db.commit()
#     db.refresh(reminder)
#     return {"id": reminder.id, "status": reminder.status}
# #---------------------------
# # # Day 5 Task Endpoints
# # # ---------------------------
# @app.get("/alerts")
# def get_alerts(db: Session = Depends(get_db)):
#     """Serves ingested alert data to the frontend."""
#     try:
#         alerts = db.query(models.Alert).order_by(models.Alert.created_at.desc()).all()
#         return alerts
#     except Exception as e:
#         print(f"Database error in /alerts: {e}")
#         raise HTTPException(status_code=500, detail="Failed to retrieve alerts.")

# @app.get("/education")
# def get_education_topics():
#     """Searches subdirectories for document files and returns a list of topics."""
#     docs_path = os.path.join('knowledge_base_docs', 'documents')
#     topics = set()  # Use a set to automatically handle duplicate filenames

#     if not os.path.isdir(docs_path):
#         raise HTTPException(status_code=404, detail="Education documents directory not found.")

#     for root, dirs, files in os.walk(docs_path):
#         for filename in files:
#             if filename.endswith(('.pdf', '.txt', '.md')):
#                 topic_name = os.path.splitext(filename)[0]
#                 topic_name = topic_name.replace('_', ' ').replace('-', ' ').title()
#                 topics.add(topic_name)

#     return {"topics": sorted(list(topics))}

# @app.post("/api/set-reminder")
# def set_reminder_from_frontend(payload: ReminderIn, db: Session = Depends(get_db)):
#     """Sets a reminder from the frontend and sends a WhatsApp confirmation."""
#     # Step 1: Save the reminder to the database (similar to your existing logic)
#     reminder = models.Reminder(
#         user_id=payload.user_id,
#         vaccine_name=payload.vaccine_name,
#         due_date=payload.due_date,
#         status="pending"
#     )
#     db.add(reminder)
#     db.commit()
#     db.refresh(reminder)

#     # Step 2: Get the user's phone number
#     user = db.query(models.User).filter(models.User.id == payload.user_id).first()
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")

#     # Step 3: Send the WhatsApp notification
#     message = f"✅ Reminder Confirmed! We will remind you about your {payload.vaccine_name} vaccine scheduled for {payload.due_date}."
#     send_whatsapp_message(user.phone, message)
    
#     return {"status": "success", "message": "Reminder set and notification sent."}



#TTs included main.py
# backend/main.py
import os
import logging
from gtts import gTTS
# from uuid import uuid4
from fastapi.staticfiles import StaticFiles
from twilio.rest import Client
import csv
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Form, Request  # Add BackgroundTasks
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db import engine, SessionLocal, Base
from backend import models
from backend.rag_utils import retrieve_docs, ask_medgemma
from backend.utils import get_message, send_whatsapp_message
from backend.tts_utils import generate_tts_file

# Auto-create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Health Chatbot Backend (Prototype)")
# ensure static/tts exists
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
TTS_DIR = os.path.join(STATIC_DIR, "tts")
os.makedirs(TTS_DIR, exist_ok=True)

# mount static dir
app.mount("/static", StaticFiles(directory=os.path.abspath(STATIC_DIR)), name="static")
# ---------------------------
# Twilio Setup
# ---------------------------
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")  # e.g. whatsapp:+1415xxxx
BASE_URL = os.getenv("BASE_URL")  # e.g. https://your-app.onrender.com

twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


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

# def process_rag_query_in_background(question: str, user_phone: str, query_id: int, db: Session):
#     """
#     This function runs in the background. It gets the AI answer and sends it as a new message.
#     """
#     print(f"BACKGROUND: Starting RAG process for query {query_id}...")
#     try:
#         retrieved = retrieve_docs(question, top_k=3)
#         rag_result = ask_medgemma(question, retrieved)
#         final_answer = rag_result.get("answer", "Sorry, I couldn't find an answer.")

#         # Save the final answer to the original query
#         db_query = db.query(models.Query).filter(models.Query.id == query_id).first()
#         if db_query:
#             db_query.response_text = final_answer
#             db_query.status = "answered"
#             db.commit()

#         # Send the final answer as a NEW WhatsApp message
#         send_whatsapp_message(to_number=user_phone, message=final_answer)
#         print(f"BACKGROUND: Successfully sent RAG response to {user_phone}.")

#     except Exception as e:
#         print(f"BACKGROUND ERROR: RAG process failed for query {query_id}: {e}")
#         # Optionally, send an error message to the user
#         send_whatsapp_message(to_number=user_phone, message="Sorry, an error occurred while I was thinking.")


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

# @app.post("/webhook/twilio", response_class=PlainTextResponse)
# def twilio_webhook(
#     From: str = Form(...),
#     Body: str = Form(...),
#     db: Session = Depends(get_db)
# ):
#     phone = From.replace("whatsapp:", "").strip()
#     channel = "whatsapp" if "whatsapp:" in From else "sms"
#     lang = "hi"
#     text = Body.lower().strip()
#     answer = ""

#     # Find or create user
#     user = db.query(models.User).filter(models.User.phone == phone).first()
#     if not user:
#         user = models.User(phone=phone)
#         db.add(user)
#         db.commit()
#         db.refresh(user)

#     # Save incoming query
#     q = models.Query(user_id=user.id, channel=channel, message_text=Body, status="received")
#     db.add(q)
#     db.commit()
#     db.refresh(q)

#     # Intent handling logic
#     # if "schedule" in text or "check vaccination" in text:
#     #     reminders = db.query(models.Reminder).filter(models.Reminder.user_id == user.id).order_by(models.Reminder.due_date).all()
#     #     if not reminders:
#     #         answer = "You have no upcoming vaccination reminders scheduled."
#     #     else:
#     #         schedule_list = [f"{r.due_date.strftime('%d %b %Y')} - {r.vaccine_name}" for r in reminders]
#     #         answer = "📅 Here are your scheduled vaccination reminders:\n" + "\n".join(schedule_list)
#     if "schedule" in text or "check vaccination" in text:
#     # Query the database for reminders for this specific user
#        reminders = db.query(models.Reminder).filter(models.Reminder.user_id == user.id).order_by(models.Reminder.due_date).all()

#        if not reminders:
#         answer = "You have no upcoming vaccination reminders scheduled."
#        else:
#         # Format the reminders from the database into a nice list
#         schedule_list = [f"{r.due_date.strftime('%d %b %Y')} - {r.vaccine_name}" for r in reminders]
#         answer = "📅 Here are your scheduled vaccination reminders:\n" + "\n".join(schedule_list)
#     elif "reminder" in text or "set reminder" in text:
#         try:
#             parts = Body.split("for")[1].strip().split("on")
#             vaccine_name = parts[0].strip()
#             due_date_str = parts[1].strip()
#             due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
#             reminder = models.Reminder(user_id=user.id, vaccine_name=vaccine_name, due_date=due_date, status="pending")
#             db.add(reminder)
#             db.commit()
#             answer = f"✅ Reminder set for {vaccine_name} on {due_date_str}."
#         except Exception:
#             answer = "⚠️ Please use format: 'Set reminder for <vaccine> on YYYY-MM-DD'"

#     else:
#         # Fallback to RAG pipeline
#         try:
#             retrieved = retrieve_docs(Body, top_k=3)
#             rag_result = ask_medgemma(Body, retrieved)
#             answer = rag_result.get("answer", "⚠️ Sorry, I could not find an answer for that.")
#         except Exception as e:
#             print(f"RAG error: {e}")
#             answer = get_message("default", lang)

#     # Handle voice response request
#     if "voice" in text and twilio_client:
#         try:
#             media_url = generate_tts_file(answer, "en")
#             twilio_client.messages.create(
#                 from_=TWILIO_PHONE_NUMBER,
#                 to=From,
#                 body="Here’s your audio reply 🎧",
#                 media_url=[media_url]
#             )
#         except Exception as e:
#             logging.exception("Voice send failed")

#     # Save response and finalize
#     q.response_text = answer
#     q.status = "answered"
#     db.commit()
    
#     return answer

@app.post("/webhook/twilio", response_class=PlainTextResponse)
def twilio_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    db: Session = Depends(get_db)
):
    phone = From.replace("whatsapp:", "").strip()
    text = Body.lower().strip()
    answer = ""

    # ... (user lookup and initial query saving code remains the same) ...
    user = db.query(models.User).filter(models.User.phone == phone).first()
    if not user:
        user = models.User(phone=phone)
        db.add(user)
        db.commit()
        db.refresh(user)
    q = models.Query(user_id=user.id, channel="whatsapp", message_text=Body, status="received")
    db.add(q)
    db.commit()
    db.refresh(q)

    # Intent handling logic
    if "schedule" in text or "check vaccination" in text:
        # ... (schedule logic remains the same) ...
        reminders = db.query(models.Reminder).filter(models.Reminder.user_id == user.id).order_by(models.Reminder.due_date).all()
        if not reminders:
            answer = "You have no upcoming vaccination reminders scheduled."
        else:
            schedule_list = [f"{r.due_date.strftime('%d %b %Y')} - {r.vaccine_name}" for r in reminders]
            answer = "📅 Here are your scheduled vaccination reminders:\n" + "\n".join(schedule_list)

    elif "reminder" in text or "set reminder" in text:
        # ... (reminder logic remains the same) ...
        try:
            parts = Body.split("for")[1].strip().split("on")
            vaccine_name = parts[0].strip()
            due_date_str = parts[1].strip()
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            reminder = models.Reminder(user_id=user.id, vaccine_name=vaccine_name, due_date=due_date, status="pending")
            db.add(reminder)
            db.commit()
            answer = f"✅ Reminder set for {vaccine_name} on {due_date_str}."
        except Exception:
            answer = "⚠️ Please use format: 'Set reminder for <vaccine> on YYYY-MM-DD'"

    else:
        # Fallback to RAG pipeline with new debug logs
        try:
            print("MAIN.PY: --- Entering RAG fallback ---")
            retrieved = retrieve_docs(Body, top_k=3)
            
            rag_result = ask_medgemma(Body, retrieved)
            print(f"MAIN.PY: Got response from ask_medgemma: {rag_result}")
            
            answer = rag_result.get("answer", "⚠️ Sorry, I could not find an answer for that.")
            print(f"MAIN.PY: Extracted answer: {answer[:50]}...") # Print first 50 chars of the answer
            
        except Exception as e:
            print(f"MAIN.PY: An error occurred in the RAG block: {e}")
            answer = "Sorry, there was an error processing your request with the AI model."
    # Handle voice response request
    if "voice" in text and twilio_client:
        try:
            # Assuming generate_tts_file is available and configured
            filepath, media_url = generate_tts_file(answer, "en")
            twilio_client.messages.create(
                from_=TWILIO_PHONE_NUMBER,
                to=From,
                body="Here’s your audio reply 🎧",
                media_url=[media_url]
            )
        except Exception as e:
            # Use logging for better error tracking in production
            logging.exception("Voice send failed")

    # Final steps with debug logs
    print("MAIN.PY: About to update database with final answer...")
    q.response_text = answer
    q.status = "answered"
    db.commit()
    print("MAIN.PY: Database updated successfully.")
    
    print("MAIN.PY: About to return answer to Twilio...")
    return answer

#Last correct running portion
# @app.post("/webhook/twilio", response_class=PlainTextResponse)
# def twilio_webhook(
#     From: str = Form(...),
#     Body: str = Form(...),
#     db: Session = Depends(get_db)
# ):
#     phone = From.replace("whatsapp:", "").strip()
#     channel = "whatsapp" if "whatsapp:" in From else "sms"
#     lang = "hi"
#     text = Body.lower().strip()
#     answer = ""

#     # Find or create user
#     user = db.query(models.User).filter(models.User.phone == phone).first()
#     if not user:
#         user = models.User(phone=phone)
#         db.add(user)
#         db.commit()
#         db.refresh(user)

#     # Save incoming query
#     q = models.Query(user_id=user.id, channel=channel, message_text=Body, status="received")
#     db.add(q)
#     db.commit()
#     db.refresh(q)

#     # --- Intent handling logic ---
#     if "schedule" in text or "check vaccination" in text:
#         # Query the database for reminders for this specific user
#         reminders = db.query(models.Reminder).filter(models.Reminder.user_id == user.id).order_by(models.Reminder.due_date).all()
        
#         # [FIX] Indentation corrected in the if/else block below
#         if not reminders:
#             answer = "You have no upcoming vaccination reminders scheduled."
#         else:
#             # Format the reminders from the database into a nice list
#             schedule_list = [f"{r.due_date.strftime('%d %b %Y')} - {r.vaccine_name}" for r in reminders]
#             answer = "📅 Here are your scheduled vaccination reminders:\n" + "\n".join(schedule_list)

#     elif "reminder" in text or "set reminder" in text:
#         try:
#             parts = Body.split("for")[1].strip().split("on")
#             vaccine_name = parts[0].strip()
#             due_date_str = parts[1].strip()
#             due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
#             reminder = models.Reminder(user_id=user.id, vaccine_name=vaccine_name, due_date=due_date, status="pending")
#             db.add(reminder)
#             db.commit()
#             answer = f"✅ Reminder set for {vaccine_name} on {due_date_str}."
#         except Exception:
#             answer = "⚠️ Please use format: 'Set reminder for <vaccine> on YYYY-MM-DD'"

#     else:
#         # Fallback to RAG pipeline
#         try:
#             retrieved = retrieve_docs(Body, top_k=3)
#             rag_result = ask_medgemma(Body, retrieved)
#             answer = rag_result.get("answer", "⚠️ Sorry, I could not find an answer for that.")
#         except Exception as e:
#             print(f"RAG error: {e}")
#             answer = get_message("default", lang)

#     # Handle voice response request
#     if "voice" in text and twilio_client:
#         try:
#             # Assuming generate_tts_file is available and configured
#             filepath, media_url = generate_tts_file(answer, "en")
#             twilio_client.messages.create(
#                 from_=TWILIO_PHONE_NUMBER,
#                 to=From,
#                 body="Here’s your audio reply 🎧",
#                 media_url=[media_url]
#             )
#         except Exception as e:
#             # Use logging for better error tracking in production
#             logging.exception("Voice send failed")

#     # Save response and finalize
#     q.response_text = answer
#     q.status = "answered"
#     db.commit()
    
#     return answer


# @app.post("/webhook/twilio", response_class=PlainTextResponse)
# def twilio_webhook(
#     From: str = Form(...),
#     Body: str = Form(...),
#     To: str = Form(...),
#     db: Session = Depends(get_db)
# ):
#     # --- Detect channel (WhatsApp vs SMS) ---
#     if "whatsapp:" in From:
#         phone = From.replace("whatsapp:", "").strip()
#         channel = "whatsapp"
#     else:
#         phone = From.strip()
#         channel = "sms"

#     # --- Language setup (later: auto-detect or user profile) ---
#     lang = "hi"

#     # --- Find or create user ---
#     user = db.query(models.User).filter(models.User.phone == phone).first()
#     if not user:
#         user = models.User(phone=phone)
#         db.add(user)
#         db.commit()
#         db.refresh(user)

#     # --- Save incoming query ---
#     q = models.Query(
#         user_id=user.id,
#         channel=channel,
#         message_text=Body,
#         status="received"
#     )
#     db.add(q)
#     db.commit()
#     db.refresh(q)

#     # --- Intent handling ---
#     text = Body.lower().strip()

#     if "schedule" in text or "check vaccination" in text:
#         # Upcoming slots
#         answer = (
#             "📅 Upcoming vaccination slots:\n"
#             "20 Sep 2025 - COVID-19 @ Community Clinic\n"
#             "21 Sep 2025 - Hepatitis B @ City Hospital\n"
#             "25 Sep 2025 - Polio @ Primary Health Center"
#         )

#     elif "reminder" in text or "set reminder" in text:
#         try:
#             # Example: "Set reminder for Polio on 2025-09-25"
#             parts = Body.split("for")[1].strip().split("on")
#             vaccine_name = parts[0].strip()
#             due_date = parts[1].strip()

#             reminder = models.Reminder(
#                 user_id=user.id,
#                 vaccine_name=vaccine_name,
#                 due_date=due_date,
#                 status="pending"
#             )
#             db.add(reminder)
#             db.commit()
#             db.refresh(reminder)

#             answer = f"✅ Reminder set for {vaccine_name} on {due_date}."
#         except Exception as e:
#             print("Reminder parsing error:", e)  # Debug in Render logs
#             answer = "⚠️ Please use format: 'Set reminder for <vaccine> on YYYY-MM-DD'"

#     elif text == "1" and channel == "sms":
#         # Escalation option for SMS
#         answer = get_message("chw_followup", lang)

#     else:
#         # Fallback → RAG pipeline
#         try:
#             payload = RAGIn(question=Body, top_k=3)
#             rag_response = rag_query(payload, db)
#             answer = rag_response["answer"]
#         except Exception as e:
#             print("RAG error:", e)
#             answer = get_message("default", lang)


# if "voice" in Body.lower():  # user asks for voice response
#     try:
#         _, media_url = generate_tts_file(answer, "en")
#         if twilio_client:
#             twilio_client.messages.create(
#                 from_=TWILIO_NUMBER,
#                 to=From,
#                 body="Here’s your audio reply 🎧",
#                 media_url=[media_url]
#             )
#     except Exception as e:
#         logging.exception("Voice send failed")

    

#     # --- SMS-specific rule: keep short ---
#     if channel == "sms" and len(answer) > 160:
#         answer = "Query too long. CHW will follow up."

#     # --- Save response ---
#     q.response_text = answer
#     q.status = "answered"
#     db.commit()
#     return answer

# -----------------------------
# NEW: TTS routes
# -----------------------------

class TTSIn(BaseModel):
    text: str
    lang: str = "en"

@app.post("/tts")
def tts_generate(payload: TTSIn):
    try:
        _, url = generate_tts_file(payload.text, payload.lang)
        return {"status": "ok", "url": url}
    except Exception as e:
        logging.exception("TTS failed")
        raise HTTPException(status_code=500, detail=str(e))


class TTSSendIn(BaseModel):
    to_phone: str       # e.g. whatsapp:+91xxxx
    text: str
    lang: str = "en"
    caption: str = None

@app.post("/tts/send")
def tts_generate_and_send(payload: TTSSendIn):
    if not twilio_client:
        raise HTTPException(status_code=500, detail="Twilio not configured")

    if not BASE_URL:
        raise HTTPException(status_code=500, detail="BASE_URL must be set")

    try:
        _, media_url = generate_tts_file(payload.text, payload.lang)
    except Exception as e:
        logging.exception("TTS gen failed")
        raise HTTPException(status_code=500, detail=str(e))

    try:
        msg = twilio_client.messages.create(
            from_=TWILIO_PHONE_NUMBER,
            to=payload.to_phone,
            body=payload.caption or "",
            media_url=[media_url]
        )
        return {"status": "sent", "sid": msg.sid, "media_url": media_url}
    except Exception as e:
        logging.exception("Twilio send failed")
        raise HTTPException(status_code=500, detail=str(e))

    
    # # ---- Vaccination Chat Flow ----
    # def process_user_message(text: str, db: Session, user: models.User) -> str:
    # """Decide how to respond based on user message."""
    # text_lower = text.lower()

    # if "schedule" in text_lower or "check vaccination" in text_lower:
    #     schedule = [
    #         "20 Sep 2025 - COVID-19 @ Community Clinic",
    #         "21 Sep 2025 - Hepatitis B @ City Hospital",
    #         "25 Sep 2025 - Polio @ Primary Health Center"
    #     ]
    #     answer = "📅 Upcoming vaccination slots:\n" + "\n".join(schedule)

    # elif "reminder" in text_lower or "set reminder" in text_lower:
    #     try:
    #         # Example input: "Set reminder for Polio on 2025-09-25"
    #         parts = text.split("for")[1].strip().split("on")
    #         vaccine_name = parts[0].strip()
    #         due_date = parts[1].strip()

    #         reminder = models.Reminder(
    #             user_id=user.id,
    #             vaccine_name=vaccine_name,
    #             due_date=due_date,
    #             status="pending"
    #         )
    #         db.add(reminder)
    #         db.commit()
    #         db.refresh(reminder)

    #         answer = f"✅ Reminder set for {vaccine_name} on {due_date}."
    #     except Exception as e:
    #         print("Reminder parsing error:", e)  # Debug log
    #         answer = "⚠️ Please use format: 'Set reminder for <vaccine> on YYYY-MM-DD'"

    # else:
    #     # Fallback → RAG pipeline
    #     payload = RAGIn(question=text, top_k=3)
    #     rag_response = rag_query(payload, db)
    #     answer = rag_response["answer"]

    # return answer




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

@app.post("/rag-query")
def rag_query(payload: RAGIn, db: Session = Depends(get_db)):
    try:
        # Store query in DB (optional if already handled)
        user = db.query(models.User).filter(models.User.phone == "test_user").first()
        if not user:
            user = models.User(phone="test_user")
            db.add(user)
            db.commit()
            db.refresh(user)

        q = models.Query(
            user_id=user.id,
            channel="internal",
            message_text=payload.question,
            status="received"
        )
        db.add(q)
        db.commit()
        db.refresh(q)

        # Run RAG pipeline
        retrieved = retrieve_docs(payload.question, top_k=payload.top_k)
        rag_result = ask_medgemma(payload.question, retrieved)
        answer = rag_result.get("answer", "⚠️ Sorry, AI could not answer.")

        # Update DB with answer
        q.response_text = answer
        q.status = "answered"
        db.commit()

        return {
            "query_id": q.id,
            "question": payload.question,
            "retrieved": retrieved,
            "answer": answer,
            "status": q.status
        }

    except Exception as e:
        import logging
        logging.error(f"/rag-query failed: {e}")
        raise HTTPException(status_code=500, detail="RAG pipeline error")


# ---------------------------
# NEW: Vaccination Mock Endpoint
# ---------------------------
@app.get("/vaccination/mock")
def vaccination_schedule():
    return {
        "status": "ok",
        "schedule": [
            {"date": "2025-09-20", "vaccine": "COVID-19", "center": "Community Clinic"},
            {"date": "2025-09-21", "vaccine": "Hepatitis B", "center": "City Hospital"},
            {"date": "2025-09-25", "vaccine": "Polio", "center": "Primary Health Center"}
        ]
    }


# ---------------------------
# NEW: Create Reminder Endpoint
# ---------------------------
# @app.post("/vaccination/reminder")
# def set_reminder(payload: ReminderIn, db: Session = Depends(get_db)):
#     reminder = models.Reminder(
#         user_id=payload.user_id,
#         vaccine_name=payload.vaccine_name,
#         due_date=payload.due_date,
#         status="pending"
#     )
#     db.add(reminder)
#     db.commit()
#     db.refresh(reminder)
#     return {"id": reminder.id, "status": reminder.status}

#---------------------------
# # Day 5 Task Endpoints
# # ---------------------------
@app.get("/alerts")
def get_alerts(db: Session = Depends(get_db)):
    """Serves ingested alert data to the frontend."""
    try:
        alerts = db.query(models.Alert).order_by(models.Alert.created_at.desc()).all()
        return alerts
    except Exception as e:
        print(f"Database error in /alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts.")

@app.get("/education")
def get_education_topics():
    """Searches subdirectories for document files and returns a list of topics."""
    docs_path = os.path.join('knowledge_base_docs', 'documents')
    topics = set()  # Use a set to automatically handle duplicate filenames

    if not os.path.isdir(docs_path):
        raise HTTPException(status_code=404, detail="Education documents directory not found.")

    for root, dirs, files in os.walk(docs_path):
        for filename in files:
            if filename.endswith(('.pdf', '.txt', '.md')):
                topic_name = os.path.splitext(filename)[0]
                topic_name = topic_name.replace('_', ' ').replace('-', ' ').title()
                topics.add(topic_name)

    return {"topics": sorted(list(topics))}

#@app.post("/api/set-reminder")
@app.post("/reminder")
def set_reminder_from_frontend(payload: ReminderIn, db: Session = Depends(get_db)):
    """Sets a reminder from the frontend and sends a WhatsApp confirmation."""
    # Step 1: Save the reminder to the database (similar to your existing logic)
    reminder = models.Reminder(
        user_id=payload.user_id,
        vaccine_name=payload.vaccine_name,
        due_date=payload.due_date,
        status="pending"
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)

    # Step 2: Get the user's phone number
    user = db.query(models.User).filter(models.User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Step 3: Send the WhatsApp notification
    message = f"✅ Reminder Confirmed! We will remind you about your {payload.vaccine_name} vaccine scheduled for {payload.due_date}."
    send_whatsapp_message(user.phone, message)
    
    return {"status": "success", "message": "Reminder set and notification sent."}

# Add this temporary debug endpoint
@app.post("/debug-webhook")
async def debug_webhook(request: Request):
    """
    A temporary endpoint to catch and print all data from Twilio without validation.
    """
    print("\n--- DEBUGGING TWILIO REQUEST ---")

    # Print the form data we received
    form_data = await request.form()
    print("Received Form Data:")
    for key, value in form_data.items():
        print(f"  {key}: {value}")

    print("--- END DEBUGGING ---\n")

    # Send a simple response back to Twilio
    return PlainTextResponse("Debug data received. Check your server logs.")