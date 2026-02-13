const predictApi = "https://snowday-ai-predictor.fly.dev/predict";
const counterApi = "https://snowday-ai-predictor.fly.dev/count";
const explainerApi = "https://snowday-ai-predictor.fly.dev/explain";
const locationApi = "https://geocoding-api.open-meteo.com/v1/search?";

/* -------------------------
   LOADING STATE
-------------------------- */


const loadingState = {
  predictions: false,
  explanations: false,
  counter: false,
  alreadyLoadedOnce: false
};

let pendingData = {
  predictions: null,
  explanations: null,
  counter: null
};

function showLoadingScreen(isVisible) {
  const el = document.querySelector(".loading-screen");
  if (!el) return;
  el.classList.toggle("hidden", !isVisible);
}

function allReady() {
  return (
    loadingState.predictions &&
    loadingState.explanations &&
    loadingState.counter
  );
}

function hydrateUI() {
  updateProbabilities(pendingData.predictions);
  updateExplainer(pendingData.explanations);
  updateOthers(pendingData.counter);
  updateURL();
}

function checkLoadingComplete() {
  if (!allReady()) return;

  // First-ever render (cached or first fetch)
  if (!loadingState.alreadyLoadedOnce) {
    hydrateUI();
    showLoadingScreen(false);
    loadingState.alreadyLoadedOnce = true;
    return;
  }

  // Subsequent fresh-data update
  setTimeout(() => {
    hydrateUI();
  }, 2500);
}


/* -------------------------
   CACHE + STARTUP
-------------------------- */

function clearCache() {
  localStorage.removeItem("snowday_predictions");
  localStorage.removeItem("prediction_explanations");
  localStorage.removeItem("counter_value");
}

const cachedPredictions = (() => {
  const v = localStorage.getItem("snowday_predictions");
  return v && v !== "null" ? v : null;
})();

const cachedExplanations = (() => {
  const v = localStorage.getItem("prediction_explanations");
  return v && v !== "null" ? v : null;
})();

const cachedCounter = (() => {
  const v = localStorage.getItem("counter_value");
  return v && v !== "null" ? v : null;
})();

const cachedLocationData = localStorage.getItem("location_data");

const cityForm = document.querySelector(".city-form");
const cityInput  = document.getElementById("cityInput");
const ghostInput = document.getElementById("ghostInput");



/* -------------------------
   LOCATION HANDLING
-------------------------- */

if (!cachedLocationData) {
  cityInput?.focus();
  resizeSearchInput();
  document.querySelector(".loading-text").textContent =
    "Search for your city to get started.";

  clearCache(); // Just incase they were on an old version of the site where there was caching but no location caching
} else {
  const loc = JSON.parse(cachedLocationData);
  const name = `${loc.name}, ${loc.admin1}`;

  cityInput.value = name;
  ghostInput.value = name;

  requestAnimationFrame(resizeSearchInput);
}

/* -------------------------
   AUTOCOMPLETE
-------------------------- */

function measureTextWidth(text, ref) {
  const span = document.createElement("span");
  span.style.visibility = "hidden";
  span.style.position = "absolute";
  span.style.whiteSpace = "pre";
  span.style.font = getComputedStyle(ref).font;
  span.textContent = text;
  document.body.appendChild(span);
  const width = span.offsetWidth;
  span.remove();
  return width;
}

function resizeSearchInput() {
  const text = ghostInput.value || cityInput.placeholder;
  cityInput.style.width = `${measureTextWidth(text, cityInput) + 6}px`;
}

let debounceTimer;
let suggestion = "";
let suggestionData = null;

cityInput.addEventListener("input", () => {
  clearTimeout(debounceTimer);

  const typed = cityInput.value;
  ghostInput.value = typed;
  resizeSearchInput();

  if (typed.length < 2) return;

  debounceTimer = setTimeout(async () => {
    const res = await fetch(
      locationApi +
      `name=${encodeURIComponent(typed)}&count=50&language=en&format=json&countryCode=CA`
    );

    const data = await res.json();
    if (!data.results?.length) return;

    const place = data.results[0];
    const full = `${place.name}, ${place.admin1}`;

    if (full.toLowerCase().startsWith(typed.toLowerCase())) {
      suggestion = full.slice(typed.length);
      suggestionData = place;
      ghostInput.value = typed + suggestion;
      resizeSearchInput();
    }
  }, 250);
});

