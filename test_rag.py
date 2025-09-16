# test_rag.py
# from backend.rag_utils import retrieve_docs

# # Vaccine-related query (should boost govt docs)
# q1 = "When should children get the polio vaccine?"
# print("---- Q1 Results ----")
# for r in retrieve_docs(q1, top_k=5):
#     print(r["rank"], r["score"], r["doc"])

# # Non-vaccine query (normal FAISS ranking)
# q2 = "What are symptoms of dengue?"
# print("---- Q2 Results ----")
# for r in retrieve_docs(q2, top_k=5):
#     print(r["rank"], r["score"], r["doc"])


# test_rag_answer.py
from backend.rag_utils import retrieve_docs, ask_medgemma

q1 = "When should children get the polio vaccine?"

# Step 1: retrieve relevant docs
retrieved = retrieve_docs(q1, top_k=3)

print("---- Retrieved Contexts ----")
for r in retrieved:
    print(f"Rank {r['rank']} | Doc: {r['doc']}")
    print(r['text'][:200], "...\n")  # just preview first 200 chars

# Step 2: ask MedGemma with retrieved chunks
response = ask_medgemma(q1, retrieved)
print("---- Final Answer ----")
print(response["answer"])
