// ── Icons Map ──
const ICONS = {
  "Worry": "😰", "Feeling Low": "😔", "Overwhelmed": "😤",
  "Calm": "😊", "Crisis": "🆘", "Mood Swings": "🔄", "Relationship Challenges": "🧩"
};

// ── State ──
let state = {
  gender: null,
  age: null,
  text: "",
  responses: {}, // To store Yes/No answers: { index: "Yes"/"No" }
  localModel: null // Store local Naive Bayes model
};

// Map model.json classes to UI indicators
const CLASS_MAPPING = {
  "Anxiety": "Worry",
  "Normal": "Calm",
  "Depression": "Feeling Low",
  "Suicidal": "Feeling Low",
  "Stress": "Overwhelmed",
  "Bipolar": "Mood Swings",
  "Personality disorder": "Relationship Challenges"
};

const STATIC_SUGGESTIONS = {
  "Worry": {
    summary: "Your brain might be in overdrive due to unwanted pressure or uncertainty, often caused by worrying about the future.",
    tips: ["Deep breathing exercises", "5-4-3-2-1 grounding technique", "Limit caffeine intake", "Write down your worries"],
    affirmation: "I am safe, and I am in control of my breath."
  },
  "Feeling Low": {
    summary: "Emotional exhaustion and a sense of hopelessness are draining your energy, making it hard to focus on small tasks.",
    tips: ["Go for a short walk", "Talk to a trusted friend", "Listen to uplifting music", "Sunlight exposure"],
    affirmation: "This feeling is temporary. I am growing stronger each day."
  },
  "Overwhelmed": {
    summary: "Life's responsibilities and the weight of your thoughts have increased. It feels like too much to handle at once.",
    tips: ["Break tasks into small steps", "Say no to extra commitments", "Take a 15-minute screen break", "Prioritize sleep"],
    affirmation: "One step at a time is enough."
  },
  "Mood Swings": {
    summary: "Your emotions are changing rapidly, which is affecting both your energy levels and your focus.",
    tips: ["Keep a mood journal", "Maintain a regular sleep cycle", "Avoid emotional triggers", "Practice mindfulness"],
    affirmation: "I embrace my emotions without letting them drive me."
  },
  "Relationship Challenges": {
    summary: "You are experiencing some tension or difficulty in your social interactions and personal connections.",
    tips: ["Set healthy boundaries", "Practice active listening", "Focus on self-care", "Express feelings clearly"],
    affirmation: "I deserve healthy and meaningful connections."
  },
  "Calm": {
    summary: "Your emotional state is currently stable. This is a great time to set new positive goals for yourself.",
    tips: ["Continue your routine", "Help someone else", "Try a new hobby", "Reflect on your progress"],
    affirmation: "I am at peace with myself and the world."
  }
};

// Load model on startup
window.addEventListener('DOMContentLoaded', async () => {
  try {
    const res = await fetch('./static/data/model.json');
    if (res.ok) {
      state.localModel = await res.json();
      console.log("Local model loaded successfully.");
    } else {
      console.warn("Local model response not OK.");
    }
  } catch (e) {
    console.warn("Could not load local model, will rely on server API or simple fallback.");
  }
});


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

