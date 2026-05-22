from flask import Flask, render_template, request, session
from langchain_pinecone import PineconeVectorStore
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.documents import Document
from pinecone import Pinecone
from sentence_transformers import CrossEncoder
from src.helper import download_embeddings
from src.prompt import system_prompt
from dotenv import load_dotenv
from typing import List
import os
import uuid

load_dotenv()


PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
os.environ["GROQ_API_KEY"] = GROQ_API_KEY


embeddings = download_embeddings()
index_name = "improved-medical-chatbot"

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(index_name)

docsearch = PineconeVectorStore(index=index, embedding=embeddings)


# MMR RETRIEVER
# fetch_k=20 candidates → return best 5 diverse docs

retriever = docsearch.as_retriever(
    search_type="mmr", search_kwargs={"k": 5, "fetch_k": 20, "lambda_mult": 0.7}
)

model = ChatGroq(model="groq/compound")

# CROSS-ENCODER RERANKER
# Reranks retrieved docs by actual relevance

reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


def rerank_documents(
    query: str, documents: List[Document], top_k: int = 3
) -> List[Document]:
    """
    Rerank retrieved documents using cross-encoder.
    Takes MMR results → returns top_k most relevant.
    """
    if not documents or len(documents) <= top_k:
        return documents

    pairs = [[query, doc.page_content] for doc in documents]
    scores = reranker.predict(pairs)

    ranked = sorted(zip(scores, documents), key=lambda x: x[0], reverse=True)
    return [doc for _, doc in ranked[:top_k]]


# QUERY EXPANSION
# Generates 3 medical variations of the query
# Retrieves + deduplicates + reranks


def expand_and_retrieve(query: str, top_k: int = 3) -> List[Document]:
    """
    Full retrieval pipeline:
    1. Expand query into 3 medical variations
    2. MMR retrieve for each variation
    3. Deduplicate
    4. Rerank → return top_k
    """
    expansion_prompt = f"""You are a medical search expert.
Generate exactly 3 different search queries for the following medical question.
Use different medical terminology, synonyms, and phrasings.
Return ONLY the 3 queries, one per line, no numbering, no extra text.

Original question: {query}"""

    try:
        response = model.invoke(expansion_prompt)
        variations = [
            q.strip() for q in response.content.strip().split("\n") if q.strip()
        ][:3]
    except Exception:
        variations = []

    all_queries = [query] + variations
    all_docs = []
    seen_content = set()

    for q in all_queries:
        try:
            docs = retriever.invoke(q)
            for doc in docs:
                content_key = doc.page_content[:100].strip()
                if content_key not in seen_content:
                    seen_content.add(content_key)
                    all_docs.append(doc)
        except Exception:
            pass

    return rerank_documents(query, all_docs, top_k=top_k)


# FORMAT CONTEXT WITH CITATIONS
# Adds page numbers to context for LLM reference


def format_context_with_sources(docs: List[Document]) -> str:
    """Format retrieved documents with page number citations."""
    if not docs:
        return "No relevant medical information found."

    formatted_parts = []
    for i, doc in enumerate(docs, 1):
        page = doc.metadata.get("page", "?")
        book = doc.metadata.get("book", "Gale Encyclopedia of Medicine")
        formatted_parts.append(
            f"[Reference {i} — {book}, Page {page}]\n" f"{doc.page_content}"
        )

    separator = "\n\n" + "─" * 40 + "\n\n"
    return "\n\n" + separator.join(formatted_parts)


prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        (
            "human",
            """Retrieved Medical Context:
{context}

─────────────────────────────────────
Question: {question}

Answer strictly from the context above.
Mention reference numbers and page numbers where applicable.
""",
        ),
    ]
)


# SESSION STORE

store = {}


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    """Get or create chat history for a session."""
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


# CONDENSE CHAIN
# Better prompt for resolving pronouns
condense_prompt = ChatPromptTemplate.from_messages(
    [
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}"),
        (
            "human",
            """Rewrite the follow-up question as a complete standalone
medical question using context from the conversation history.

Rules:
- Replace pronouns like "its", "it", "the condition" with the actual medical term
- If question already stands alone, return it unchanged
- Return ONLY the rewritten question, nothing else

Example:
  History: User asked about acne
  Follow-up: "What are its symptoms?"
  Rewritten: "What are the symptoms of acne?"
""",
        ),
    ]
)

condense_chain = condense_prompt | model | StrOutputParser()


def get_standalone_question(x: dict) -> str:
    """Rewrite follow-up questions using chat history."""
    if x.get("chat_history"):
        return condense_chain.invoke(x)
    return x["question"]


# FULL RAG CHAIN
# Step 1: Rewrite follow-up question
# Step 2: Query expansion + MMR + Reranking
# Step 3: Format context with citations
# Step 4: Prompt + LLM
# ============================================================
rag_core_chain = (
    RunnablePassthrough.assign(standalone_question=get_standalone_question)  # Step 1
    | RunnablePassthrough.assign(
        raw_docs=lambda x: expand_and_retrieve(  # Step 2
            x["standalone_question"], top_k=3
        )
    )
    | RunnablePassthrough.assign(
        context=lambda x: format_context_with_sources(x["raw_docs"])  # Step 3
    )
    | prompt  # Step 4a
    | model  # Step 4b
)


# WRAP WITH MEMORY

rag_chain_with_memory = RunnableWithMessageHistory(
    rag_core_chain,
    get_session_history,
    input_messages_key="question",
    history_messages_key="chat_history",
)


# FLASK APP
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))


@app.route("/")
def index():
    return render_template("chat.html")


@app.route("/get", methods=["GET", "POST"])
def chat():
    msg = request.form["msg"]

    # Create session ID if not exists
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())

    try:
        response = rag_chain_with_memory.invoke(
            {"question": msg},
            config={"configurable": {"session_id": session["session_id"]}},
        )
        return response.content

    except Exception as e:
        error_msg = str(e)

        if "rate_limit_exceeded" in error_msg or "429" in error_msg:
            return "⚠️ Too many requests. Please wait a few seconds and try again."

        elif "401" in error_msg or "invalid_api_key" in error_msg:
            return "⚠️ API key is invalid or missing. Please check your configuration."

        elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
            return "⚠️ Connection error. Please check your internet and try again."

        else:
            return f"⚠️ Something went wrong. Please try again in a moment."


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
