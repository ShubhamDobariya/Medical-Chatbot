from flask import Flask, render_template, jsonify, request
from langchain_community.vectorstores import Pinecone
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from src.helper import download_embeddings
from src.prompt import *
from dotenv import load_dotenv
import os
import uuid

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
os.environ["GROQ_API_KEY"] = GROQ_API_KEY

embeddings = download_embeddings()

index_name = "medical-chatbot"

docsearch = Pinecone.from_existing_index(index_name=index_name, embedding=embeddings)

retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k": 3})

model = ChatGroq(model="groq/compound")

# PROMPT — added MessagesPlaceholder for memory

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "Context:\n{context}\n\nQuestion: {question}"),
    ]
)


# SESSION STORE

store = {}


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


# CONDENSE CHAIN — rewrites follow-up questions using history

condense_prompt = ChatPromptTemplate.from_messages(
    [
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}"),
        (
            "human",
            "Given the above conversation, rewrite the follow-up question as a standalone question that includes all necessary context. Just return the rewritten question, nothing else.",
        ),
    ]
)

condense_chain = condense_prompt | model | StrOutputParser()


def get_standalone_question(x):
    if x.get("chat_history"):
        return condense_chain.invoke(x)
    return x["question"]


# RAG CHAIN

rag_core_chain = (
    RunnablePassthrough.assign(standalone_question=get_standalone_question)
    | RunnablePassthrough.assign(
        context=lambda x: retriever.invoke(x["standalone_question"])
    )
    | prompt
    | model
)


# WRAP WITH MEMORY

rag_chain_with_memory = RunnableWithMessageHistory(
    rag_core_chain,
    get_session_history,
    input_messages_key="question",
    history_messages_key="chat_history",
)

app = Flask(__name__)
app.secret_key = os.urandom(24)


@app.route("/")
def index():
    return render_template("chat.html")


@app.route("/get", methods=["GET", "POST"])
def chat():
    msg = request.form["msg"]

    from flask import session

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

        #  Rate limit error
        if "rate_limit_exceeded" in error_msg or "429" in error_msg:
            return "⚠️ I'm receiving too many requests right now. Please wait a few seconds and try again."

        #  API key error
        elif "401" in error_msg or "invalid_api_key" in error_msg:
            return "⚠️ API key is invalid or missing. Please check your configuration."

        #  Connection error
        elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
            return "⚠️ Connection error. Please check your internet and try again."

        #  Any other error
        else:
            return "⚠️ Something went wrong. Please try again in a moment."


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # 👈 Railway sets PORT automatically
    app.run(host="0.0.0.0", port=port, debug=False)