// ── Guided Prompts ──
const GUIDED_QUESTIONS = {
  "male": {
    "teen": [
      "Do you feel constant pressure to perform well in studies?",
      "Is social media making you feel less confident about yourself?",
      "Are you struggling with sleep because of late-night thoughts?",
      "Do you feel disconnected from your parents or siblings?",
      "Are you worried about what you will do after finishing school?",
      "Do you feel like your friends don't truly understand you?"
    ],
    "young": [
      "Is career uncertainty or work pressure weighing you down?",
      "Do you feel lonely even when you are with other people?",
      "Are you struggling to balance your job with personal life?",
      "Do you feel constant pressure to achieve financial success?",
      "Are relationship issues affecting your mental peace?",
      "Do you find it hard to stay motivated for your goals?"
    ],
    "adult": [
      "How is the balance between your job and family life right now?",
      "Are financial or professional responsibilities causing constant worry?",
      "Do you feel you have enough time for your own mental wellbeing?",
      "Are you worried about the future stability of your family?",
      "Do you feel appreciated for the work you do at home and office?",
      "Is physical health becoming a source of stress for you?"
    ],
    "mid": [
      "Are you experiencing stress regarding future stability or retirement?",
      "How are changes in your health or energy levels affecting you?",
      "Do you feel a sense of isolation or disconnect from younger generations?",
      "Are you worried about the health of your elderly parents or spouse?",
      "Do you feel that you've achieved what you wanted in life?",
      "Is the 'empty nest' feeling making you feel sad or purposeless?"
    ],
    "elderly": [
      "Are you feeling lonely or missing people who are no longer around?",
      "How is your physical health impacting your mood today?",
      "Do you find it difficult to find purpose in your daily activities?",
      "Do you feel like you are a burden to your family members?",
      "Are memories of the past making you feel regretful or sad?",
      "Are you worried about how your family will manage or what will happen to them after you are gone?"
    ]
  },
  "female": {
    "teen": [
      "Do you feel judged by your peers based on your appearance?",
      "Is academic competition causing you constant anxiety?",
      "Do you feel like you have to hide your true feelings from friends?",
      "Are you experiencing mood swings that you can't explain?",
      "Do you feel overwhelmed by the expectations of being 'perfect'?",
      "Is social media pressure making you feel inadequate?"
    ],
    "young": [
      "Are you feeling burnt out from balancing career and home expectations?",
      "Do you feel anxious about your future life choices like marriage?",
      "Is the pressure to look or behave a certain way exhausting you?",
      "Do you feel you lack a strong emotional support system?",
      "Are you finding it hard to set boundaries with people in your life?",
      "Do you often feel like you're falling behind your peers' milestones?"
    ],
    "adult": [
      "How is the weight of family responsibilities affecting your time?",
      "Do you feel overwhelmed by the 'invisible mental load' of daily life?",
      "Are you finding it hard to cope with workplace stress and home duties?",
      "Do you feel your personal needs are always last on the priority list?",
      "Are you worried about the upbringing or future of your children?",
      "Do you feel a loss of your own identity outside of being a mother/wife?"
    ],
    "mid": [
      "Are life transitions or empty-nest feelings causing you sadness?",
      "How are you coping with changes in your physical wellbeing (e.g. menopause)?",
      "Do you feel that your emotional needs are being met by those around you?",
      "Are you worried about your financial independence in the future?",
      "Do you feel a sense of regret about things you couldn't do earlier?",
      "Is the health of your partner or parents a constant source of worry?"
    ],
    "elderly": [
      "Do you often feel isolated or disconnected from your family?",
      "How do memories of the past affect your current emotional state?",
      "Are health concerns making it difficult for you to stay positive?",
      "Do you feel that your wisdom and presence are valued by others?",
      "Are you afraid of the future or of losing your independence?",
      "Do you worry about the future of your children or family and how they will cope without you?"
    ]
  }
};

// ── Initialization ──
async function fetchStats() {
  try {
    console.log("Fetching system stats from /api/stats...");
    const res = await fetch('/api/stats');
    if (!res.ok) throw new Error("Stats API error: " + res.status);
    const data = await res.json();
    console.log("Stats received successfully:", data);
    
    // Update live ticker in header
    if (document.getElementById("liveTotal")) document.getElementById("liveTotal").textContent = data.total || 0;
    if (document.getElementById("liveToday")) document.getElementById("liveToday").textContent = data.today || 0;

    // Update dashboard items if visible
    if (document.getElementById("totalStats")) document.getElementById("totalStats").textContent = data.total || 0;
    if (document.getElementById("todayStats")) document.getElementById("todayStats").textContent = data.today || 0;
    
    console.log("Rendering graphs...");
    if (document.getElementById("breakdownChart")) renderChart(data.breakdown);
    if (document.getElementById("mainTrendChart")) renderTrendChart(data.history, "mainTrendChart");
    if (document.getElementById("mainBarChart")) renderBarChart(data.breakdown, "mainBarChart");
    
    if (document.getElementById("recentLogBody")) {
      populateRecentTable(data.recent);
    }
  } catch (err) {
    console.error("CRITICAL: Failed to fetch stats:", err);
  }
}

