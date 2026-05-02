// ── Icons Map ──
const ICONS = {
  "Anxiety": "😰", "Depression": "😔", "Stress": "😤",
  "Normal": "😊", "Suicidal": "🆘", "Bipolar": "🔄", "Personality disorder": "🧩"
};

// ── State ──
let state = {
  gender: null,
  age: null,
  text: "",
  model: null // To store the fetched model.json
};

// ── Prior Rules (Duplicated from app.py for static use) ──
const PRIOR_RULES = {
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
};

const AGE_LABELS = {
  "teen": "Teen (13–19)", "young": "Young Adult (20–35)",
  "adult": "Adult (36–55)", "mid": "Middle Age (56–65)", "elderly": "Elderly (65+)"
};

// ── Initialization ──
window.addEventListener('DOMContentLoaded', async () => {
  try {
    const res = await fetch("data/model.json");
    state.model = await res.json();
    console.log("Neural model loaded successfully");
  } catch (err) {
    console.error("Failed to load model:", err);
  }
});

// ── Selectors ──
function selectGender(g) {
  state.gender = g;
  document.querySelectorAll(".gender-grid .select-box").forEach(el => el.classList.remove("selected"));
  document.getElementById(g === "male" ? "gMale" : "gFemale").classList.add("selected");
  checkStep1();
}

function selectAge(a) {
  state.age = a;
  document.querySelectorAll(".age-grid .select-box").forEach(el => el.classList.remove("selected"));
  const idMap = { teen: "aTeen", young: "aYoung", adult: "aAdult", mid: "aMid", elderly: "aElderly" };
  document.getElementById(idMap[a]).classList.add("selected");
  checkStep1();
}

function checkStep1() {
  const isReady = state.gender && state.age;
  document.getElementById("nextBtn").disabled = !isReady;
}

// ── Navigation ──
function goStep2() {
  document.getElementById("step1").style.display = "none";
  document.getElementById("step2").style.display = "block";
  updateStepper(2);
}

function goStep1() {
  document.getElementById("step2").style.display = "none";
  document.getElementById("step1").style.display = "block";
  updateStepper(1);
}

function updateStepper(step) {
  document.querySelectorAll(".step").forEach((el, idx) => {
    el.classList.toggle("active", idx + 1 === step);
  });
}

function setTag(t) {
  document.getElementById("feelingInput").value = t;
}

// ── Inference Engine ──
async function analyze() {
  const text = document.getElementById("feelingInput").value.trim();
  if (!text) return;

  const btn = document.getElementById("analyzeBtn");
  btn.disabled = true;
  btn.textContent = "Processing Neural Data...";

  // Show results area with loading
  document.getElementById("step2").style.display = "none";
  document.getElementById("step3").style.display = "block";
  updateStepper(3);

  document.getElementById("resultArea").innerHTML = `
    <div class="card glass" style="text-align:center; padding: 4rem;">
      <div class="logo-icon animate-pulse">🧠</div>
      <p style="margin-top: 1rem; color: var(--text-muted);">Integrating prior probabilities with statement evidence...</p>
    </div>`;

  // Local Neural Analysis (Ported from Python)
  setTimeout(() => {
    const result = runNeuralInference(text);
    renderResult(result);
  }, 800); // Simulate processing time for UX
}

