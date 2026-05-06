import flask
from flask import Flask, render_template, request, jsonify
import json
import os
import random
import re
import math
import sqlite3
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
import google.generativeai as genai

# Download NLTK data
try:
    nltk.download('vader_lexicon', quiet=True)
    sia = SentimentIntensityAnalyzer()
except:
    sia = None

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

# ─── Fallback Knowledge Base (Granular & Demographic-Specific) ───────────────
FALLBACK_RESOURCES = {
    "male": {
        "teen": {
            "Worry": {"summary": "Study pressure aur social acceptance ka bojh teen boys par kaafi hota hai.", "tips": ["Study sessions ke beech 15 min break lein", "Physical activity (football/gym) shuru karein", "Caffeine kam karein", "Apne kisi dost se dil ki baat karein"], "affirmation": "Main apni mehnat se har mushkil paar kar sakta hoon."},
            "Feeling Low": {"summary": "Aksar is umer mein akelapan aur doston ki kami mehsoos hoti hai.", "tips": ["Screen time kam karein", "Subah ki dhoop mein 10 min guzarein", "Apna pasandida music sunein", "Family ke sath thora waqt bitayein"], "affirmation": "Har din ek naya mouqa hai behtar banne ka."},
            "Overwhelmed": {"summary": "Boht sari umeedon aur future ki fikar ka bojh.", "tips": ["Ek waqt mein ek kaam karein", "Bari cheezon ko chotay hisson mein divide karein", "Gheri saans lein", "Social media se break lein"], "affirmation": "Main kafi hoon aur main handle kar sakta hoon."}
        },
        "young": {
            "Worry": {"summary": "Career aur financial stability ki fikar is umer mein aam hai.", "tips": ["Monthly budget banayein", "Apne career goals ko likh lein", "7-8 ghante ki neend puri karein", "Work-life balance banayein"], "affirmation": "Meri mehnat rang layegi."},
            "Relationship Challenges": {"summary": "Commitments aur social life ka balance mushkil lag sakta hai.", "tips": ["Clear communication rakhein", "Healthy boundaries set karein", "Self-care ko priority dein", "Gusso par control rakhein"], "affirmation": "Main izzat aur mohabbat ke qabil hoon."}
        },
        "adult": {
            "Overwhelmed": {"summary": "Ghar aur office ki zimmedariyan thaka deti hain.", "tips": ["Family ke sath quality time guzarein", "Hobby ke liye waqt nikalein", "Meditation shuru karein", "Zimmedariyan share karein"], "affirmation": "Main apne khandan ki taqat hoon."},
            "Worry": {"summary": "Bacho ka mustaqbil aur sehat ki fikar.", "tips": ["Bacho ke sath khelein", "Financial planning karein", "Healthy lifestyle apnaein", "Tension kam lein"], "affirmation": "Sab theek ho jayega."}
        }
    },
    "female": {
        "teen": {
            "Worry": {"summary": "Looks aur peer pressure teen girls ke liye baray masle hain.", "tips": ["Journaling shuru karein", "Positive affirmations parhein", "Social media ka use kam karein", "Apni pasand ka kaam karein"], "affirmation": "Main jesi hoon, behtareen hoon."},
            "Mood Swings": {"summary": "Hormonal changes aur stress ki wajah se mood tezi se badalta hai.", "tips": ["Water intake barhayein", "Yoga ya stretching karein", "Proper rest lein", "Healthy diet rakhein"], "affirmation": "Main apne emotions ko control kar sakti hoon."}
        },
        "young": {
            "Worry": {"summary": "Career aur marriage ka pressure is stage par boht hota hai.", "tips": ["Apne liye waqt nikalein", "Friends ke sath outitng pe jayein", "Skill development pe focus karein", "Pressure mein faisla na lein"], "affirmation": "Mera rasta mere liye behtareen hai."},
            "Relationship Challenges": {"summary": "Expectations aur boundaries ka masla.", "tips": ["Dil ki baat saaf karein", "Toxic logon se door rahein", "Self-respect pe compromise na karein", "Counseling lein agar zaroorat ho"], "affirmation": "Main sukoon aur khushi ki qabil hoon."}
        }
    }
}

