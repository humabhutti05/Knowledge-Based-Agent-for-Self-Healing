// ── Icons Map ──
const ICONS = {
  "Anxiety": "😰", "Depression": "😔", "Stress": "😤",
  "Normal": "😊", "Suicidal": "🆘", "Bipolar": "🔄", "Personality disorder": "🧩"
};

// ── State ──
let state = {
  gender: null,
  age: null,
  text: ""
};

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

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, gender: state.gender, age: state.age })
    });
    const data = await res.json();
    renderResult(data);
  } catch (err) {
    document.getElementById("resultArea").innerHTML = `<div class="card glass">Error: ${err.message}</div>`;
    btn.disabled = false;
    btn.textContent = "Run Neural Inference";
  }
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