cityInput.addEventListener("keydown", e => {
  if (e.key === "Backspace" || e.key === "Delete") {
    suggestion = "";
    suggestionData = null;
  }

  if ((e.key === "Enter" || e.key === "Tab" || e.key === "ArrowRight") && suggestionData) {
    e.preventDefault();
    autocomplete();
  }
});

cityForm.addEventListener("submit", e => {
  if (!suggestionData) return;

  e.preventDefault();
  confirmCity();
});

function autocomplete()
{
  cityInput.value += suggestion;

  clearCache();
  localStorage.setItem("location_data", JSON.stringify(suggestionData));
  location.reload();
}

/* -------------------------
   ODOMETERS
-------------------------- */

const odometers = new Map();

function getOdometer(el, start = 0) {
  if (odometers.has(el)) return odometers.get(el);

  const odo = new Odometer({
    el,
    value: start,
    format: "(ddd)",
    theme: "default"
  });

  odometers.set(el, odo);
  return odo;
}

function updateOdometer(el, value) {
  const odo = getOdometer(el, Number(el.textContent) || 0);
  odo.update(value);
}

/* -------------------------
   UI UPDATERS (NO LOADING LOGIC)
-------------------------- */

function roundTo5(percent) {
  return Math.round(percent / 5) * 5;
}

function updateURL() {
  const slug = cityInput.value
  .toLowerCase()
  .replace(/\s+/g, "-")
  .replace(/[^a-z-]/g, "");

  window.history.pushState({}, "", `?city=${slug}`);
}

function updateProbabilities(list) {
  const current = document.querySelector(".odometer");
  const label = document.querySelector(".current-label");

  updateOdometer(current, roundTo5(Number(list[0].snow_day_probability)));
  label.textContent = list[0].weekday;

  const values = document.querySelectorAll(".metric-value .odometer");
  const labels = document.querySelectorAll(".metric-label");

  for (let i = 1; i < list.length; i++) {
    updateOdometer(values[i - 1], roundTo5(Number(list[i].snow_day_probability)));
    labels[i - 1].textContent = list[i].weekday;
  }
}

function updateOthers(value) {
  updateOdometer(
    document.querySelector(".others-amount .odometer"),
    Number(value)
  );
}

function updateExplainer(list) {
  const els = document.querySelectorAll(".reason");
  list.forEach((r, i) => els[i].textContent = r.reason);
  popReasons();
}

function popReasons() {
  const container = document.querySelector(".reasons");
  container.classList.remove("is-visible");
  void container.offsetWidth;
  container.classList.add("is-visible");
}

/* ------------------------- 
    APPLY CACHED UI 
-------------------------- */ 

let hadAnyCache = false;

if (cachedPredictions) {
  try {
    pendingData.predictions = JSON.parse(cachedPredictions);
    loadingState.predictions = true;
    hadAnyCache = true;
  } catch {}
}

if (cachedExplanations) {
  try {
    pendingData.explanations = JSON.parse(cachedExplanations);
    loadingState.explanations = true;
    hadAnyCache = true;
  } catch {}
}

if (cachedCounter !== null) {
  const num = Number(cachedCounter);
  if (!Number.isNaN(num)) {
    pendingData.counter = num;
    loadingState.counter = true;
    hadAnyCache = true;
  }
}

if (hadAnyCache) {
  checkLoadingComplete(); // immediate render from cache
}

/* -------------------------
   FETCH DATA
-------------------------- */

if (cachedLocationData) {
  const loc = JSON.parse(cachedLocationData);
  const lat = loc.latitude;
  const lon = loc.longitude;

  fetch(predictApi + `?lat=${lat}&lon=${lon}`)
    .then(r => r.json())
    .then(data => {
      localStorage.setItem("snowday_predictions", JSON.stringify(data));
      pendingData.predictions = data;
      loadingState.predictions = true;
      checkLoadingComplete();
    });

  fetch(explainerApi + `?lat=${lat}&lon=${lon}`)
    .then(r => r.json())
    .then(data => {
      localStorage.setItem("prediction_explanations", JSON.stringify(data));
      pendingData.explanations = data;
      loadingState.explanations = true;
      checkLoadingComplete();
    });

  fetch(counterApi)
    .then(r => r.text())
    .then(val => {
      const num = Number(val);
      localStorage.setItem("counter_value", String(num));
      pendingData.counter = num;
      loadingState.counter = true;
      checkLoadingComplete();
    });
}

