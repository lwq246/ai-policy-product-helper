# AI Policy & Product Helper (RAG)

A production-ready, local-first Retrieval-Augmented Generation (RAG) application. This system enables users to query company policies and product catalogs with high precision, offering verified citations and a polished user interface.

## 🚀 Quick Start (One Command)

1.  **Configure Environment:** Copy the example environment file and add your `OPENROUTER_API_KEY`.
    ```bash
    cp .env.example .env
    ```
2.  **Run with Docker Compose:**
    ```bash
    docker compose up --build
    ```
3.  **Access the Application:**
    - **Frontend UI:** [http://localhost:3000](http://localhost:3000)
    - **Backend API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
    - **Qdrant Dashboard:** [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

---

## 🏗️ Architecture

The system follows a decoupled, containerized architecture designed for local-first data privacy and cloud-based reasoning:

```text
[ User Browser (Next.js) ] <----> [ FastAPI Backend ] <----> [ Qdrant Vector DB ]
                                         |
                                  [ OpenRouter AI ]
```

## 🛠️ Key Engineering Decisions & Challenges

During development, I refactored the skeleton starter pack to resolve critical infrastructure bugs and optimize the RAG pipeline:

- **Decoupled Embedding Strategy:** I optimized retrieval accuracy by generating vectors from a "Rich Signal" string (Document Title + Section + Content) to maximize semantic weight. However, I maintained a **"Clean Body"** storage strategy in the database payload. This ensures the AI finds the correct data with high confidence while the UI remains professional and non-redundant.
- **Deterministic Data Lifecycle (UUID5):** To satisfy Qdrant's strict schema requirements and ensure data integrity, I implemented **UUID5 mapping** derived from content hashes. This makes the ingestion process **Idempotent**—re-running ingestion updates existing points instead of creating duplicates.
- **Semantic Embedding Upgrade:** I replaced the placeholder hash-based embedding function with a state-of-the-art transformer model (`all-MiniLM-L6-v2`). This enables true **Semantic Search**, allowing the system to understand synonyms and context (e.g., matching "broken" with "defective") rather than relying on simple keyword or hash matching.
- **UX & Display Filtering:** I implemented a custom sanitization filter in the React frontend to strip technical Markdown artifacts (`#`, `##`) from citation views. This provides a clean, "quote-style" experience for the user while preserving the structural headers necessary for the AI's internal reasoning.
- **Startup State Hydration:** The backend performs a handshake with Qdrant upon boot to hydrate system metrics. This ensures that document counts and system status are accurate immediately upon restart, fulfilling the **"Local-First"** persistence requirement.

## 🔄 LLM Implementation & Changes

As per the requirement to use a real LLM for the demo, the following changes were implemented:

- **Provider Switch:** Successfully transitioned from the `stub` provider to `openrouter` by configuring environment variables and initializing the `OpenRouterLLM` class.
- **Cost & Budget Control:** Added a `max_tokens=500` limit to the OpenRouter completion call. This ensures the system remains within credit limits while providing concise, actionable answers.

## 🧪 Testing & Validation

The API logic and RAG pipeline are validated using `pytest` within the containerized environment.

**To run the test suite:**

```bash
docker compose run --rm -e PYTHONPATH=. backend pytest
```

**Test Results**

- **test_health**: PASSED  
  _Backend reachability verified._

- **test_ingest_and_ask**: PASSED  
  _End-to-end data flow and AI response verified._

## 📊 Performance Metrics

As seen in the Admin Panel, the system provides real-time observability:

- **Retrieval Latency:** ~21ms (Highly optimized via local Qdrant vector indexing).
- **Generation Latency:** ~3.2s (Standard round-trip latency for cloud-based LLM reasoning).
- **Data Density:** Documents are intelligently chunked based on Markdown headers to maintain semantic focus and prevent context fragmentation.

## 📈 Future Roadmap

- **Semantic Reranking**  
  Integrate a Cross-Encoder to filter out "semantic noise" and improve precision for queries where keywords overlap across different policies.

- **Token Streaming**  
  Refactor the API to support Server-Sent Events (SSE) for real-time AI typing effects in the UI, improving perceived performance.
