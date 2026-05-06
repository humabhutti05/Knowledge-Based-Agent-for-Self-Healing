import flask
from flask import Flask, render_template, request, jsonify
import json
import os
import random
import re
import math
import sqlite3
import google.generativeai as genai

# Configure Gemini — Load API key from .env file
from dotenv import load_dotenv
load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
genai.configure(api_key=GEMINI_API_KEY)
generation_config = {
  "temperature": 0.7,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 1024,
  "response_mime_type": "application/json",
}
model = genai.GenerativeModel(
  model_name="gemini-flash-latest",
  generation_config=generation_config,
)
app = Flask(__name__)

# ─── Load Local Trained Model ───────────────────────────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'data', 'model.json')
MODEL_DATA = None
if os.path.exists(MODEL_PATH):
    try:
        with open(MODEL_PATH, 'r') as f:
            MODEL_DATA = json.load(f)
    except Exception as e:
        print(f"Error loading model: {e}")


# ─── Knowledge Base: Gender + Age Prior Probabilities ───────────────────────
PRIOR_RULES = {
    "male": {
        "teen":    {"Anxiety":18,"Depression":20,"Stress":22,"Bipolar":12,"Suicidal":14,"Normal":10,"Personality disorder":4},
        "young":   {"Anxiety":16,"Depression":18,"Stress":28,"Bipolar":10,"Suicidal":12,"Normal":12,"Personality disorder":4},
        "adult":   {"Anxiety":14,"Depression":22,"Stress":30,"Bipolar":12,"Suicidal":10,"Normal":8,"Personality disorder":4},
        "mid":     {"Anxiety":16,"Depression":26,"Stress":24,"Bipolar":10,"Suicidal":12,"Normal":8,"Personality disorder":4},
        "elderly": {"Anxiety":18,"Depression":32,"Stress":18,"Bipolar":8,"Suicidal":14,"Normal":6,"Personality disorder":4},
    },
    "female": {
        "teen":    {"Anxiety":30,"Depression":25,"Stress":16,"Bipolar":8,"Suicidal":10,"Normal":7,"Personality disorder":4},
        "young":   {"Anxiety":32,"Depression":28,"Stress":16,"Bipolar":8,"Suicidal":8,"Normal":5,"Personality disorder":3},
        "adult":   {"Anxiety":28,"Depression":30,"Stress":18,"Bipolar":9,"Suicidal":7,"Normal":5,"Personality disorder":3},
        "mid":     {"Anxiety":26,"Depression":32,"Stress":18,"Bipolar":8,"Suicidal":8,"Normal":5,"Personality disorder":3},
        "elderly": {"Anxiety":22,"Depression":36,"Stress":16,"Bipolar":8,"Suicidal":10,"Normal":5,"Personality disorder":3},
    }
}

AGE_LABELS = {
    "teen":    "Teen (13–19)",
    "young":   "Young Adult (20–35)",
    "adult":   "Adult (36–55)",
    "mid":     "Middle Age (56–65)",
    "elderly": "Elderly (65+)"
}

# ─── Fallback Knowledge Base (When API Fails) ────────────────────────────────
FALLBACK_RESOURCES = {
    "Worry": {
        "summary": "Aapka brain shayad kisi unwanted pressure ya uncertainty ki wajah se overdrive mein hai. Yeh aksar future ki fikar ki wajah se hota hai.",
        "tips": ["Deep breathing exercises (5 mins)", "5-4-3-2-1 grounding technique", "Caffeine kam karein", "Apni fikron ko ek diary mein likhein"],
        "affirmation": "Main mehfooz hoon, aur meri saans mere control mein hai."
    },
    "Feeling Low": {
        "summary": "Emotional thakawat aur mayusi aapki energy drain kar rahi hai. Choti baaton par focus karna mushkil lag raha hai.",
        "tips": ["Ek choti walk par jayein", "Kisi qareebi dost se baat karein", "Halka aur sukoon wala music sunein", "Dhoop mein thora waqt guzarein"],
        "affirmation": "Ye feeling temporary hai. Main har din behtar mehsoos karunga."
    },
    "Overwhelmed": {
        "summary": "Zindagi ki zimmedariyan aur thoughts ka bojh barh gaya hai. It feels like too much to handle at once.",
        "tips": ["Kaam ko chotay hisson mein baantein", "Extra zimmedariyon ko 'No' kahein", "15 minute screen break lein", "Neend puri karne ki koshish karein"],
        "affirmation": "Ek waqt mein ek qadam uthana kafi hai."
    },
    "Calm": {
        "summary": "Aapka emotional state filhal stable hai. Yeh behtareen waqt hai naye goals set karne ka.",
        "tips": ["Apna routine jari rakhein", "Kisi ki madad karein", "Koi naya hobby shuru karein", "Apni kamyabiyon par ghaur karein"],
        "affirmation": "Main apne aap aur duniya ke sath sukoon mein hoon."
    }
}

# ─── Data Logging (SQLite) ──────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'wellbeing.db')

def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                user_text TEXT,
                gender TEXT,
                age TEXT,
                prediction TEXT,
                confidence TEXT,
                posterior_probs TEXT,
                summary TEXT,
                tips TEXT,
                affirmation TEXT,
                is_crisis INTEGER
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database Init Error: {e}")

