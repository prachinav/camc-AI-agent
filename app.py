import os
import uuid
import re
import shutil
from PIL import Image, ImageDraw
from typing import Optional, Tuple
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

from rag_functions.docs_preprocess import chunk_documents, call_embed_model, retrieve_docs
from rag_functions.create_chain import setup_chain
from rag_functions.database import init_db, add_db_docs, load_documents
from rag_functions.chat_history import get_session_history, save_session_history
from langchain_core.runnables.history import RunnableWithMessageHistory
from species_data_handler import SpeciesLocationEngine

session_id = str(uuid.uuid4())

current_directory = os.path.dirname(os.path.abspath(__file__))
data_folder = os.path.join(current_directory, "data")
db_path = os.path.join(current_directory, "chroma_db")

species_engine = SpeciesLocationEngine()
geolocator = Nominatim(user_agent="species_locator_app")

def is_location_query(question: str) -> bool:
    triggers = ['grow in', 'plant in', 'species in', 'near', 'around', 'at coordinates', 'in region']
    return any(trigger in question.lower() for trigger in triggers)

def get_location_coordinates(location_input: str) -> Optional[Tuple[float, float]]:
    if ',' in location_input:
        parts = [p.strip() for p in location_input.split(',')]
        if len(parts) == 2:
            try:
                lat = float(parts[0])
                lon = float(parts[1])
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return (lat, lon)
            except ValueError:
                pass

    attempts = [
        location_input,
        location_input.title(),
        location_input.replace("St ", "Saint ").replace("St. ", "Saint ")
    ]

    country_matches = re.search(r',\s*([a-zA-Z\s]+)$', location_input)
    if country_matches:
        country = country_matches.group(1)
        attempts.extend([
            location_input,
            f"{location_input.split(',')[0].strip()}"
        ])

    for attempt in attempts:
        try:
            location = geolocator.geocode(attempt, exactly_one=True, timeout=10)
            if location:
                return (location.latitude, location.longitude)
        except (GeocoderTimedOut, GeocoderUnavailable):
            continue

    return None

def extract_location_from_question(question: str) -> Optional[str]:
    question_lower = question.lower()
    patterns = [
        r'(?:in|near|around|for)\s+(.+?)(?:\?|$)',
        r'at\s+(.+?)(?:\?|$)',
        r'coordinates\s+(.+?)(?:\?|$)',
        r'in\s+(.+?)\s*,\s*(.+?)(?:\?|$)',
        r'near\s+(.+?)\s*,\s*(.+?)(?:\?|$)'
    ]

    for pattern in patterns:
        match = re.search(pattern, question_lower)
        if match:
            return ', '.join([g.strip() for g in match.groups() if g.strip()])

    return None

def handle_location_query(question: str) -> Tuple[Optional[Tuple[float, float]], Optional[str]]:
    location_str = extract_location_from_question(question)
    if not location_str:
        return None, "Please specify a location (e.g., 'What plants grow in Raleigh?')"

    coords = get_location_coordinates(location_str)
    if not coords:
        return None, f"Could not find coordinates for: {location_str}"

    return coords, None

def generate_lagoa_rica_map(clone_scores, top_n=3):
    top_clones = sorted(clone_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]

    base_path = "data/LagoaRica.png"
    output_path = "temp/Lagoa_Rica_Annotated.png"
    public_path = "static/maps/Lagoa_Rica_Annotated.png"

    os.makedirs("temp", exist_ok=True)
    os.makedirs("static/maps", exist_ok=True)

    if not os.path.exists(base_path):
        raise FileNotFoundError(f"Map image not found: {base_path}")

    base_image = Image.open(base_path).convert("RGBA")
    overlay = Image.new("RGBA", base_image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    draw.text((20, 30), "Top Recommended Clones:", fill=(255, 0, 0, 255))
    for i, (clone, score) in enumerate(top_clones):
        draw.text((20, 65 + i * 35), f"{i+1}. {clone} - Score {score:.2f}", fill=(255, 0, 0, 255))

    annotated_image = Image.alpha_composite(base_image, overlay)
    annotated_image.save(output_path)

    if os.path.exists(output_path):
        os.makedirs("static/maps", exist_ok=True)
        shutil.copy(output_path, public_path)
    else:
        raise FileNotFoundError("Annotated image failed to save before copy")

    return "/static/maps/Lagoa_Rica_Annotated.png"