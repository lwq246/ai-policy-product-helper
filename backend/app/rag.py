import time, os, math, json, hashlib
from typing import List, Dict, Tuple
import numpy as np
from .settings import settings
from .ingest import chunk_text, doc_hash
from qdrant_client import QdrantClient, models as qm
import uuid  # Add this at the top
from sentence_transformers import SentenceTransformer
# ---- Simple local embedder (deterministic) ----
def _tokenize(s: str) -> List[str]:
    return [t.lower() for t in s.split()]

class LocalEmbedder:
    def __init__(self, dim: int = 384):
        self.dim = dim
        # This downloads a tiny (80MB) AI model that runs locally on your CPU
        # It understands English meanings and synonyms
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def embed(self, text: str) -> np.ndarray:
        # This turns the MEANING of the text into math
        embedding = self.model.encode(text)
        return embedding.astype("float32")

# ---- Vector store abstraction ----
class InMemoryStore:
    def __init__(self, dim: int = 384):
        self.dim = dim
        self.vecs: List[np.ndarray] = []
        self.meta: List[Dict] = []
        self._hashes = set()

    def upsert(self, vectors: List[np.ndarray], metadatas: List[Dict]):
        for v, m in zip(vectors, metadatas):
            h = m.get("hash")
            if h and h in self._hashes:
                continue
            self.vecs.append(v.astype("float32"))
            self.meta.append(m)
            if h:
                self._hashes.add(h)

    def search(self, query: np.ndarray, k: int = 4) -> List[Tuple[float, Dict]]:
        if not self.vecs:
            return []
        A = np.vstack(self.vecs)  # [N, d]
        q = query.reshape(1, -1)  # [1, d]
        # cosine similarity
        sims = (A @ q.T).ravel() / (np.linalg.norm(A, axis=1) * (np.linalg.norm(q) + 1e-9) + 1e-9)
        idx = np.argsort(-sims)[:k]
        return [(float(sims[i]), self.meta[i]) for i in idx]

class QdrantStore:
    def __init__(self, collection: str, dim: int = 384):
        self.client = QdrantClient(url="http://qdrant:6333", timeout=10.0)
        self.collection = collection
        self.dim = dim
        self._ensure_collection()
        

    def _ensure_collection(self):
        try:
            self.client.get_collection(self.collection)
        except Exception:
            self.client.recreate_collection(
                collection_name=self.collection,
                vectors_config=qm.VectorParams(size=self.dim, distance=qm.Distance.COSINE)
            )

    def upsert(self, vectors: List[np.ndarray], metadatas: List[Dict]):
        points = []
        for i, (v, m) in enumerate(zip(vectors, metadatas)):
            points.append(qm.PointStruct(id=m.get("id") or m.get("hash") or i, vector=v.tolist(), payload=m))
        self.client.upsert(collection_name=self.collection, points=points)

    def search(self, query: np.ndarray, k: int = 4) -> List[Tuple[float, Dict]]:
        res = self.client.search(
            collection_name=self.collection,
            query_vector=query.tolist(),
            limit=k,
            with_payload=True
        )
        out = []
        for r in res:
            out.append((float(r.score), dict(r.payload)))
        return out

# ---- LLM provider ----
class StubLLM:
    def generate(self, query: str, contexts: List[Dict]) -> str:
        lines = [f"Answer (stub): Based on the following sources:"]
        for c in contexts:
            sec = c.get("section") or "Section"
            lines.append(f"- {c.get('title')} — {sec}")
        lines.append("Summary:")
        # naive summary of top contexts
        joined = " ".join([c.get("text", "") for c in contexts])
        lines.append(joined[:600] + ("..." if len(joined) > 600 else ""))
        return "\n".join(lines)

class OpenRouterLLM:
    def __init__(self, api_key: str, model: str = "openai/gpt-4o-mini"):
        from openai import OpenAI
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        self.model = model

    def generate(self, query: str, contexts: List[Dict]) -> str:
        prompt = f"You are a helpful company policy assistant. Cite sources by title and section when relevant.\nQuestion: {query}\nSources:\n"
        for c in contexts:
            prompt += f"- {c.get('title')} | {c.get('section')}\n{c.get('text')[:600]}\n---\n"
        prompt += "Write a concise, accurate answer grounded in the sources. If unsure, say so."
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role":"user","content":prompt}],
            temperature=0.1,
             max_tokens=500
        )
        return resp.choices[0].message.content

# ---- RAG Orchestrator & Metrics ----
class Metrics:
    def __init__(self):
        self.t_retrieval = []
        self.t_generation = []

    def add_retrieval(self, ms: float):
        self.t_retrieval.append(ms)

    def add_generation(self, ms: float):
        self.t_generation.append(ms)

    def summary(self) -> Dict:
        avg_r = sum(self.t_retrieval)/len(self.t_retrieval) if self.t_retrieval else 0.0
        avg_g = sum(self.t_generation)/len(self.t_generation) if self.t_generation else 0.0
        return {
            "avg_retrieval_latency_ms": round(avg_r, 2),
            "avg_generation_latency_ms": round(avg_g, 2),
        }

