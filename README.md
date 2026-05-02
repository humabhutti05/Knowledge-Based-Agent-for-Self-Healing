# Self HealUp — Knowledge-Based Mental Health Agent

A Flask web application implementing a **Knowledge-Based Agent** for mental health support,
using gender & age-aware Bayesian inference rules on 53,043 labeled mental health statements.

## Architecture (as per diagram)

```
User Input → Knowledge Base → Inference Engine → Suggestions & Guidance → Support to User
              (Mental Health    (Processing &      (Recommendations        (Advice &
               Data & Rules)    Analysis)           & Tips)                 Solutions)
```

## Features

- **Gender-based rules** — Male vs Female prior probabilities
- **Age-group rules** — Teen / Young Adult / Adult / Middle Age / Elderly
- **7 Mental Health Categories** — Anxiety, Depression, Stress, Bipolar, Suicidal, Personality Disorder, Normal
- **Posterior probability bars** — Bayesian inference result visualization
- **Gender & Age tailored tips** — Recommendations specific to profile
- **Crisis detection** — Auto-banner for suicidal ideation
- **Dataset** — 53,043 labeled statements in `data/Combined_Data.csv`

## Setup & Run

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Set your Anthropic API Key
```bash
# Windows
set ANTHROPIC_API_KEY=your_api_key_here

# Mac / Linux
export ANTHROPIC_API_KEY=your_api_key_here
```

### 3. Run the app
```bash
python app.py
```

### 4. Open browser
```
http://localhost:5000
```

## Project Structure

```
self_healup/
├── app.py                  ← Flask backend + inference rules
├── requirements.txt        ← Python dependencies
├── README.md
├── data/
│   └── Combined_Data.csv   ← 53,043 labeled mental health statements
├── templates/
│   └── index.html          ← Main HTML page
└── static/
    ├── css/
    │   └── style.css       ← Styling
    └── js/
        └── app.js          ← Frontend logic
```

## Knowledge Base Rules

Prior probabilities are defined in `app.py` under `PRIOR_RULES`.
Each gender × age combination has a different probability distribution
reflecting real-world mental health research patterns.

Example:
- **Female, Teen** → Anxiety: 30%, Depression: 25%, Stress: 16%
- **Male, Adult**  → Stress: 30%, Depression: 22%, Anxiety: 14%

The inference engine combines these priors with the AI's analysis of the
user's statement to produce posterior probabilities — the final result.

## Note

This app is for educational/research purposes only.
It is NOT a substitute for professional mental health care.
