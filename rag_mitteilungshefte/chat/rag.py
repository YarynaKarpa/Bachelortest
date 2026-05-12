import chromadb
from sentence_transformers import SentenceTransformer
from groq import Groq
from django.conf import settings

_engine = None

class RAGEngine:
    def __init__(self):
        self.chroma = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
        self.collection = self.chroma.get_or_create_collection(
            name="mitteilungshefte",
            metadata={"hnsw:space": "cosine"}
        )
        print("⏳ Lade Embedding-Modell...")
        self.embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        self.llm = Groq(api_key=settings.GROQ_API_KEY)
        print("✅ RAG Engine bereit.")

    def ingest(self, docs):
        existing = set(self.collection.get()["ids"])
        new_docs = [d for d in docs if d["id"] not in existing]
        if not new_docs:
            print("Alle Dokumente bereits vorhanden.")
            return 0
        texts = [d["text"] for d in new_docs]
        embeddings = self.embedder.encode(texts, show_progress_bar=True).tolist()
        self.collection.add(
            documents=texts,
            embeddings=embeddings,
            ids=[d["id"] for d in new_docs],
            metadatas=[d.get("metadata", {}) for d in new_docs],
        )
        print(f"✅ {len(new_docs)} Dokumente eingefügt.")
        return len(new_docs)

    def ask(self, question):
        q_emb = self.embedder.encode([question]).tolist()
        results = self.collection.query(
            query_embeddings=q_emb,
            n_results=min(3, self.collection.count()),
            include=["documents", "metadatas"],
        )
        chunks = results["documents"][0]
        metas = results["metadatas"][0]

        context = "\n\n---\n\n".join(
            f"[Heft {m.get('heft','?')}, Thema: {m.get('thema','?')}]\n{c}"
            for c, m in zip(chunks, metas)
        )

        response = self.llm.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Du bist ein hilfreicher Assistent für die Mitteilungshefte "
                        "der Altnürnberger Landschaft e.V. Beantworte Fragen nur auf "
                        "Basis des Kontexts. Antworte auf Deutsch. Wenn die Information "
                        "nicht im Kontext steht, sage das ehrlich."
                    )
                },
                {
                    "role": "user",
                    "content": f"Kontext:\n{context}\n\nFrage: {question}"
                }
            ]
        )
        return {
            "answer": response.choices[0].message.content,
            "sources": [{"heft": m.get("heft","?"), "thema": m.get("thema","?")}
                        for m in metas],
        }

    def count(self):
        return self.collection.count()


def get_engine():
    global _engine
    if _engine is None:
        _engine = RAGEngine()
    return _engine