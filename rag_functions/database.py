import hashlib
import os
from rag_functions.docs_preprocess import chunk_documents
from langchain_community.document_loaders import DirectoryLoader
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders.pdf import PyPDFLoader


def load_documents(data_folder):
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)

    loader = DirectoryLoader(data_folder, glob="*.pdf", loader_cls = PyPDFLoader)
    return loader.load()

def init_db(chunks, embeddings_model, folder_path):
    """
    Initialize Chroma with given chunks and embedding model, save it to the folder path,
    or load from the folder if it exists.
    """
    chroma_path = folder_path
    if os.path.exists(chroma_path):
        vectorstore = Chroma(persist_directory=chroma_path, embedding_function=embeddings_model)
    else:
        vectorstore = Chroma.from_documents(documents=chunks, embedding=embeddings_model, persist_directory=chroma_path)
    return vectorstore

def add_db_docs(vectorstore, data_path, embeddings_model):
    """
    Load documents from the folder, check if they exist in the vectorstore, and add them if they don't.
    """
    documents = load_documents(data_path)
    for document in documents:
        content = document.page_content
        embedding = embeddings_model.embed_query(content)
        result = vectorstore.similarity_search_by_vector(embedding, k=3)
        if not result:
            print("This content does not exist in vector database. Adding the content.")
            chunks = chunk_documents(content)
            vectorstore.add_texts(chunks)