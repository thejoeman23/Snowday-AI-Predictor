const predictApi = "https://api.snowdaypredictor.io/predict";
const counterApi = "https://api.snowdaypredictor.io/count";

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
  const currentPercentEl = document.querySelector(".current-percent");
  const currentLabelEl = document.querySelector(".current-label");

  updateOdometer(
    currentPercentEl,
    Number(list[0].snow_day_probability)
  );
  currentLabelEl.textContent = list[0].weekday;

  // Other days
  const metricValues = document.querySelectorAll(".metric-value");
  const metricLabels = document.querySelectorAll(".metric-label");

  for (let i = 1; i < list.length; i++) {
    updateOdometer(
      metricValues[i - 1],
      Number(list[i].snow_day_probability)
    );
    metricLabels[i - 1].textContent = list[i].weekday;
  }
}

function updateOthers(value) {
  const othersEl = document.querySelector(".others-amount");
  updateOdometer(othersEl, Number(value));
}

/* -------------------------
   CACHE FIRST
-------------------------- */

const cachedCounter = localStorage.getItem("counter_value");
if (cachedCounter !== null) {
  updateOthers(Number(cachedCounter));
}

const cachedPredictions = localStorage.getItem("snowday_predictions");
if (cachedPredictions) {
  updateProbabilities(JSON.parse(cachedPredictions));
}

/* -------------------------
   FETCH FRESH DATA
-------------------------- */

fetch(predictApi)
  .then(r => r.ok ? r.json() : Promise.reject())
  .then(data => {
    localStorage.setItem("snowday_predictions", JSON.stringify(data));
    updateProbabilities(data);
  })
  .catch(console.error);

fetch(counterApi)
  .then(r => r.ok ? r.text() : Promise.reject())
  .then(counter => {
    localStorage.setItem("counter_value", counter);
    updateOthers(Number(counter));
  })
  .catch(console.error);

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
