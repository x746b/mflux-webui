"use strict";

const MFChatPreferences = (() => {
  const KEY = "mflux-web:chat-preferences";
  function normalize(value) {
    const model = value?.model === "gpt-6-sol" ? "gpt-6.1-sol" : value?.model;
    return {
      enabled: value?.enabled !== false,
      provider: value?.provider === "omlx" ? "omlx" : "openai",
      model: ["gpt-6-luna", "gpt-6.1-sol"].includes(model) ? model : "gpt-6-luna",
      instructions: typeof value?.instructions === "string" ? value.instructions.slice(0, 4000) : "",
    };
  }
  function load() {
    let value;
    try { value = JSON.parse(localStorage.getItem(KEY) || "null"); } catch { /* defaults */ }
    const normalized = normalize(value);
    if (value?.model === "gpt-6-sol") {
      try { localStorage.setItem(KEY, JSON.stringify({ ...value, model: normalized.model })); }
      catch { /* migration still applies for this page */ }
    }
    return normalized;
  }
  let current = load();
  function read() { return { ...current }; }
  function save(value) {
    current = normalize(value);
    let saved = true;
    try { localStorage.setItem(KEY, JSON.stringify(current)); }
    catch { saved = false; }
    window.dispatchEvent(new Event("mflux-chat-preferences"));
    return saved;
  }
  window.addEventListener("storage", (event) => {
    if (event.key === KEY || event.key === null) {
      current = load();
      window.dispatchEvent(new Event("mflux-chat-preferences"));
    }
  });
  return { read, save };
})();