window.addEventListener('DOMContentLoaded', async () => {
  try {
    const res = await fetch("/static/data/model.json");
    if (!res.ok) throw new Error("Model file not found at /static/data/model.json");
    state.model = await res.json();
    console.log("Neural model loaded successfully");
  } catch (err) {
    console.error("Failed to load model:", err);
  }
  
  // Call stats fetch immediately
  fetchStats();
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
function goStep2(isBack = false) {
  document.getElementById("step1").style.display = "none";
  document.getElementById("step2").style.display = "block";
  
  if (!isBack) {
    state.responses = {}; // Only reset if moving forward from Step 1
  }
  
  renderQuestions();
  updateStepper(2);
}

function goStep2FromStep3() {
  document.getElementById("step3").style.display = "none";
  document.getElementById("step2").style.display = "block";
  document.getElementById("analyzeBtn").disabled = false;
  document.getElementById("analyzeBtn").textContent = "Run Analysis";
  updateStepper(2);
}

function renderQuestions() {
  const prompts = GUIDED_QUESTIONS[state.gender][state.age] || [];
  const promptList = document.getElementById("promptList");
  
  let html = prompts.map((p, idx) => `
    <div class="mcq-item">
      <div class="mcq-question">${p}</div>
      <div class="mcq-options">
        <button class="mcq-btn" onclick="selectMCQ(${idx}, 'Yes', this)">Yes</button>
        <button class="mcq-btn" onclick="selectMCQ(${idx}, 'No', this)">No</button>
        <button class="mcq-btn" onclick="selectMCQ(${idx}, 'Maybe / Not Sure', this)">Maybe / Not Sure</button>
      </div>
    </div>
  `).join('');

  // Add "Others" option
  html += `
    <div class="mcq-item">
      <div class="mcq-question">Anything else you'd like to share? (Optional)</div>
      <div class="mcq-options">
        <button class="mcq-btn" onclick="toggleOthers(this)">Others / Custom</button>
      </div>
    </div>
  `;

  promptList.innerHTML = html;
  document.getElementById("guidedPromptsContainer").style.display = "block";
  
  // Restore previous selections if any
  Object.entries(state.responses).forEach(([idx, val]) => {
    const items = document.querySelectorAll(".mcq-item");
    if (items[idx]) {
      const btn = Array.from(items[idx].querySelectorAll(".mcq-btn")).find(b => b.textContent === val);
      if (btn) btn.classList.add("selected");
    }
  });

  // Hide textarea initially, show only if "Others" is clicked
  document.getElementById("customInputArea").style.display = "none";
}

function selectMCQ(idx, val, btn) {
  state.responses[idx] = val;
  
  // Update button UI
  const parent = btn.parentElement;
  parent.querySelectorAll(".mcq-btn").forEach(b => b.classList.remove("selected"));
  btn.classList.add("selected");
}

function toggleOthers(btn) {
  const area = document.getElementById("customInputArea");
  const isHidden = area.style.display === "none";
  area.style.display = isHidden ? "block" : "none";
  btn.classList.toggle("selected", isHidden);
  if (isHidden) {
    document.getElementById("feelingInput").focus();
  }
}

function selectPrompt(btn) {
  const input = document.getElementById("feelingInput");
  input.value = btn.textContent + "\n\n";
  input.focus();
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
  // Construct the text from MCQ responses and custom input
  let finalText = "";
  const questions = GUIDED_QUESTIONS[state.gender][state.age] || [];
  
  Object.entries(state.responses).forEach(([idx, ans]) => {
    if (ans === "Yes") {
      finalText += questions[idx] + " Yes. ";
    } else if (ans === "Maybe / Not Sure") {
      finalText += questions[idx] + " (I'm not sure/Maybe). ";
    }
  });

  const customText = document.getElementById("feelingInput").value.trim();
  if (customText) {
    finalText += "\n" + customText;
  }

  if (!finalText.trim()) {
    alert("Please answer some questions or share your thoughts first.");
    return;
  }

  const btn = document.getElementById("analyzeBtn");
  btn.disabled = true;
  btn.textContent = "Analyzing...";

  // Show results area with loading
  document.getElementById("step2").style.display = "none";
  document.getElementById("step3").style.display = "block";
  updateStepper(3);

  document.getElementById("resultArea").innerHTML = `
    <div class="card glass" style="text-align:center; padding: 4rem;">
      <div class="logo-icon animate-pulse">✨</div>
      <p style="margin-top: 1rem; color: var(--text-muted);">Self HealUp is carefully thinking about what you said...</p>
    </div>`;

  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: finalText,
        gender: state.gender,
        age: state.age
      })
    });
    
    if (!response.ok) throw new Error('Server not found');
    
    const result = await response.json();
    renderResult(result);
  } catch (error) {
    console.warn("Server connection failed, falling back to local inference...");
    // Always fall back to runLocalInference now, which has a safe fallback
    const result = runLocalInference(finalText);
    renderResult(result);
  }
}