def save_assessment(result, user_text):
    try:
        from datetime import datetime
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO assessments (
                timestamp, user_text, gender, age, prediction, 
                confidence, posterior_probs, summary, tips, affirmation, is_crisis
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            user_text,
            result.get("gender"),
            result.get("ageLabel"),
            result.get("condition"),
            result.get("confidence"),
            json.dumps(result.get("posteriorProbs")),
            result.get("summary"),
            json.dumps(result.get("tips")),
            result.get("affirmation"),
            1 if result.get("isCrisis") else 0
        ))
        
        conn.commit()
        conn.close()
        print("Data successfully saved to database.", flush=True)
    except Exception as e:
        print(f"Error saving to database: {e}")

# client = anthropic.Anthropic()  # Removed Anthropic dependency

@app.route("/api/stats", methods=["GET"])
def get_stats():
    try:
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Total count
        cursor.execute('SELECT COUNT(*) FROM assessments')
        total = cursor.fetchone()[0]
        
        # Today's count
        cursor.execute("SELECT COUNT(*) FROM assessments WHERE timestamp LIKE ?", (f'{today}%',))
        today_count = cursor.fetchone()[0]
        
        # Category breakdown
        cursor.execute('SELECT prediction, COUNT(*) FROM assessments GROUP BY prediction')
        rows = cursor.fetchall()
        breakdown = {row[0]: row[1] for row in rows}
        
        conn.close()
        return jsonify({
            "total": total,
            "today": today_count,
            "breakdown": breakdown
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/priors", methods=["POST"])
def get_priors():
    data = request.json
    gender = data.get("gender", "male")
    age = data.get("age", "young")
    priors = PRIOR_RULES.get(gender, {}).get(age, {})
    return jsonify({"priors": priors, "ageLabel": AGE_LABELS.get(age, age)})

@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.json
    text    = data.get("text", "")
    gender  = data.get("gender", "male")
    age     = data.get("age", "young")

    if not text.strip():
        return jsonify({"error": "No input provided"}), 400

    priors    = PRIOR_RULES.get(gender, {}).get(age, {})
    g_label   = "Male" if gender == "male" else "Female"
    a_label   = AGE_LABELS.get(age, age)

    # ─── Gemini Inference Logic ────────────────────────────────────────────────
    prompt = f"""
You are a highly empathetic and professional Wellbeing Guide. 
Analyze the feelings of a {g_label} ({a_label}) who expressed: "{text}"

Guidelines for analysis:
1. Frequency/Intensity: Pay attention to words like "hamesha", "kabhi kabhi", "rozana", "daily", or any percentages mentioned.
2. Categories: Worry, Feeling Low, Overwhelmed, Mood Swings, Relationship Challenges, Calm.
3. Language: If the user input is in Roman Urdu, the summary and tips should be primarily in Roman Urdu. If in English, use English.

CRITICAL: The "tips" must be:
- "Acha or Bht Acha": High quality, practical, and non-generic.
- "Unique": Do NOT give basic advice like "rest" or "drink water". Give 4 specific, actionable, and deep suggestions tailored for a {a_label} {g_label}.
- "Personalized": Directly address the nuance of what they said.

Respond ONLY with this JSON format:
{{
  "condition": "Primary Emotional State",
  "confidence": "High/Medium/Low",
  "posteriorProbs": {{
    "Worry": 0, "Feeling Low": 0, "Overwhelmed": 0, "Mood Swings": 0, "Relationship Challenges": 0, "Calm": 0
  }},
  "summary": "2-3 empathetic sentences in the user's language.",
  "tips": ["Tip 1", "Tip 2", "Tip 3", "Tip 4"],
  "affirmation": "A short, powerful affirmation.",
  "isCrisis": false
}}
"""

    try:
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        
        # Clean markdown
        if "```" in raw_text:
            raw_text = re.sub(r"```[a-z]*\n?", "", raw_text)
            raw_text = raw_text.replace("```", "")
        raw_text = raw_text.strip()
        
        print(f"Gemini Response: {raw_text}", flush=True)
        result_data = json.loads(raw_text)
        
        # Add required UI fields
        result_data["gender"] = g_label
        result_data["ageLabel"] = a_label
        
        # ─── Save User Data ──────────────────────────────────────────────────
        save_assessment(result_data, text)
        
        return jsonify(result_data)
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        with open("error.log", "a") as f: # Use append
            f.write("\n" + "="*20 + "\n")
            f.write(error_msg + "\n")
            f.write(traceback.format_exc() + "\n")
        
        print(f"Gemini API Error: {error_msg}", flush=True)
        
        # Determine likely fallback category from text (simple keyword matching)
        lower_text = text.lower()
        category = "Calm"
        if any(w in lower_text for w in ["tension", "worry", "dar", "fikar", "anxious"]): category = "Worry"
        elif any(w in lower_text for w in ["sad", "low", "mayus", "dukh", "depressed"]): category = "Feeling Low"
        elif any(w in lower_text for w in ["burden", "pressure", "bojh", "overwhelmed"]): category = "Overwhelmed"
        
        fb = FALLBACK_RESOURCES.get(category, FALLBACK_RESOURCES["Calm"])
        
        return jsonify({
            "condition": category,
            "confidence": "Low (Offline Mode)",
            "posteriorProbs": {category: 100},
            "summary": fb["summary"] + " (Note: Gemini API is currently unavailable, using local insights)",
            "tips": fb["tips"],
            "affirmation": fb["affirmation"],
            "isCrisis": False,
            "gender": g_label,
            "ageLabel": a_label,
            "error": "API_KEY_LEAKED" if "403" in error_msg else "SERVER_ERROR"
        })

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
