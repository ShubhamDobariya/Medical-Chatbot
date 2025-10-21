from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from typing import List
from langchain_core.documents import Document


# Extract text from PDF files
def load_pdf_files(data):
    """Process all PDF files in a directory"""

    loader = DirectoryLoader(data, glob="**/*.pdf", loader_cls=PyPDFLoader)
    documents = loader.load()
    return documents


# Reduce metadata from Document
def filter_to_reduce_metadata_docs(docs: List[Document]) -> List[Document]:
    """
    Given a list of Document objects, return a new list of Document objects,
    containing only 'source' in metadata and the original 'page_content'.
    """
    reduce_docs: List[Document] = []
    for doc in docs:
        src = doc.metadata.get("source")
        reduce_docs.append(
            Document(page_content=doc.page_content, metadata={"source": src})
        )
    return reduce_docs


## Split the document into smaller chunks
def text_split(reduce_metadata_docs):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=20, length_function=len
    )
    texts_chunk = text_splitter.split_documents(reduce_metadata_docs)
    return texts_chunk


# Download the embedding from HuggingFace
def download_embeddings():
    """
    Download and Return the HuggingFace Embeddings Model.
    """

    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
    )

    return embeddings
