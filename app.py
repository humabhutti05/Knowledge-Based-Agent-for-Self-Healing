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
        with open("error.log", "w") as f:
            f.write(str(e) + "\n")
            f.write(traceback.format_exc() + "\n")
            if 'raw_text' in locals():
                f.write("\nRAW TEXT:\n" + raw_text)
        print(f"Gemini API Error: {e}", flush=True)
        # Fallback if Gemini fails
        return jsonify({
            "condition": "Calm",
            "confidence": "Low",
            "posteriorProbs": {"Calm": 100, "Worry": 0, "Feeling Low": 0},
            "summary": "We couldn't connect right now, but please know you are heard.",
            "tips": ["Take a deep breath", "Drink some water", "Rest your eyes", "Talk to a friend"],
            "affirmation": "You are resilient.",
            "isCrisis": False,
            "gender": g_label,
            "ageLabel": a_label
        })

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