class RAGEngine:
    def __init__(self):
        self.embedder = LocalEmbedder(dim=384)

        # 1. INITIALIZE THE STORE (This must happen first!)
        if settings.vector_store == "qdrant":
            # This calls the QdrantStore class which has your retry loop
            self.store = QdrantStore(collection=settings.collection_name, dim=384)
        else:
            self.store = InMemoryStore(dim=384)

        # 2. INITIALIZE OTHER VARIABLES
        self.metrics = Metrics()
        self._doc_titles = set()
        self._chunk_count = 0

        # 3. SYNC PERSISTENCE (Optional check for existing data)
        if settings.vector_store == "qdrant":
            try:
                collection_info = self.store.client.get_collection(settings.collection_name)
                self._chunk_count = collection_info.points_count
                print(f"--- SUCCESS: Found {self._chunk_count} existing chunks in Qdrant ---")
            except Exception as e:
                print(f"--- NOTE: Collection empty or new: {e} ---")

        # 4. LLM SELECTION
        if settings.llm_provider == "openrouter" and settings.openrouter_api_key:
            self.llm = OpenRouterLLM(
                api_key=settings.openrouter_api_key,
                model=settings.llm_model,
            )
            self.llm_name = f"openrouter:{settings.llm_model}"
        else:
            self.llm = StubLLM()
            self.llm_name = "stub"

    def ingest_chunks(self, chunks: List[Dict]) -> Tuple[int, int]:
        vectors = []
        metas = []
        doc_titles_before = set(self._doc_titles)

        for ch in chunks:
            # 1. Identify the different versions of the text
            clean_body = ch["text"]                  # The one without headers

            # --- THE RICH EMBEDDING INPUT ---
            # We combine Title, Section, and Full Text into the math signal.
            # This makes it almost impossible for Qdrant to miss the right chunk.
            rich_signal = f"File: {ch['title']} | Section: {ch['section']} | Content: {clean_body}"
            
            # 2. Math Signal (Extreme Accuracy)
            v = self.embedder.embed(rich_signal)           

            # 3. Create unique deterministic ID for Qdrant
            h = doc_hash(clean_body)
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, h))
            
            # 4. Database Storage (Clean Payload)
            # We only store the 'clean_body' so the AI and User see professional text
            meta = {
                "id": point_id,
                "hash": h,
                "title": ch["title"],
                "section": ch["section"],
                "text": clean_body 
            }
            
            vectors.append(v)
            metas.append(meta)
            self._doc_titles.add(ch["title"])
            self._chunk_count += 1
        
        # Send everything to the database
        self.store.upsert(vectors, metas)
        
        new_docs_count = len(self._doc_titles) - len(doc_titles_before)
        return (new_docs_count, len(metas))
        # vectors = []
        # metas = []
        # doc_titles_before = set(self._doc_titles)

        # for ch in chunks:
        #     # The raw text from ingest.py (includes the ## header)
        #     full_text_chunk = ch["text"]
            
        #     # --- LOGIC TO SEPARATE HEADER FROM BODY ---
        #     lines = full_text_chunk.splitlines()
        #     # If there's more than one line, the first is the header, the rest is the clean body
        #     if len(lines) > 1:
        #         clean_body = "\n".join(lines[1:]).strip()
        #     else:
        #         clean_body = full_text_chunk # Fallback if no body exists
                
        #     # 1. Create unique ID
        #     h = doc_hash(full_text_chunk)
        #     point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, h))

        #     # 2. THE EMBEDDING (Uses the FULL content 'p' + Metadata for high accuracy)
        #     v = self.embedder.embed(full_text_chunk)

        #     # 3. THE PAYLOAD (Stores ONLY the clean body text)
        #     meta = {
        #         "title": ch["title"],
        #         "section": ch["section"],
        #         "text": clean_body, # <--- Clean text for the UI and AI reading
        #         "hash": h,
        #         "id": point_id
        #     }
            
        #     vectors.append(v)
        #     metas.append(meta)
        #     self._doc_titles.add(ch["title"])
        #     self._chunk_count += 1
        
        # self.store.upsert(vectors, metas)
        # new_docs_count = len(self._doc_titles) - len(doc_titles_before)
        # return (new_docs_count, len(metas))

    def retrieve(self, query: str, k: int = 4) -> List[Dict]:
        t0 = time.time()
        qv = self.embedder.embed(query)
        results = self.store.search(qv, k=k)
        self.metrics.add_retrieval((time.time()-t0)*1000.0)
        return [meta for score, meta in results]

    def generate(self, query: str, contexts: List[Dict]) -> str:
        t0 = time.time()
        answer = self.llm.generate(query, contexts)
        self.metrics.add_generation((time.time()-t0)*1000.0)
        return answer

    def stats(self) -> Dict:
        m = self.metrics.summary()
        
        # Ask Qdrant for the REAL count right now
        actual_chunks = 0
        if settings.vector_store == "qdrant":
            try:
                info = self.store.client.get_collection(self.store.collection)
                actual_chunks = info.points_count
            except:
                actual_chunks = self._chunk_count # fallback
        else:
            actual_chunks = self._chunk_count

        return {
            "total_docs": len(self._doc_titles), # This will still reset unless you scroll Qdrant
            "total_chunks": actual_chunks,      # This will now show the real DB count!
            "embedding_model": settings.embedding_model,
            "llm_model": self.llm_name,
            **m
        }

# ---- Helpers ----
def build_chunks_from_docs(docs: List[Dict], chunk_size: int, overlap: int) -> List[Dict]:
    out = []
    for d in docs:
        # For Markdown policy documents, the section splitting we did in ingest.py 
        # is already the perfect "chunk". We don't need to arbitrarily split by words 
        # anymore because it destroys the clean Markdown structure!
        
        # We simply pass the beautifully structured docs straight to the engine.
        out.append({
            "title": d["title"], 
            "section": d["section"], 
            "text": d["text"]           # The clean body for the database
        })
    return out
