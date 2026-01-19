const predictApi = "https://snowday-ai-predictor.fly.dev/predict";
const counterApi = "https://snowday-ai-predictor.fly.dev/count";
const explainerApi = "https://snowday-ai-predictor.fly.dev/explain";


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

const cachedExplanations = localStorage.getItem("prediction_explanations");
if (cachedExplanations) {
  updateExplainer(JSON.parse(cachedExplanations));
}

/* -------------------------
   FETCH FRESH DATA
-------------------------- */

fetch(predictApi)
  .then(r => r.ok ? r.json() : Promise.reject())
  .then(data => {
    localStorage.setItem("snowday_predictions", JSON.stringify(data));
    setTimeout(function(){
      updateProbabilities(data);
    }, 2000);
  })
  .catch(console.error);

fetch(explainerApi)
  .then(r => r.ok ? r.json() : Promise.reject())
  .then(data => {
    if (JSON.stringify(data) != cachedExplanations)
    {
      localStorage.setItem("prediction_explanations", JSON.stringify(data));
      setTimeout(function(){
        updateProbabilities(data);
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
