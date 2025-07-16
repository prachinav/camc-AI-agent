import csv

import requests
from flask import Flask, request, jsonify, render_template, redirect, url_for
import uuid
import os
import re
import json
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

from app import (
    is_location_query,
    handle_location_query,
    geolocator,
    retrieve_docs,
    setup_chain,
    get_session_history,
    save_session_history,
    init_db,
    load_documents,
    chunk_documents,
    call_embed_model,
    generate_lagoa_rica_map
)
from langchain_core.runnables.history import RunnableWithMessageHistory

from species_data_handler import get_species_for_location

app = Flask(__name__)
data_folder = "data"
db_path = "chroma_db"
docs = load_documents(data_folder)
chunks = chunk_documents(docs)
embeddings_model = call_embed_model("sentence-transformers/all-MiniLM-L12-v2")
vectorstore = init_db(chunks, embeddings_model, db_path)

species_code_to_name = {}

with open('data/species_metadata.csv', 'r') as f:
    reader = csv.reader(f)
    for row in reader:
        scientific_name = row[0]
        species_code = row[1]
        species_code_to_name[species_code] = scientific_name

#************************************************************************
def is_species_query(query):
    keywords = ["species", "clone", "plant", "forest", "recommend", "region", "genetic", "plantation"]
    query_lower = query.lower()
    return any(word in query_lower for word in keywords)

def chat_with_ollama(prompt):
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3", "prompt": prompt},
            stream=True
        )

        full_text = ""

        for line in response.iter_lines():
            if line:
                data = json.loads(line.decode('utf-8'))
                if 'response' in data:
                    full_text += data['response']

        return full_text if full_text else "I'm unable to answer right now."

    except Exception as e:
        print(f"Error connecting to ChatOllama: {e}")
        return "Error connecting to ChatOllama."

def map_species_codes_to_names(species_codes):
    return [species_code_to_name.get(code, code) for code in species_codes]

def build_full_prompt(chat_history, user_input):
    history_text = ""
    for message in chat_history:
        role = message.get('role') if isinstance(message, dict) else message[0]
        content = message.get('content') if isinstance(message, dict) else message[1]
        if role == 'human':
            history_text += f"User: {content}\n"
        elif role == 'ai':
            history_text += f"AI: {content}\n"
    history_text += f"User: {user_input}\nAI:"
    return history_text


#******************************************************************************
@app.route("/")
def index():
    new_session_id = str(uuid.uuid4())
    return redirect(url_for('chat_with_session', session_id=new_session_id))

@app.route("/chat/<session_id>")
def chat_with_session(session_id):
    session_file = os.path.join("rag_functions", "sessions", f"{session_id}.json")
    if not os.path.exists(session_file):
        with open(session_file, "w") as f:
            json.dump([], f)  # for empty history
    return render_template("chat.html", session_id=session_id)

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message")
    session_id = request.args.get("session_id")
    session_file = os.path.join("rag_functions", "sessions", f"{session_id}.json")

    if not session_id:
        return jsonify({"error": "Missing session_id"}), 400

    chat_history = get_session_history(session_id)
    response_text = None

    if not is_species_query(user_input):
        full_prompt = build_full_prompt(chat_history, user_input)
        response = chat_with_ollama(full_prompt)

    elif re.search(r"clones.*lagoa rica", user_input, re.IGNORECASE):
        df = pd.read_excel("data/productivity.xlsx")
        clone_scores = df.drop(columns=["longitude", "latitude", "project"]).iloc[0].to_dict()
        top_clones = sorted(clone_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        recommendation = "\n".join(
            [f"{i+1}. {clone} — MAI6 {score:.2f}" for i, (clone, score) in enumerate(top_clones)]
        )

        map_url = generate_lagoa_rica_map(clone_scores)

        response_text = (
                "<strong>Top Recommended Clones for Lagoa Rica:</strong><br><br>"
                + recommendation.replace("\n", "<br>") +
                f"<br><br><img class='preview-img' src='{map_url}' alt='Map Preview'>" +
                "<br><br><strong>Climatic Information:</strong><br>"
                "Located in Cluster 2<br>"
                "Water Deficit Historic: 66 mm<br>"
                "Precipitation Historic: 1343 mm<br>"
                "Water Deficit Forecast: 153 mm"
        )

    elif is_location_query(user_input):
        coords, error = handle_location_query(user_input)
        if error:
            response_text = error
        else:
            lat, lon = coords
            try:
                species_list = get_species_for_location(lat, lon)
                print("Species List:" + species_list)
            except Exception as e:
                response_text = f"Database error: {str(e)}"
                species_list = []

            if not species_list:
                response_text = "No species found near this location."
            else:
                try:
                    location = geolocator.reverse(f"{lat},{lon}")
                    location_name = location.address.split(',')[0] if location else f"{lat:.4f}, {lon:.4f}"
                except:
                    location_name = f"{lat:.4f}, {lon:.4f}"

                prompt = (
                        f"User asked: {user_input}\n\n"
                        f"Location: {location_name}\n"
                        f"Species found: {len(species_list)}\n\n"
                        f"Species List:\n" + "\n".join([
                    f"- {s}" for s in species_list[:5]
                ])
                )

                print(prompt)
                response_text = None

    if response_text is None:
        prompt = user_input if 'prompt' not in locals() else prompt
        retriever = retrieve_docs(prompt, vectorstore, similar_docs_count=5, see_content=False)
        retrieved_docs = retriever.invoke(prompt)

        if not retrieved_docs or len(retrieved_docs) == 0:
            full_prompt = build_full_prompt(chat_history, user_input)
            response_text = chat_with_ollama(full_prompt)
        else:
            rag_chain = setup_chain("llama3.2:1b", retriever)

            conversational_rag_chain = RunnableWithMessageHistory(
                rag_chain,
                lambda _: chat_history,
                input_messages_key="input",
                history_messages_key="chat_history",
                output_messages_key="answer"
            )

            final_answer = ""
            for chunk in conversational_rag_chain.stream(
                    {"input": prompt},
                    config={"configurable": {"session_id": session_id}}
            ):
                if 'answer' in chunk:
                    final_answer += chunk["answer"]
            response_text = final_answer

    session_history = []
    if os.path.exists(session_file):
        with open(session_file) as f:
            session_history = json.load(f)

    session_history.extend([
        {"role": "human", "content": user_input},
        {"role": "ai", "content": response_text}
    ])
    with open(session_file, "w") as f:
        json.dump(session_history, f, indent=2)

    save_session_history(session_id)

    return jsonify({"response": response_text})


@app.route("/history/<session_id>")
def get_history(session_id):
    session_path = os.path.join("rag_functions", "sessions", f"{session_id}.json")
    if not os.path.exists(session_path):
        return jsonify([])
    with open(session_path, "r") as f:
        return jsonify(json.load(f))

@app.route("/sessions")
def list_sessions():
    session_path = os.path.join("rag_functions", "sessions")
    os.makedirs(session_path, exist_ok=True)

    sessions = sorted(
        [f for f in os.listdir(session_path) if f.endswith(".json")],
        key=lambda f: os.path.getmtime(os.path.join(session_path, f)),
        reverse=True
    )
    return jsonify([f.replace(".json", "") for f in sessions])

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5050)