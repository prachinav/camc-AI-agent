from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_retrieval_chain, create_history_aware_retriever
from langchain.chains.combine_documents import create_stuff_documents_chain

def format_docs(docs):
    """Format retrieved documents for easy consumption."""
    return "\n\n".join(doc.page_content for doc in docs)

def setup_llm(model_name, base_url="http://127.0.0.1:11434"):
    """Initialize the chat model."""
    return ChatOllama(model=model_name, base_url=base_url, keep_alive=-1)

def setup_history_aware_retriever(llm, retriever):
    """Create a history-aware retriever to improve question context handling."""
    system_prompt = (
        "Reformulate the latest user question into a standalone query, "
        "taking into account previous chat history. "
        "Do NOT answer the question, only rephrase it if needed."
    )
    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [("system", system_prompt), MessagesPlaceholder("chat_history"), ("human", "{input}")]
    )
    return create_history_aware_retriever(llm, retriever, contextualize_q_prompt)

def setup_question_answer_chain(llm):
    """Create the RAG-based question-answering chain."""
    system_prompt = (
        "You are an AI assistant. Use the provided context to answer the question accurately. "
        "If the answer is unknown, tell the user to search the web. Keep responses concise.\n\n"
        "{context}"
    )
    qa_prompt = ChatPromptTemplate.from_messages(
        [("system", system_prompt), MessagesPlaceholder("chat_history"), ("human", "{input}")]
    )
    return create_stuff_documents_chain(llm, qa_prompt)

def setup_chain(model_name, retriever, base_url="http://127.0.0.1:11434"):
    """Create the full retrieval-augmented generation (RAG) pipeline."""
    llm = setup_llm(model_name, base_url)
    history_aware_retriever = setup_history_aware_retriever(llm, retriever)
    question_answer_chain = setup_question_answer_chain(llm)


    return create_retrieval_chain(history_aware_retriever, question_answer_chain)