/* -------------------------
   FEEDBACK SUBMISSION
-------------------------- */

const button = document.getElementById("submitFeedback");
const box = document.getElementById("feedbackBox");
const statusMsg = document.getElementById("submitStatus");

button.addEventListener("click", async () => {
  const content = box.value.trim();
  if (!content) return box.focus();

  button.disabled = true;

  try {
    await fetch(
      "https://discord.com/api/webhooks/1455940293374251171/usYpb_FqdvLcCxJkfFnKSCKPbvSTGpEhSYcrCfHurV43IIwArVN7xRjQo70csIgkPDy0",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: `📩 New feedback:\n\n${content}`
        })
      }
    );

    statusMsg.textContent = "Submitted — thank you!";
    box.value = "";

  } catch {
    statusMsg.textContent = "Submission failed. Try again later.";
  }

  button.disabled = false;
});

const ctx = document.getElementById('test');

// 0–23 hours
const hours = [
  "0","1","2","3","4","5","6","7",
  "8","9","10","11","12","13","14","15",
  "16","17","18","19","20","21","22","23"
];

// TEST DATA (realistic winter storm pattern)

// mm per hour
const precipitationData = [
  0,0,0,0.2,0.5,1.2,2.0,2.8,
  3.5,4.2,3.8,3.0,2.4,1.8,1.2,0.8,
  0.5,0.3,0.2,0.1,0,0,0,0
];

// cm per hour
const snowData = [
  0,0,0,0.1,0.3,0.8,1.5,2.2,
  2.8,3.1,2.6,2.0,1.6,1.2,0.8,0.5,
  0.3,0.2,0.1,0,0,0,0,0
];

// km/h gusts
const gustData = [
  10,12,15,18,22,28,35,40,
  45,50,55,52,48,42,38,34,
  30,26,22,18,15,12,10,8
];

// km visibility (drops during storm)
const visibilityData = [
  16,16,15,12,10,7,5,3,
  2,1.5,1.2,1.5,2,3,4,6,
  8,10,12,14,16,16,16,16
];

// °C
const tempData = [
  -6,-7,-8,-8,-9,-9,-10,-10,
  -9,-8,-7,-6,-5,-4,-3,-3,
  -4,-5,-6,-6,-7,-7,-7,-6
];

const mixedChart = new Chart(ctx, {
  data: {
    labels: hours,
    datasets: [
      {
        type: 'bar',
        label: 'Precipitation (mm)',
        data: precipitationData,
        yAxisID: 'yPrecip'
      },
      {
        type: 'bar',
        label: 'Snowfall (cm)',
        data: snowData,
        yAxisID: 'yPrecip'
      },
      {
        type: 'line',
        label: 'Wind Gusts (km/h)',
        data: gustData,
        yAxisID: 'yWind',
        tension: 0.35,
        pointRadius: 0
      },
      {
        type: 'line',
        label: 'Visibility (km)',
        data: visibilityData,
        yAxisID: 'yVis',
        tension: 0.35,
        pointRadius: 0
      },
      {
        type: 'line',
        label: 'Temperature (°C)',
        data: tempData,
        yAxisID: 'yTemp',
        tension: 0.35,
        pointRadius: 0
      }
    ]
  },
  options: {
    responsive: true,
    interaction: {
      mode: 'index',
      intersect: false
    },
    scales: {
      x: {
        title: {
          display: true,
          text: 'Hour of Day'
        }
      },

      yPrecip: {
        type: 'linear',
        position: 'left',
        title: {
          display: true,
          text: 'Precipitation / Snow'
        }
      },

      yTemp: {
        type: 'linear',
        position: 'left',
        offset: true,
        title: {
          display: true,
          text: 'Temperature (°C)'
        }
      },

      yWind: {
        type: 'linear',
        position: 'right',
        title: {
          display: true,
          text: 'Wind Gusts (km/h)'
        },
        grid: {
          drawOnChartArea: false
        }
      },

      yVis: {
        type: 'linear',
        position: 'right',
        offset: true,
        title: {
          display: true,
          text: 'Visibility (km)'
        },
        grid: {
          drawOnChartArea: false
        }
      }
    }
  }
}); 