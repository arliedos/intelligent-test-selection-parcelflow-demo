/* Shared client-side validation and safe-rendering helpers for the minimal
 * ParcelFlow demo UI. Plain stdlib-only JS (no bundler, no framework). */

const DESTINATIONS = ["DOMESTIC", "REGIONAL", "INTERNATIONAL"];
const SERVICES = ["STANDARD", "EXPRESS"];

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function validateQuoteForm({ weightG, destination, service }) {
  const errors = [];
  const weight = Number(weightG);
  if (!Number.isInteger(weight) || weight <= 0) {
    errors.push("Weight must be a positive whole number of grams.");
  }
  if (!DESTINATIONS.includes(destination)) {
    errors.push("Destination must be one of: " + DESTINATIONS.join(", "));
  }
  if (!SERVICES.includes(service)) {
    errors.push("Service must be one of: " + SERVICES.join(", "));
  }
  return { valid: errors.length === 0, errors };
}

const ParcelFlowValidation = { escapeHtml, validateQuoteForm, DESTINATIONS, SERVICES };

if (typeof module !== "undefined" && module.exports) {
  module.exports = ParcelFlowValidation;
}
if (typeof window !== "undefined") {
  window.ParcelFlowValidation = ParcelFlowValidation;
}

