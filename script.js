const predictApi = "https://api.snowdaypredictor.io/predict";
const counterApi = "https://api.snowdaypredictor.io/count";

function updateProbabilities(list) {
    document.querySelector(".current-percent").textContent =
    list[0].snow_day_probability + "%";
    document.querySelector(".current-label").textContent =
    list[0].weekday;

    const metricValues = document.querySelectorAll(".metric-value");
    const metricLabels = document.querySelectorAll(".metric-label");

    for (let i = 1; i < list.length; i++) {
    metricValues[i - 1].textContent = list[i].snow_day_probability + "%";
    metricLabels[i - 1].textContent = list[i].weekday;
    }
}

function updateOthers(value) {
    document.querySelector(".others-amount").textContent =
    value + " others are hoping for a snow day 🔥";
}

// ✅ READ CACHE FIRST
const cachedCounter = localStorage.getItem("counter_value");
if (cachedCounter !== null) {
    updateOthers(Number(cachedCounter));
}

const cachedPredictions = localStorage.getItem("snowday_predictions");
if (cachedPredictions) {
    const parsed = JSON.parse(cachedPredictions);
    updateProbabilities(parsed);
}

// ✅ FETCH FRESH
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

  // Feedback submission

  const button = document.getElementById("submitFeedback");
  const box = document.getElementById("feedbackBox");
  const statusMsg = document.getElementById("submitStatus");

  button.addEventListener("click", async () => {
    const content = box.value.trim();

    if (!content) {
      box.focus();
      return;
    }

    button.disabled = true;

    try {
      await fetch("https://discord.com/api/webhooks/1455940293374251171/usYpb_FqdvLcCxJkfFnKSCKPbvSTGpEhSYcrCfHurV43IIwArVN7xRjQo70csIgkPDy0", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: `📩 New feedback:\n \n ${content}`
        })
      });

      statusMsg.textContent = "Submitted — thank you!";
      box.value = "";

    } catch (err) {
      statusMsg.textContent = "Submission failed. Try again later.";
    }

    button.disabled = false;
  });