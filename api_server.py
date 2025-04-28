from flask import Flask, request, jsonify, render_template, redirect, url_for
import uuid
import os
import re
import json
import pandas as pd

from app import (
    is_location_query,
    handle_location_query,
    species_engine,
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

app = Flask(__name__)

data_folder = "data"
db_path = "chroma_db"
docs = load_documents(data_folder)
chunks = chunk_documents(docs)
embeddings_model = call_embed_model("sentence-transformers/all-MiniLM-L12-v2")
vectorstore = init_db(chunks, embeddings_model, db_path)

@app.route("/")
def index():
    new_session_id = str(uuid.uuid4())
    return redirect(url_for('chat_with_session', session_id=new_session_id))

@app.route("/chat/<session_id>")
def chat_with_session(session_id):
    session_file = os.path.join("rag_functions", "sessions", f"{session_id}.json")
    if not os.path.exists(session_file):
        with open(session_file, "w") as f:
            json.dump([], f)  # empty history
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

    trigger_phrase = "Which clones do you recommend to be planted in lagoa rica"
    if re.search(r"clones.*lagoa rica", user_input, re.IGNORECASE):
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

    if response_text is None and is_location_query(user_input):
        coords, error = handle_location_query(user_input)
        if error:
            response_text = error
        else:
            lat, lon = coords
            nearby_studies = species_engine.find_nearby_studies(lat, lon)
            if not nearby_studies:
                response_text = "No studies found near this location."
            else:
                recommendations = species_engine.recommend_species(nearby_studies)
                try:
                    location = geolocator.reverse(f"{lat},{lon}")
                    location_name = location.address.split(',')[0] if location else f"{lat:.4f}, {lon:.4f}"
                except:
                    location_name = f"{lat:.4f}, {lon:.4f}"

                prompt = (
                        f"User asked: {user_input}\n\n"
                        f"Location: {location_name}\n"
                        f"Studies analyzed: {len(nearby_studies)}\n"
                        f"Closest study: {nearby_studies[0]['distance_km']:.1f}km away\n\n"
                        "Scientific recommendations:\n" + "\n".join([
                    f"- {s['name']} ({s['code']}): Score {s['avg_score']:.1f}, "
                    f"Frost: {s['Frost Tolerance']}, Height: {s['Dominant Height Mean']}m"
                    for s in recommendations[:3]
                ])
                )
                response_text = None

    if response_text is None:
        prompt = user_input if 'prompt' not in locals() else prompt
        retriever = retrieve_docs(prompt, vectorstore, similar_docs_count=5, see_content=False)
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