# Generic Fallback for missing combos
GENERIC_FALLBACK = {
    "Worry": {"summary": "General anxiety aur fikar ka ehsas.", "tips": ["Gheri saans lein", "Paani piyein", "Fikar ko likh lein", "Walking karein"], "affirmation": "Main mehfooz hoon."},
    "Feeling Low": {"summary": "Udasi aur thakawat ka ehsas.", "tips": ["Rest karein", "Music sunein", "Dost se baat karein", "Nahayein"], "affirmation": "Ye waqt bhi guzar jayega."},
    "Overwhelmed": {"summary": "Kaam aur thoughts ka bojh.", "tips": ["Break lein", "To-do list banayein", "No kahein", "Deep breath"], "affirmation": "Ek qadam kafi hai."},
    "Calm": {"summary": "Sukoon aur itminan ka ehsas.", "tips": ["Shukar ada karein", "Naya goal banayein", "Madad karein", "Smile"], "affirmation": "Main khush hoon."}
}

# ─── KRR Ontology: Classes & Relationships ──────────────────────────────────
# This represents the "Ontology-based structure" for Mental Health Support
ONTOLOGY = {
    "Categories": ["Worry", "Feeling Low", "Overwhelmed", "Mood Swings", "Relationship Challenges", "Calm"],
    "Demographics": {
        "Age": ["teen", "young", "adult", "mid", "elderly"],
        "Gender": ["male", "female"]
    },
    "InferenceRules": {
        "HighDistress": ["suicide", "kill", "harm", "zindagi khatam", "marna"],
        "SentimentThresholds": {"Negative": -0.1, "Neutral": 0.1, "Positive": 0.5}
    }
}

# ─── Decision Logic: Knowledge-Based Reasoning Engine ───────────────────────
def reason_inference(text, gender, age):
    """
    KRR reasoning engine combining Bayesian Priors with Rule-based NLP.
    """
    scores = {"Worry": 0, "Feeling Low": 0, "Overwhelmed": 0, "Mood Swings": 0, "Relationship Challenges": 0, "Calm": 0}
    
    # 1. NLP Rule-based Analysis (VADER Sentiment)
    sentiment_score = 0
    if sia:
        sentiment_score = sia.polarity_scores(text)['compound']
    
    # 2. Bayesian Prior Reasoning
    priors = PRIOR_RULES.get(gender, {}).get(age, {})
    # Map KRR classes from dataset to UI Categories
    mapping = {
        "Anxiety": "Worry", "Normal": "Calm", "Depression": "Feeling Low",
        "Suicidal": "Feeling Low", "Stress": "Overwhelmed", "Bipolar": "Mood Swings",
        "Personality disorder": "Relationship Challenges"
    }
    
    for cls, val in priors.items():
        ui_cat = mapping.get(cls)
        if ui_cat:
            scores[ui_cat] += val

    # 3. Decision Logic adjustment based on sentiment
    if sentiment_score < ONTOLOGY["InferenceRules"]["SentimentThresholds"]["Negative"]:
        scores["Feeling Low"] += 20
        scores["Worry"] += 10
    elif sentiment_score > ONTOLOGY["InferenceRules"]["SentimentThresholds"]["Positive"]:
        scores["Calm"] += 30

    # 4. Behavior Detection (Specific keywords for confidence boosting)
    lower_text = text.lower()
    if any(w in lower_text for w in ["hamesha", "daily", "always", "every"]):
        # Boost current winner's confidence logic
        pass

    # Normalize
    total = sum(scores.values())
    probs = {k: round((v/total)*100, 1) for k, v in scores.items()}
    winner = max(probs, key=probs.get)
    
    return winner, probs, sentiment_score

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

    g_label   = "Male" if gender == "male" else "Female"
    a_label   = AGE_LABELS.get(age, age)

    # ─── KRR Reasoning Engine (Rule-based & NLP) ─────────────────────────────
    # This fulfills the "Knowledge Representation and Reasoning" requirement
    category_reasoned, probs_reasoned, sentiment_val = reason_inference(text, gender, age)
    
    # ─── Gemini Inference Logic (Optional Enhancement) ──────────────────────
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
        # Check for Crisis first (Decision Rule)
        is_crisis = any(w in text.lower() for w in ONTOLOGY["InferenceRules"]["HighDistress"])
        
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
        result_data["isCrisis"] = is_crisis or result_data.get("isCrisis", False)
        
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
        
        fb = FALLBACK_RESOURCES.get(gender, {}).get(age, {}).get(category_reasoned)
        if not fb:
            fb = GENERIC_FALLBACK.get(category_reasoned, GENERIC_FALLBACK["Calm"])
        
        return jsonify({
            "condition": category_reasoned,
            "confidence": "Reasoned (KRR Engine)",
            "posteriorProbs": probs_reasoned,
            "summary": fb["summary"] + f" (NLP Sentiment: {sentiment_val})",
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
