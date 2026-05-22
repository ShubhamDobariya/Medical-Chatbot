# store_index.py
from src.helper import download_embeddings
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
from typing import List
from uuid import uuid4
import os

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY


# Step 1: Load PDF
def load_pdf_files(data):
    loader = DirectoryLoader(data, glob="**/*.pdf", loader_cls=PyPDFLoader)
    return loader.load()


# Step 2: Enrich Metadata
def filter_metadata(docs: List[Document]) -> List[Document]:
    result = []
    for doc in docs:
        if not doc.page_content.strip():
            continue
        result.append(
            Document(
                page_content=doc.page_content,
                metadata={
                    "source": doc.metadata.get("source", "Unknown"),
                    "page": doc.metadata.get("page", 0) + 1,
                    "book": "Gale Encyclopedia of Medicine 2nd Edition",
                },
            )
        )
    return result


# Step 3: Hybrid Chunking
def text_split_hybrid(docs, embedding_model):
    print("Running SemanticChunker...")
    semantic_splitter = SemanticChunker(
        embeddings=embedding_model,
        breakpoint_threshold_type="percentile",
        breakpoint_threshold_amount=85,
    )
    semantic_chunks = semantic_splitter.split_documents(docs)
    print(f"Semantic chunks: {len(semantic_chunks)}")

    safety_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", ", ", " ", ""],
    )

    final_chunks = []
    for chunk in semantic_chunks:
        if len(chunk.page_content) > 1200:
            final_chunks.extend(safety_splitter.split_documents([chunk]))
        else:
            final_chunks.append(chunk)

    print(f"Final chunks: {len(final_chunks)}")
    return final_chunks


# Step 4: Store in Pinecone
def store_in_pinecone(chunks, embedding_model):
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index_name = "medical-chatbot"

    if not pc.has_index(index_name):
        print(f"Creating index '{index_name}'...")
        pc.create_index(
            name=index_name,
            dimension=384,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        print("Index created!")

    index = pc.Index(index_name)
    vector_store = PineconeVectorStore(index=index, embedding=embedding_model)

    print(f"Storing {len(chunks)} chunks in Pinecone...")
    uuids = [str(uuid4()) for _ in range(len(chunks))]
    vector_store.add_documents(documents=chunks, ids=uuids)
    print(f"Done! {len(chunks)} chunks stored.")
    print(f"Index stats: {index.describe_index_stats()}")


# Step 5: Main
if __name__ == "__main__":
    print("Step 1: Loading PDF...")
    extracted_data = load_pdf_files("data")

    print("Step 2: Filtering metadata...")
    clean_docs = filter_metadata(extracted_data)
    print(f"Clean docs: {len(clean_docs)}")

    print("Step 3: Loading embeddings...")
    embedding = download_embeddings()

    print("Step 4: Chunking documents...")
    texts_chunk = text_split_hybrid(clean_docs, embedding)

    print("Step 5: Storing in Pinecone...")
    store_in_pinecone(texts_chunk, embedding)

    print("\n Indexing complete! You can now run app.py")