function runLocalInference(text) {
  const model = state.localModel;
  const words = text.toLowerCase().match(/\w+/g) || [];
  const scores = {};
  
  // Default values if model fails to load
  if (!model) {
      return {
        condition: "Calm",
        confidence: "Low",
        posteriorProbs: { "Worry": 10, "Feeling Low": 10, "Overwhelmed": 10, "Mood Swings": 10, "Relationship Challenges": 10, "Calm": 50 },
        summary: STATIC_SUGGESTIONS["Calm"].summary,
        tips: STATIC_SUGGESTIONS["Calm"].tips,
        affirmation: STATIC_SUGGESTIONS["Calm"].affirmation,
        isCrisis: text.toLowerCase().includes("kill") || text.toLowerCase().includes("suicide"),
        gender: state.gender,
        ageLabel: state.age
      };
  }
  
  // Naive Bayes Logic
  model.classes.forEach(cls => {
    let score = Math.log(model.class_priors[cls] || 1e-5);
    words.forEach(word => {
      if (model.word_probs[word]) {
        const wordCount = model.word_probs[word][cls] || 0;
        const totalWordsInClass = model.class_totals[cls];
        score += Math.log((wordCount + 1) / (totalWordsInClass + model.vocab_size));
      }
    });
    scores[cls] = score;
  });

  // Convert log scores to probabilities for UI
  const maxScore = Math.max(...Object.values(scores));
  const expScores = {};
  let totalExp = 0;
  Object.keys(scores).forEach(cls => {
    expScores[cls] = Math.exp(scores[cls] - maxScore);
    totalExp += expScores[cls];
  });

  const rawProbs = {};
  Object.keys(expScores).forEach(cls => {
    rawProbs[cls] = (expScores[cls] / totalExp) * 100;
  });

  // Map to UI Categories
  const uiProbs = { "Worry": 0, "Feeling Low": 0, "Overwhelmed": 0, "Mood Swings": 0, "Relationship Challenges": 0, "Calm": 0 };
  
  if (model) {
    Object.keys(rawProbs).forEach(cls => {
      const uiCat = CLASS_MAPPING[cls];
      if (uiCat) uiProbs[uiCat] += rawProbs[cls];
    });
  } else {
    // If no model at all, just fall back to normal
    uiProbs["Calm"] = 100;
  }

  // Normalize uiProbs to 100
  let uiTotal = 0;
  Object.values(uiProbs).forEach(v => uiTotal += v);
  if (uiTotal > 0) {
      Object.keys(uiProbs).forEach(k => uiProbs[k] = (uiProbs[k] / uiTotal) * 100);
  } else {
      uiProbs["Calm"] = 100;
  }

  // Find winner
  const winner = Object.entries(uiProbs).reduce((a, b) => b[1] > a[1] ? b : a)[0] || "Calm";
  
  // Keyword-based refinement (Frequency & Intensity)
  let confidence = "Medium";
  const lowerText = text.toLowerCase();
  if (lowerText.includes("all the time") || lowerText.includes("daily") || lowerText.includes("every day")) {
    confidence = "High";
  } else if (lowerText.includes("sometimes") || lowerText.includes("rarely") || lowerText.includes("usually")) {
    confidence = "Medium";
  }

  const staticData = STATIC_SUGGESTIONS[winner] || STATIC_SUGGESTIONS["Calm"];

  return {
    condition: winner,
    confidence: confidence,
    posteriorProbs: uiProbs,
    summary: staticData.summary,
    tips: staticData.tips,
    affirmation: staticData.affirmation,
    isCrisis: text.toLowerCase().includes("kill") || text.toLowerCase().includes("suicide"),
    gender: state.gender,
    ageLabel: state.age
  };
}


