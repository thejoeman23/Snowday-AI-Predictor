const predictApi = "https://snowday-ai-predictor.fly.dev/predict";
const counterApi = "https://snowday-ai-predictor.fly.dev/count";
const explainerApi = "https://snowday-ai-predictor.fly.dev/explain";
const locationApi = "https://geocoding-api.open-meteo.com/v1/search?"

/* -------------------------
   CACHE + STARTUP
-------------------------- */

const cachedCounter = localStorage.getItem("counter_value");
const cachedPredictions = localStorage.getItem("snowday_predictions");
const cachedExplanations = localStorage.getItem("prediction_explanations");
const cachedLocationData = localStorage.getItem("location_data");

const cityInput = document.getElementById("cityInput");
const ghostInput = document.getElementById("ghostInput");

if (!cachedLocationData) {
  cityInput?.focus();
  // getLocation();
}
else {
  const cachedName =
    JSON.parse(cachedLocationData).name + ", " +
    JSON.parse(cachedLocationData).admin1;

  cityInput.value = cachedName;
  ghostInput.value = cachedName;

  requestAnimationFrame(() => {
    resizeSearchInput();
  });
}

function getLocation() {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(success, error);
  } else { 
    x.innerHTML = "Geolocation is not supported by this browser.";
  }
}

async function success(position) {
  const { latitude, longitude } = position.coords;

  try {
    const res = await fetch(
      `https://geocoding-api.open-meteo.com/v1/reverse?latitude=${latitude}&longitude=${longitude}&count=1&language=en`
    );

    const data = await res.json();
    if (!data.results || !data.results.length) return;

    const location = data.results[0];

    localStorage.setItem("location_data", JSON.stringify(location));
    location.reload();

  } catch (err) {
    console.error("Failed to reverse-geocode location", err);
  }
}

function error() { alert("Sorry, no position available."); }

/* -------------------------
    CITY AUTOCOMPLETE
-------------------------- */

function measureTextWidth(text, referenceEl) {
  const span = document.createElement("span");
  span.style.position = "absolute";
  span.style.visibility = "hidden";
  span.style.whiteSpace = "pre";
  span.style.font = getComputedStyle(referenceEl).font;
  span.textContent = text || referenceEl.placeholder;

  document.body.appendChild(span);
  const width = span.offsetWidth;
  document.body.removeChild(span);

  return width;
}

function resizeSearchInput() {
  const text = ghostInput.value || cityInput.placeholder;
  const width = measureTextWidth(text, cityInput);
  cityInput.style.width = `${width + 6}px`;
}

requestAnimationFrame(() => {
  resizeSearchInput();
});

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
      `name=${encodeURIComponent(typed)}&count=10&language=en&format=json&countryCode=CA,SE`
    );

    const data = await res.json();
    if (!data.results?.length) return;

    const placeData = data.results[0];
    const fullName = `${placeData.name}, ${placeData.admin1}`;

    const fullLower = fullName.toLowerCase();
    const typedLower = typed.toLowerCase();

    if (fullLower.startsWith(typedLower)) {
      suggestion = fullName.slice(typed.length);
      suggestionData = placeData;

      ghostInput.value = typed + suggestion;
      resizeSearchInput();
    }

  }, 250);
});

cityInput.addEventListener("keydown", (e) => {
  if (e.key === "Backspace" || e.key === "Delete") {
    suggestion = "";
    suggestionData = null;
  }

  if (e.key == "Tab" || e.key == "ArrowRight" || e.key == "Enter") {
    if (suggestion) {
      e.preventDefault();
      cityInput.value += suggestion;
      suggestion = cityInput.value;

      localStorage.setItem("location_data", JSON.stringify(suggestionData));
      location.reload();
    }
  }
});

/* -------------------------
   ODOMETER REGISTRY
-------------------------- */

const odometers = new Map();

