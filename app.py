import flask
from flask import Flask, render_template, request, jsonify
import json
import os
import random
import re
import math
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

# ─── Data Logging ───────────────────────────────────────────────────────────
HISTORY_PATH = os.path.join(os.path.dirname(__file__), 'data', 'history.json')

def save_assessment(result, user_text):
    try:
        from datetime import datetime
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_text": user_text,
            "gender": result.get("gender"),
            "age": result.get("ageLabel"),
            "prediction": result.get("condition"),
            "confidence": result.get("confidence"),
            "posteriorProbs": result.get("posteriorProbs")
        }
        
        history = []
        if os.path.exists(HISTORY_PATH):
            try:
                with open(HISTORY_PATH, 'r') as f:
                    history = json.load(f)
            except:
                history = []
        
        history.append(log_entry)
        
        with open(HISTORY_PATH, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Error saving history: {e}")

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
Analyze the feelings of a {g_label} ({a_label}) who said: "{text}"

Pay special attention to frequency keywords like "sometimes", "usually", "daily", "all the time", or numerical values (e.g. 50-60%) if provided. Use these to adjust the intensities of the categories and your confidence level.

Identify the intensities for these categories: Worry, Feeling Low, Overwhelmed, Mood Swings, Relationship Challenges, Calm.
The total sum of probabilities MUST be 100.

Respond ONLY with this JSON format:
{{
  "condition": "Primary Feeling Name",
  "confidence": "High/Medium/Low",
  "posteriorProbs": {{
    "Worry": 15,
    "Feeling Low": 10,
    ... (all 6 categories summing to 100)
  }},
  "summary": "2 sentences in user's language (Roman Urdu/English) explaining why they feel this way.",
  "tips": ["Tip 1", "Tip 2", "Tip 3", "Tip 4"],
  "affirmation": "Short positive sentence.",
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
    app.run(debug=True, port=5000)
