---
title: Medical Chatbot
emoji: 🩺
colorFrom: red
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: RAG medical chatbot powered by Gale Encyclopedia of Medicine
---

# 🩺 Medical Chatbot — RAG over the Gale Encyclopedia of Medicine

An end-to-end **Retrieval-Augmented Generation (RAG)** chatbot that answers medical questions strictly from the **Gale Encyclopedia of Medicine (2nd Edition)**. Built with **LangChain**, **Pinecone**, **Groq LLM**, **HuggingFace embeddings**, and **Flask** — and deployed on **🤗 Hugging Face Spaces**.

The pipeline goes well beyond a vanilla RAG: it performs **query expansion**, **MMR retrieval**, **cross-encoder reranking**, **conversation memory**, and **page-level citations** — all wrapped behind a clean Flask chat UI.

---

## 🚀 Live Demo

👉 **Try it live on Hugging Face Spaces:** [https://huggingface.co/spaces/&lt;your-username&gt;/Medical-Chatbot](https://huggingface.co/spaces/)

---

## ✨ Features

- **Domain-grounded answers** — replies are restricted to retrieved medical context; never hallucinated.
- **Query Expansion** — every user question is rewritten into 3 medical variations to improve recall.
- **MMR Retrieval** — fetches 20 candidates and returns the 5 most diverse and relevant chunks.
- **Cross-Encoder Reranking** — `ms-marco-MiniLM-L-6-v2` reorders retrieved docs by true relevance.
- **Follow-up Resolution** — pronouns like "its", "it", "the condition" are rewritten using chat history.
- **Conversation Memory** — per-session chat history via Flask sessions + `RunnableWithMessageHistory`.
- **Page-level Citations** — every answer includes the reference book and page number.
- **Hybrid Chunking** — `SemanticChunker` (percentile breakpoints) + `RecursiveCharacterTextSplitter` safety net.
- **Production-ready** — Dockerfile + Gunicorn, deployed to Hugging Face Spaces.

---

## 🧠 Architecture

```
                       ┌────────────────────────────┐
   User Question  ───▶ │  Standalone Question       │  (condense follow-ups)
                       └─────────────┬──────────────┘
                                     │
                                     ▼
                       ┌────────────────────────────┐
                       │  Query Expansion (Groq)    │  3 medical variations
                       └─────────────┬──────────────┘
                                     │
                                     ▼
                       ┌────────────────────────────┐
                       │  Pinecone MMR Retriever    │  k=5, fetch_k=20
                       └─────────────┬──────────────┘
                                     │
                                     ▼
                       ┌────────────────────────────┐
                       │  Cross-Encoder Reranker    │  top-3 most relevant
                       └─────────────┬──────────────┘
                                     │
                                     ▼
                       ┌────────────────────────────┐
                       │  Prompt + Groq LLM         │  with citations
                       └─────────────┬──────────────┘
                                     │
                                     ▼
                              Final Answer
```

---

## 🛠️ Tech Stack

| Layer          | Technology                                                 |
| -------------- | ---------------------------------------------------------- |
| **LLM**        | Groq (`groq/compound`)                                     |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` (via HuggingFace) |
| **Reranker**   | `cross-encoder/ms-marco-MiniLM-L-6-v2`                     |
| **Vector DB**  | Pinecone (serverless, AWS `us-east-1`)                     |
| **Framework**  | LangChain + LangChain Experimental                         |
| **Chunking**   | SemanticChunker + RecursiveCharacterTextSplitter           |
| **Backend**    | Flask + Gunicorn                                           |
| **Frontend**   | HTML / CSS / JS (Jinja templates)                          |
| **Deployment** | 🤗 Hugging Face Spaces (Docker SDK)                        |

---

## 📂 Project Structure

```
Medical-Chatbot/
├── app.py                  # Flask app + full RAG chain with memory
├── store_index.py          # PDF ingestion → chunking → Pinecone upsert
├── src/
│   ├── helper.py           # Embedding model loader
│   └── prompt.py           # System prompt for the medical assistant
├── templates/
│   └── chat.html           # Chat UI
├── static/
│   ├── chat.css
│   ├── chat.js
│   └── images/
├── data/                   # (you provide) PDF medical references
├── requirements.txt
├── Dockerfile              # Used by HF Spaces to build the container
├── Procfile
├── setup.py
└── .env                    # Local API keys (not committed)
```

---

## 🚀 Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/Medical-Chatbot.git
cd Medical-Chatbot
```

### 2. Create a virtual environment

```bash
# Using conda
conda create -n medibot python=3.10 -y
conda activate medibot

# Or using venv
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
PINECONE_API_KEY="your_pinecone_api_key"
GROQ_API_KEY="your_groq_api_key"
HUGGINGFACEHUB_API_TOKEN="your_huggingface_token"
```

Get your keys from:

- **Pinecone** — https://app.pinecone.io
- **Groq** — https://console.groq.com
- **HuggingFace** — https://huggingface.co/settings/tokens

### 5. Add your medical reference PDFs

Place your PDF files (e.g., _Gale Encyclopedia of Medicine 2nd Edition_) inside a `data/` directory:

```
Medical-Chatbot/
└── data/
    └── gale_encyclopedia_of_medicine.pdf
```

### 6. Build the vector index (one-time)

```bash
python store_index.py
```

This will:

1. Load all PDFs in `data/`
2. Enrich metadata (page numbers, book name)
3. Semantically chunk the documents
4. Push embeddings to Pinecone

### 7. Run the chatbot

```bash
python app.py
```

Open your browser at **http://localhost:8080** 🎉

---

## 🤗 Deploy on Hugging Face Spaces

This project is configured to run directly on **Hugging Face Spaces** using the **Docker SDK**.

### 1. Create a new Space

Go to [huggingface.co/new-space](https://huggingface.co/new-space) and choose:

- **SDK:** `Docker`
- **Hardware:** CPU Basic (free tier works fine)
- **Visibility:** Public or Private

### 2. Push your code

```bash
git remote add space https://huggingface.co/spaces/<your-username>/Medical-Chatbot
git push space main
```

The Space will read the YAML frontmatter at the top of this `README.md` and automatically build the Docker image using the included `Dockerfile`.

### 3. Add your secrets

In your Space **Settings → Variables and secrets**, add:

| Name                       | Value                            |
| -------------------------- | -------------------------------- |
| `PINECONE_API_KEY`         | your Pinecone key                |
| `GROQ_API_KEY`             | your Groq key                    |
| `HUGGINGFACEHUB_API_TOKEN` | your HuggingFace token           |
| `SECRET_KEY`               | random string for Flask sessions |

### 4. Done!

Once the build finishes, your chatbot will be live at:
`https://huggingface.co/spaces/<your-username>/Medical-Chatbot`

> ℹ️ The Space exposes port **7860** (configured in the YAML frontmatter and in the `Dockerfile`).

---

## 🐳 Docker (alternative)

You can also build and run the container locally:

```bash
docker build -t medical-chatbot .
docker run -p 7860:7860 --env-file .env medical-chatbot
```

The app will be available at **http://localhost:7860**.

---

## 🧪 Example Questions

- "What is acne?"
- "What are the symptoms of diabetes?"
- "How is tuberculosis treated?"
- "What causes high blood pressure?" → follow up with "What are its symptoms?"

---

## ⚠️ Disclaimer

This chatbot is for **educational purposes only**. It is **not** a substitute for professional medical advice, diagnosis, or treatment. Always consult a qualified healthcare professional for medical concerns.

---

## 📜 License

This project is licensed under the terms of the [LICENSE](LICENSE) file included in the repository.
