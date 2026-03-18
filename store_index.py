from dotenv import load_dotenv
import os
from src.helper import (
    load_pdf_files,
    filter_to_reduce_metadata_docs,
    text_split,
    download_embeddings,
)
from pinecone import Pinecone
from pinecone import ServerlessSpec

from langchain_community.vectorstores import Pinecone as LC_Pinecone


load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
os.environ["GROQ_API_KEY"] = GROQ_API_KEY


extracted_data = load_pdf_files(data="./data")
filter_data = filter_to_reduce_metadata_docs(extracted_data)
text_chunks = text_split(filter_data)


embeddings = download_embeddings()


pinecone_api_key = PINECONE_API_KEY
pc = Pinecone(api_key=pinecone_api_key)


index_name = "medical-chatbot"

existing_indexes = [index.name for index in pc.list_indexes()]
if index_name not in existing_indexes:
    pc.create_index(
        name=index_name,
        dimension=384,  # Dimension of the embedding
        metric="cosine",  # Cosine Similarity
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )

index = pc.Index(index_name)


docsearch = LC_Pinecone.from_documents(
    index_name=index_name, embedding=embeddings, documents=text_chunks
)
