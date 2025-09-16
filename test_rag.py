# test_rag.py
from backend.rag_utils import retrieve_docs

# Vaccine-related query (should boost govt docs)
q1 = "When should children get the polio vaccine?"
print("---- Q1 Results ----")
for r in retrieve_docs(q1, top_k=5):
    print(r["rank"], r["score"], r["doc"])

# Non-vaccine query (normal FAISS ranking)
q2 = "What are symptoms of dengue?"
print("---- Q2 Results ----")
for r in retrieve_docs(q2, top_k=5):
    print(r["rank"], r["score"], r["doc"])
