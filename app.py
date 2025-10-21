from flask import Flask, render_template, jsonify, request
from langchain_community.vectorstores import Pinecone
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_core.runnables import RunnableMap
from src.helper import download_embeddings
from src.prompt import *
from dotenv import load_dotenv
import os

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
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", '"Context:\n{context}\n\nQuestion: {question}'),
    ]
)


rag_chain = (
    RunnableMap(
        {
            "question": lambda x: x,  # Pass user input as 'question'
            "context": lambda x: retriever.invoke(x),  # Pass user input to retriever
        }
    )
    | prompt
    | model
)

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("chat.html")


@app.route("/get", methods=["GET", "POST"])
def chat():
    msg = request.form["msg"]
    input = msg
    # print(input)
    response = rag_chain.invoke(input)
    # print("Response :", response.content)
    return response.content


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)
