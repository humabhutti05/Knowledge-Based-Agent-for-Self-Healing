from flask import Flask, render_template, request, jsonify
import json
import os
import random
import re
import math

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

    # ─── Inference Logic ─────────────────────────────────────────────────────
    if MODEL_DATA:
        # Use Trained Naive Bayes Model
        tokens = re.findall(r'\w+', text.lower())
        classes = MODEL_DATA["classes"]
        vocab_size = MODEL_DATA["vocab_size"]
        
        # Start with log priors from the training data combined with profile priors
        # Profile priors are 0-100, we convert to relative weights
        profile_weights = {k: v/100 for k, v in priors.items()}
        
        class_scores = {}
        for c in classes:
            # P(C) - combining dataset prior with profile prior
            data_prior = MODEL_DATA["class_priors"].get(c, 1/len(classes))
            profile_prior = profile_weights.get(c, 0.1) # fallback
            
            # Log probability to avoid underflow
            score = math.log(data_prior * profile_prior)
            
            # P(W|C) - adding log likelihoods for each token
            for token in tokens:
                count = MODEL_DATA["word_probs"].get(token, {}).get(c, 0)
                # Laplace smoothing
                prob = (count + 1) / (MODEL_DATA["class_totals"].get(c, 0) + vocab_size)
                score += math.log(prob)
            
            class_scores[c] = score

        # Convert back from log space to probabilities for UI
        # Shift scores for stability (exp(score - max_score))
        max_score = max(class_scores.values())
        exp_scores = {k: math.exp(v - max_score) for k, v in class_scores.items()}
        total_exp = sum(exp_scores.values())
        
        posteriors = {k: round((v / total_exp) * 100, 2) for k, v in exp_scores.items()}
        top_condition = max(posteriors, key=posteriors.get)
        
    else:
        # Fallback to simple keyword matcher if model not ready
        keywords = {
            "Anxiety": ["worried", "anxious", "panic", "heart racing", "nervous", "fear", "scared"],
            "Depression": ["sad", "hopeless", "tired", "crying", "alone", "dark", "numb", "worthless"],
            "Stress": ["busy", "pressure", "deadline", "overwhelmed", "work", "exhausted", "tension"],
            "Bipolar": ["mood swings", "manic", "hyper", "low", "energy", "unstable"],
            "Suicidal": ["end it", "kill", "goodbye", "no point", "harm", "die", "suicide"],
            "Personality disorder": ["relationships", "self-image", "impulsive", "splitting"],
            "Normal": ["okay", "fine", "good", "stable", "happy", "normal"]
        }
        scores = {k: 0 for k in priors.keys()}
        for condition, terms in keywords.items():
            if condition in scores:
                for term in terms:
                    if term in text.lower(): scores[condition] += 2
        
        total = sum(priors.values())
        posteriors = {}
        for k, p_val in priors.items():
            multiplier = 1 + (scores.get(k, 0) * 0.5)
            posteriors[k] = p_val * multiplier
        
        norm_total = sum(posteriors.values())
        posteriors = {k: round((v / norm_total) * 100, 2) for k, v in posteriors.items()}
        top_condition = max(posteriors, key=posteriors.get)

    # ─── Shared Logic (Confidence, Crisis, Content) ──────────────────────────
    is_crisis = "kill" in text.lower() or "suicide" in text.lower() or "end it" in text.lower()
    if posteriors.get("Suicidal", 0) > 40: is_crisis = True # High suicidal prob
    
    confidence = "High" if max(posteriors.values()) > 60 else "Medium" if max(posteriors.values()) > 30 else "Low"

    summaries = {
        "Anxiety": f"Your patterns suggest a high correlation with anxiety symptoms. As a {g_label} {a_label}, this often manifests as a cycle of persistent worry and physical tension.",
        "Depression": f"The emotional depth of your statement reflects signs of clinical depression. For individuals in the {a_label} group, this can feel like a heavy, unchanging weight.",
        "Stress": f"You are showing clear indicators of high-level stress. This is common in the {a_label} profile when responsibilities exceed perceived capacity.",
        "Normal": f"Your current statement aligns with a stable mental state, though you remain proactive about your wellbeing.",
        "Suicidal": "URGENT: Your statement contains markers of severe crisis. We strongly urge you to contact a helpline immediately."
    }
    summary = summaries.get(top_condition, f"Analysis suggests {top_condition} is the primary driver of your current state.")

    tips_pool = {
        "Anxiety": ["Deep belly breathing", "Limit screen time before bed", "Grounding: 5-4-3-2-1 technique", "Write down worries to externalize them"],
        "Depression": ["Step outside for 5 mins", "Reach out to one person today", "Listen to upbeat music", "Focus on one small task"],
        "Stress": ["Prioritize and delegate", "Take a short walk", "Practice mindfulness", "Establish clear work-life boundaries"],
        "Normal": ["Keep up your routine", "Practice gratitude journaling", "Stay physically active", "Nurture your social connections"],
    }
    tips = tips_pool.get(top_condition, tips_pool["Normal"])[:4]

    result = {
        "condition": top_condition,
        "confidence": confidence,
        "posteriorProbs": posteriors,
        "summary": summary,
        "tips": tips,
        "affirmation": f"You are resilient, and understanding these patterns is the first step toward healing.",
        "isCrisis": is_crisis,
        "gender": g_label,
        "ageLabel": a_label
    }

    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
