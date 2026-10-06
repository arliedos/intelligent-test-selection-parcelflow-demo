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

// UI-level role visibility: EXPRESS is hidden from the customer role in the
// quote form's service selector. This narrows what customers are offered;
// it is not a substitute for the server's environment-driven EXPRESS gate
// (see REQ-QUOTE-3), which still applies independently of role.
function visibleServicesForRole(role) {
  if (role === "ops" || role === "admin") {
    return SERVICES.slice();
  }
  return SERVICES.filter((service) => service !== "EXPRESS");
}

const ParcelFlowValidation = { escapeHtml, validateQuoteForm, visibleServicesForRole, DESTINATIONS, SERVICES };

if (typeof module !== "undefined" && module.exports) {
  module.exports = ParcelFlowValidation;
}
if (typeof window !== "undefined") {
  window.ParcelFlowValidation = ParcelFlowValidation;
}