function runNeuralInference(text) {
  const priors = PRIOR_RULES[state.gender][state.age];
  const g_label = state.gender === "male" ? "Male" : "Female";
  const a_label = AGE_LABELS[state.age];

  let posteriors = {};
  let top_condition = "Normal";

  if (state.model) {
    const tokens = text.toLowerCase().match(/\w+/g) || [];
    const classes = state.model.classes;
    const vocab_size = state.model.vocab_size;
    const profile_weights = Object.fromEntries(Object.entries(priors).map(([k, v]) => [k, v / 100]));
    
    let class_scores = {};
    for (let c of classes) {
      const data_prior = state.model.class_priors[c] || (1 / classes.length);
      const profile_prior = profile_weights[c] || 0.1;
      
      let score = Math.log(data_prior * profile_prior);
      for (let token of tokens) {
        const count = (state.model.word_probs[token] && state.model.word_probs[token][c]) || 0;
        const prob = (count + 1) / (state.model.class_totals[c] + vocab_size);
        score += Math.log(prob);
      }
      class_scores[c] = score;
    }

    const max_score = Math.max(...Object.values(class_scores));
    const exp_scores = Object.fromEntries(Object.entries(class_scores).map(([k, v]) => [k, Math.exp(v - max_score)]));
    const total_exp = Object.values(exp_scores).reduce((a, b) => a + b, 0);
    
    posteriors = Object.fromEntries(Object.entries(exp_scores).map(([k, v]) => [k, (v / total_exp) * 100]));
    top_condition = Object.keys(posteriors).reduce((a, b) => posteriors[a] > posteriors[b] ? a : b);
  } else {
    // Basic fallback if model didn't load
    posteriors = {...priors};
    top_condition = "Normal";
  }

  const is_crisis = text.toLowerCase().includes("kill") || text.toLowerCase().includes("suicide") || posteriors["Suicidal"] > 40;
  const confidence = Math.max(...Object.values(posteriors)) > 60 ? "High" : Math.max(...Object.values(posteriors)) > 30 ? "Medium" : "Low";

  const summaries = {
    "Anxiety": `Your patterns suggest a high correlation with anxiety symptoms. As a ${g_label} ${a_label}, this often manifests as a cycle of persistent worry.`,
    "Depression": `The emotional depth of your statement reflects signs of clinical depression. For individuals in the ${a_label} group, this can feel like a heavy weight.`,
    "Stress": `You are showing clear indicators of high-level stress. This is common in the ${a_label} profile when responsibilities exceed capacity.`,
    "Normal": `Your current statement aligns with a stable mental state.`,
    "Suicidal": "URGENT: Your statement contains markers of severe crisis. Please contact a helpline immediately."
  };

  const tips_pool = {
    "Anxiety": ["Deep belly breathing", "Limit screen time before bed", "Grounding: 5-4-3-2-1 technique", "Write down worries"],
    "Depression": ["Step outside for 5 mins", "Reach out to one person today", "Listen to upbeat music", "Focus on one small task"],
    "Stress": ["Prioritize and delegate", "Take a short walk", "Practice mindfulness", "Clear work-life boundaries"],
    "Normal": ["Keep up your routine", "Practice gratitude journaling", "Stay physically active", "Nurture social connections"],
  };

  return {
    condition: top_condition,
    confidence: confidence,
    posteriorProbs: posteriors,
    summary: summaries[top_condition] || summaries["Normal"],
    tips: tips_pool[top_condition] || tips_pool["Normal"],
    affirmation: "You are resilient, and understanding these patterns is the first step toward healing.",
    isCrisis: is_crisis,
    gender: g_label,
    ageLabel: a_label
  };
}


function renderResult(d) {
  const icon = ICONS[d.condition] || "✨";
  
  // Sort and build probability bars
  const sortedProbs = Object.entries(d.posteriorProbs).sort((a, b) => b[1] - a[1]);
  const probBars = sortedProbs.map(([name, val]) => `
    <div class="prob-item">
      <span class="prob-name">${name}</span>
      <div class="prob-track">
        <div class="prob-bar" style="width: ${val}%; opacity: ${name === d.condition ? 1 : 0.3}"></div>
      </div>
      <span class="prob-val" style="width: 40px; text-align: right; font-size: 0.8rem;">${Math.round(val)}%</span>
    </div>
  `).join("");

  // Build tips
  const tips = d.tips.map(t => `<div class="tip-card">${t}</div>`).join("");

  document.getElementById("resultArea").innerHTML = `
    <div class="result-container">
      ${d.isCrisis ? `
        <div class="crisis-alert">
          <h4 style="margin-bottom: 0.5rem;">🆘 Crisis Support Detected</h4>
          <p style="font-size: 0.9rem;">Your statement contains markers of high distress. Please reach out to a professional or a crisis helpline immediately. You are not alone.</p>
        </div>` : ''}

      <div class="card glass">
        <div class="result-header">
          <div class="res-icon">${icon}</div>
          <div class="res-info">
            <p>Primary Indicator</p>
            <h3>${d.condition} <span class="badge" style="background: rgba(255,255,255,0.1); border: 1px solid var(--border-glass);">${d.confidence} Confidence</span></h3>
          </div>
        </div>

        <div class="prob-grid">
          <label class="group-label">Posterior Distribution</label>
          ${probBars}
        </div>

        <div class="summary-box">
          ${d.summary}
        </div>

        <div class="input-group">
          <label class="group-label">Neural Recommendations</label>
          <div class="tips-grid">
            ${tips}
          </div>
        </div>

        <div class="affirmation" style="text-align: center; color: var(--accent-primary); font-weight: 500; font-style: italic;">
          "${d.affirmation}"
        </div>
      </div>
    </div>
  `;
}

function reset() {
  state = { gender: null, age: null, text: "" };
  document.getElementById("feelingInput").value = "";
  document.querySelectorAll(".select-box").forEach(el => el.classList.remove("selected"));
  document.getElementById("step3").style.display = "none";
  document.getElementById("step1").style.display = "block";
  document.getElementById("nextBtn").disabled = true;
  document.getElementById("analyzeBtn").disabled = false;
  document.getElementById("analyzeBtn").textContent = "Run Neural Inference";
  updateStepper(1);
}

// ── Shortcuts ──
document.addEventListener("keydown", (e) => {
  if (e.ctrlKey && e.key === "Enter") {
    if (document.getElementById("step2").style.display !== "none") analyze();
  }
});

