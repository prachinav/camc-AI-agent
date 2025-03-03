import os
import uuid
from rag_functions.docs_preprocess import chunk_documents, call_embed_model, retrieve_docs, filter_think_tokens, structure_answer
from rag_functions.create_chain import setup_chain
from rag_functions.database import init_db, add_db_docs, load_documents
from rag_functions.chat_history import get_session_history, save_session_history
from langchain_core.runnables.history import RunnableWithMessageHistory

session_id = str(uuid.uuid4())

current_directory = os.path.dirname(os.path.abspath(__file__))
data_folder = os.path.join(current_directory, "data")
db_path = os.path.join(current_directory, "chroma_db")

docs = load_documents(data_folder)
chunks = chunk_documents(docs)

embed_model_name = "sentence-transformers/all-MiniLM-L12-v2"
embeddings_model = call_embed_model(embed_model_name)

vectorstore = init_db(chunks, embeddings_model, db_path)

add_db_docs(vectorstore, data_folder, embeddings_model)

chat_history = get_session_history(session_id)

while True:
    question = input("\n\nEnter your question (or type 'exit' to quit): ")
    if question.lower() == 'exit':
        break

    retriever = retrieve_docs(question, vectorstore, similar_docs_count = 5, see_content=False)
    rag_chain = setup_chain("deepseek-r1:1.5b", retriever)

    conversational_rag_chain = RunnableWithMessageHistory(
        rag_chain,
        lambda _: chat_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    )

    answer = ""
    for chunk in conversational_rag_chain.stream(
            {"input": question},
            config={
                "configurable": {"session_id": session_id}
            },
    ):

        if 'answer' in chunk:
            answer += chunk['answer']

    filtered = filter_think_tokens(answer)
    print(structure_answer(filtered), end="", flush=True)
    chat_history.add_user_message(question)
    chat_history.add_ai_message(answer)


save_session_history(session_id)