function getOdometer(el, startValue = 0) {
  if (odometers.has(el)) return odometers.get(el);

  const odo = new Odometer({
    el,
    value: startValue,
    format: "(ddd)",   // change if you want decimals
    theme: "default"
  });

  odometers.set(el, odo);
  return odo;
}

function updateOdometer(el, newValue) {
  const current = Number(el.textContent) || 0;
  const odo = getOdometer(el, current);
  odo.update(newValue);
}

/* -------------------------
   UI UPDATERS
-------------------------- */

function updateProbabilities(list) {
  // Current day
  const currentPercentEl = document.querySelector(".odometer");
  const currentLabelEl = document.querySelector(".current-label");

  updateOdometer(
    currentPercentEl,
    Number(list[0].snow_day_probability)
  );
  currentLabelEl.textContent = list[0].weekday;

  // Other days
  const metricValues = document.querySelectorAll(".metric-value .odometer");
  const metricLabels = document.querySelectorAll(".metric-label");

  for (let i = 1; i < list.length; i++) {
    // i = 1 since list[0] was already used for the currect percentage
    const index = i - 1; // i -1 because metricValues/Labels start at 0 

    updateOdometer(
      metricValues[index],
      Number(list[i].snow_day_probability)
    );

    metricLabels[index].textContent = list[i].weekday;
  }
}

function updateOthers(value) {
  const othersEl = document.querySelector(".others-amount .odometer");
  updateOdometer(othersEl, Number(value));
}

function updateExplainer(list) {
  const explainerElmts = document.querySelectorAll(".reason");
  for (let i = 0; i < list.length; i++){
    explainerElmts[i].textContent = list[i].reason;
  }

  popReasons();
}

function popReasons(containerSelector = ".reasons") {
  const container = document.querySelector(containerSelector);
  if (!container) return;

  const items = [...container.querySelectorAll(".reason")];

  // assign stagger index
  items.forEach((el, idx) => el.style.setProperty("--i", idx));

  // retrigger animation reliably
  container.classList.remove("is-visible");
  // force reflow so animations restart
  void container.offsetWidth;

  container.classList.add("is-visible");
}

/* -------------------------
   APPLY CACHED UI
-------------------------- */

if (cachedCounter !== null) {
  updateOthers(Number(cachedCounter));
}

if (cachedPredictions) {
  try {
    updateProbabilities(JSON.parse(cachedPredictions));
  } catch (e) {
    console.error("Failed to parse cached snowday_predictions", e);
  }
}

if (cachedExplanations) {
  try {
    updateExplainer(JSON.parse(cachedExplanations));
  } catch (e) {
    console.error("Failed to parse cached prediction_explanations", e);
  }
}

/* -------------------------
   FETCH FRESH DATA
-------------------------- */

if (cachedLocationData) {

  const lat = JSON.parse(cachedLocationData).latitude;
  const lon = JSON.parse(cachedLocationData).longitude;

  fetch(predictApi + `?lat=${lat}&lon=${lon}`)
    .then(r => r.ok ? r.json() : Promise.reject())
    .then(data => {
      localStorage.setItem("snowday_predictions", JSON.stringify(data));
      setTimeout(function(){
        updateProbabilities(data);
      }, 2000);
    })
    .catch(console.error);

  fetch(explainerApi + `?lat=${lat}&lon=${lon}`)
    .then(r => r.ok ? r.json() : Promise.reject())
    .then(reasons => {
      if (JSON.stringify(reasons) != cachedExplanations)
      {
        localStorage.setItem("prediction_explanations", JSON.stringify(reasons));
        setTimeout(function(){
          updateExplainer(reasons);
        }, 2000);
      }
    })
    .catch(console.error);

  fetch(counterApi)
    .then(r => r.ok ? r.text() : Promise.reject())
    .then(counter => {
      localStorage.setItem("counter_value", counter);
      setTimeout(function(){
        updateOthers(Number(counter))
      }, 2000);

    })
    .catch(console.error);

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