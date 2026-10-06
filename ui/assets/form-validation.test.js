const test = require("node:test");
const assert = require("node:assert/strict");
const { escapeHtml, validateQuoteForm, visibleServicesForRole, DESTINATIONS, SERVICES } = require("./form-validation.js");

test("escapeHtml escapes angle brackets and ampersands", () => {
  assert.equal(escapeHtml("<b>&</b>"), "&lt;b&gt;&amp;&lt;/b&gt;");
});

test("escapeHtml escapes quotes to prevent attribute injection", () => {
  assert.equal(escapeHtml(`"'`), "&quot;&#39;");
});

test("validateQuoteForm accepts a well-formed request", () => {
  const result = validateQuoteForm({ weightG: "500", destination: "DOMESTIC", service: "STANDARD" });
  assert.equal(result.valid, true);
  assert.deepEqual(result.errors, []);
});

test("validateQuoteForm rejects non-numeric weight", () => {
  const result = validateQuoteForm({ weightG: "abc", destination: "DOMESTIC", service: "STANDARD" });
  assert.equal(result.valid, false);
  assert.ok(result.errors.length > 0);
});

test("validateQuoteForm rejects unknown destination", () => {
  const result = validateQuoteForm({ weightG: "500", destination: "MOON", service: "STANDARD" });
  assert.equal(result.valid, false);
});

test("validateQuoteForm rejects unknown service", () => {
  const result = validateQuoteForm({ weightG: "500", destination: "DOMESTIC", service: "OVERNIGHT" });
  assert.equal(result.valid, false);
});

test("DESTINATIONS and SERVICES enumerate the supported baseline values", () => {
  assert.deepEqual(DESTINATIONS, ["DOMESTIC", "REGIONAL", "INTERNATIONAL"]);
  assert.deepEqual(SERVICES, ["STANDARD", "EXPRESS"]);
});

test("visibleServicesForRole hides EXPRESS from the customer role in the UI selector", () => {
  assert.deepEqual(visibleServicesForRole("customer"), ["STANDARD"]);
});

test("visibleServicesForRole shows all services for ops and admin roles", () => {
  assert.deepEqual(visibleServicesForRole("ops"), ["STANDARD", "EXPRESS"]);
  assert.deepEqual(visibleServicesForRole("admin"), ["STANDARD", "EXPRESS"]);
});

test("visibleServicesForRole falls back to STANDARD-only for an unknown role", () => {
  assert.deepEqual(visibleServicesForRole("bogus"), ["STANDARD"]);
});
