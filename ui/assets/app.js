/* Minimal ParcelFlow demo UI wiring. Talks to the local API over fetch().
 * No framework; relies on form-validation.js for client-side checks and safe
 * rendering (escapeHtml) before inserting any server-derived text. */
/* global document, fetch */

(function () {
  const { escapeHtml, validateQuoteForm, visibleServicesForRole, DESTINATIONS } = window.ParcelFlowValidation;

  function byId(id) {
    return document.getElementById(id);
  }

  function renderErrors(container, errors) {
    container.innerHTML = "";
    container.hidden = errors.length === 0;
    errors.forEach((message) => {
      const li = document.createElement("li");
      li.textContent = message; // textContent, not innerHTML: safe by construction
      container.appendChild(li);
    });
  }

  function renderQuoteResult(container, quote) {
    container.innerHTML =
      "<p>Quote <strong>" + escapeHtml(quote.quote_id) + "</strong>: " +
      escapeHtml(String(quote.amount_cents)) + " " + escapeHtml(quote.currency) + " cents</p>";
  }

  async function submitQuote(event) {
    event.preventDefault();
    const weightG = byId("weight_g").value;
    const destination = byId("destination").value;
    const service = byId("service").value;
    const errorsEl = byId("quote-errors");
    const resultEl = byId("quote-result");

    const { valid, errors } = validateQuoteForm({ weightG, destination, service });
    if (!valid) {
      renderErrors(errorsEl, errors);
      resultEl.innerHTML = "";
      return;
    }
    renderErrors(errorsEl, []);

    const role = byId("role").value;
    const response = await fetch("/api/quotes", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Demo-Role": role },
      body: JSON.stringify({ weight_g: Number(weightG), destination, service }),
    });
    const payload = await response.json();
    if (!response.ok) {
      renderErrors(errorsEl, [payload.error || "request failed"]);
      return;
    }
    renderQuoteResult(resultEl, payload);
  }

  function populateSelect(selectEl, values) {
    const previous = selectEl.value;
    selectEl.innerHTML = "";
    values.forEach((value) => {
      const opt = document.createElement("option");
      opt.value = value;
      opt.textContent = value;
      selectEl.appendChild(opt);
    });
    if (values.includes(previous)) {
      selectEl.value = previous;
    }
  }

  function refreshServicesForRole() {
    const role = byId("role").value;
    populateSelect(byId("service"), visibleServicesForRole(role));
  }

  document.addEventListener("DOMContentLoaded", () => {
    populateSelect(byId("destination"), DESTINATIONS);
    refreshServicesForRole();
    byId("role").addEventListener("change", refreshServicesForRole);
    byId("quote-form").addEventListener("submit", submitQuote);
  });
})();