function renderResult(d) {
  const icon = ICONS[d.condition] || "✨";
  
  // ── Normalize probabilities to always sum to exactly 100% ──
  const rawProbs = d.posteriorProbs;
  const rawTotal = Object.values(rawProbs).reduce((a, b) => a + b, 0);
  const normalized = {};
  let normTotal = 0;
  const keys = Object.keys(rawProbs);
  keys.forEach((k, i) => {
    if (i === keys.length - 1) {
      normalized[k] = 100 - normTotal; // Last item absorbs rounding error
    } else {
      normalized[k] = Math.round((rawProbs[k] / rawTotal) * 100);
      normTotal += normalized[k];
    }
  });

  // Sort and build probability bars
  const sortedProbs = Object.entries(normalized).sort((a, b) => b[1] - a[1]);
  const probBars = sortedProbs.map(([name, val]) => `
    <div class="prob-item">
      <span class="prob-name">${name}</span>
      <div class="prob-track">
        <div class="prob-bar" style="width: ${val}%; opacity: ${name === d.condition ? 1 : 0.3}"></div>
      </div>
      <span class="prob-val" style="width: 40px; text-align: right; font-size: 0.8rem;">${val}%</span>
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
          <label class="group-label">Helpful Activities to try right now</label>
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
  state = { gender: null, age: null, text: "", responses: {} };
  document.getElementById("feelingInput").value = "";
  document.querySelectorAll(".select-box").forEach(el => el.classList.remove("selected"));
  document.getElementById("step3").style.display = "none";
  document.getElementById("step1").style.display = "block";
  document.getElementById("nextBtn").disabled = true;
  document.getElementById("analyzeBtn").disabled = false;
  document.getElementById("analyzeBtn").textContent = "Run Analysis";
  updateStepper(1);
}

// ── Shortcuts ──
document.addEventListener("keydown", (e) => {
  if (e.ctrlKey && e.key === "Enter") {
    if (document.getElementById("step2").style.display !== "none") analyze();
  }
});

// ── Dashboard Logic ──
let breakdownChart = null;

async function toggleDashboard() {
  const overlay = document.getElementById("dashboardOverlay");
  if (!overlay) return;
  const isHidden = overlay.style.display === "none" || overlay.style.display === "";
  
  if (isHidden) {
    overlay.style.display = "block";
    await fetchStats();
  } else {
    overlay.style.display = "none";
  }
}

function renderChart(breakdown) {
  const chartEl = document.getElementById('breakdownChart');
  if (!chartEl) return;
  
  const ctx = chartEl.getContext('2d');
  const labels = Object.keys(breakdown);
  const values = Object.values(breakdown);
  
  if (breakdownChart) {
    breakdownChart.destroy();
  }
  
  breakdownChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: values,
        backgroundColor: ['#6366f1', '#ec4899', '#8b5cf6', '#10b981', '#f59e0b', '#3b82f6'],
        borderWidth: 0,
        hoverOffset: 15
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#94a3b8', font: { family: 'Outfit', size: 11 }, padding: 15 }
        }
      },
      cutout: '75%'
    }
  });
}

function renderTrendChart(history, canvasId = 'trendChart') {
  const chartEl = document.getElementById(canvasId);
  if (!chartEl) return;
  
  const ctx = chartEl.getContext('2d');
  const dates = history.map(h => h.date);
  
  // Extract unique categories
  const categories = ["Worry", "Feeling Low", "Overwhelmed", "Mood Swings", "Relationship Challenges", "Calm"];
  const colors = {
    "Worry": "#6366f1", "Feeling Low": "#ec4899", "Overwhelmed": "#8b5cf6", 
    "Mood Swings": "#10b981", "Relationship Challenges": "#f59e0b", "Calm": "#3b82f6"
  };

  const datasets = categories.map(cat => ({
    label: cat,
    data: history.map(h => h.data[cat] || 0),
    backgroundColor: colors[cat],
    borderRadius: 4
  }));

  if (trendCharts[canvasId]) {
    trendCharts[canvasId].destroy();
  }
  
  trendCharts[canvasId] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: dates,
      datasets: datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { stacked: true, grid: { display: false }, ticks: { color: '#94a3b8' } },
        y: { stacked: true, beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8', stepSize: 1 } }
      },
      plugins: {
        legend: { display: true, position: 'top', labels: { color: '#94a3b8', font: { size: 10 } } },
        tooltip: { mode: 'index', intersect: false }
      }
    }
  });
}

let barCharts = {};
function renderBarChart(breakdown, canvasId = 'mainBarChart') {
  const chartEl = document.getElementById(canvasId);
  if (!chartEl) return;
  
  const ctx = chartEl.getContext('2d');
  const labels = Object.keys(breakdown);
  const values = Object.values(breakdown);
  
  if (barCharts[canvasId]) {
    barCharts[canvasId].destroy();
  }
  
  barCharts[canvasId] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        data: values,
        backgroundColor: '#6366f1',
        borderRadius: 8,
        barThickness: 20
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
        x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
      },
      plugins: {
        legend: { display: false }
      }
    }
  });
}

function populateRecentTable(recent) {
  const body = document.getElementById("recentLogBody");
  if (!body) return;
  
  body.innerHTML = recent.map(row => `
    <tr>
      <td>${row.time}</td>
      <td style="text-transform: capitalize;">${row.gender}</td>
      <td>${row.age}</td>
      <td><span class="badge" style="background: rgba(99,102,241,0.1); color: #818cf8; border: none; padding: 4px 10px;">${row.result}</span></td>
      <td><span style="color: #10b981;">●</span> ${row.conf}</td>
    </tr>
  `).join('');
}

