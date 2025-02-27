import re

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema.document import Document

def call_embed_model(model_name):
    embeddings_model = HuggingFaceEmbeddings(model_name=model_name)
    return embeddings_model

def chunk_documents(docs: list[Document]):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000,
                                                   chunk_overlap=80)
    return text_splitter.split_documents(docs)

def retrieve_docs(question, vector_store, similar_docs_count, see_content:False):
    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": similar_docs_count})
    retrieved_docs = retriever.invoke(question)

    if see_content:
        for i in range(similar_docs_count):
            print(retrieved_docs[i].page_content)

    return retriever

def filter_think_tokens(text):
    """ Remove <think>...</think> tokens from the model's output. """
    filtered_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return filtered_text.strip()