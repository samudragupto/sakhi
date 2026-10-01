/**
 * Main Application Orchestrator Module
 */

import { playTTS, startRecording, stopRecording } from "./audio.js";
import { setupPrivacyHandlers } from "./privacy.js";
import { renderQuickReplies, renderResult, updateCaption, updateProgress } from "./ui.js";

const localeResponse = await fetch("/locales/hi.json");
const locale = await localeResponse.json();
const translate = (key) => key.split(".").reduce((value, part) => value?.[part], locale);
window.sakhiLocale = locale;
window.sakhiTranslate = translate;
document.title = translate("ui.document_title");

document.querySelectorAll("[data-i18n]").forEach((element) => {
  element.textContent = translate(element.dataset.i18n);
});
document.querySelectorAll("[data-i18n-aria-label]").forEach((element) => {
  element.setAttribute("aria-label", translate(element.dataset.i18nAriaLabel));
});
document.querySelectorAll("[data-i18n-alt]").forEach((element) => {
  element.setAttribute("alt", translate(element.dataset.i18nAlt));
});
document.querySelectorAll(".progress-dots .dot").forEach((dot) => {
  dot.title = translate("ui.progress_step").replace("{step}", dot.dataset.step);
});

const recipeSteps = document.getElementById("recipe-steps");
locale.privacy.recipe_steps.forEach((step) => {
  const paragraph = document.createElement("p");
  paragraph.textContent = step;
  recipeSteps.appendChild(paragraph);
});

let sessionId = sessionStorage.getItem("sakhi_session_id") || crypto.randomUUID();
sessionStorage.setItem("sakhi_session_id", sessionId);

let isRecording = false;
let currentStep = 0;
let lastEligibilityData = null;
let modalReturnFocus = null;

function openModal(modal) {
  modalReturnFocus = document.activeElement;
  modal.hidden = false;
  modal.querySelector("button")?.focus();
}

function closeModal(modal) {
  modal.hidden = true;
  if (modalReturnFocus instanceof HTMLElement) modalReturnFocus.focus();
  modalReturnFocus = null;
}

async function sendChat(message) {
  updateCaption(translate("ui.working"));
  try {
    const res = await fetch("/api/v1/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message: message }),
    });

    if (res.ok) {
      const data = await res.json();
      handleChatResponse(data);
    } else {
      updateCaption(translate("ui.contact_error"));
    }
  } catch {
    updateCaption(translate("ui.network_error"));
  }
}

function handleChatResponse(data) {
  updateCaption(data.caption);
  playTTS(data.speech_text);

  currentStep++;
  updateProgress(Math.min(currentStep, 5));

  if (data.ui_action === "SHOW_RESULT" && data.data) {
    lastEligibilityData = data.data;
    renderResult(data.data, showOfficerCard, findNearbyAnganwadi);
  } else {
    renderQuickReplies(data.quick_replies, (val) => {
      sendChat(val);
    });
  }
}

async function showOfficerCard() {
  if (!lastEligibilityData) return;
  try {
    const res = await fetch("/api/v1/card", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        child_number: lastEligibilityData.reason_code === "ELIGIBLE_SECOND_CHILD_GIRL" ? 2 : 1,
        benefit_amount_inr: lastEligibilityData.benefit_amount_inr,
        categories: lastEligibilityData.categories || [],
        required_documents: lastEligibilityData.required_documents || [],
      }),
    });
    if (!res.ok) throw new Error("card unavailable");
    const card = await res.json();
    const modal = document.getElementById("officer-card-modal");
    document.getElementById("card-title-hi").textContent = card.title_hi;
    document.getElementById("card-title-en").textContent = card.title_en;
    document.getElementById("card-benefit-hi").textContent = card.benefit_hi;
    document.getElementById("card-benefit-en").textContent = card.benefit_en;
    document.getElementById("card-qr-img").src = card.qr_code_base64;
    document.getElementById("card-disclaimer").textContent = card.disclaimer_hi;

    const docList = document.getElementById("card-docs-list");
    docList.replaceChildren();
    card.documents_hi.forEach((doc, idx) => {
      const li = document.createElement("li");
      li.textContent = `${doc} (${card.documents_en[idx] || ""})`;
      docList.appendChild(li);
    });

    openModal(modal);
  } catch {
    updateCaption(translate("ui.contact_error"));
  }
}

async function findNearbyAnganwadi() {
  updateCaption(translate("ui.places_loading"));
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        fetchCentres(pos.coords.latitude, pos.coords.longitude);
      },
      () => {
        fetchCentres(28.61, 77.20);
      }
    );
  } else {
    fetchCentres(28.61, 77.20);
  }
}

async function fetchCentres(lat, lng) {
  try {
    const res = await fetch(`/api/v1/places/nearby?lat=${lat}&lng=${lng}`);
    if (!res.ok) throw new Error("places unavailable");
    const data = await res.json();
    const modal = document.getElementById("places-modal");
    const list = document.getElementById("places-list");
    list.replaceChildren();
    data.centres.forEach((centre) => {
      const item = document.createElement("div");
      item.className = "place-item";
      const name = document.createElement("strong");
      name.textContent = centre.name;
      const address = document.createElement("small");
      address.className = "place-address";
      address.textContent = centre.address;
      const directions = document.createElement("a");
      directions.href = centre.maps_url;
      directions.target = "_blank";
      directions.rel = "noopener noreferrer";
      directions.textContent = `${translate("ui.directions")} ↗`;
      item.append(name, address, directions);
      list.appendChild(item);
    });
    openModal(modal);
  } catch {
    updateCaption(translate("ui.places_error"));
  }
}

function initializeApp() {
  setupPrivacyHandlers(() => {
    // Reset to start on wipe
    currentStep = 0;
    lastEligibilityData = null;
    sessionId = crypto.randomUUID();
    sessionStorage.setItem("sakhi_session_id", sessionId);
    updateProgress(0);
    document.getElementById("screen-result").hidden = true;
    document.getElementById("quick-replies-container").replaceChildren();
    document.getElementById("btn-start-app").classList.remove("is-hidden");
    updateCaption(translate("app.greeting"));
  });

  const micBtn = document.getElementById("btn-mic");
  if (micBtn) {
    window.addEventListener("sakhi:recording-cancelled", () => {
      isRecording = false;
      micBtn.classList.remove("listening");
      micBtn.querySelector(".mic-label").textContent = translate("ui.mic_label");
    });
    micBtn.addEventListener("click", () => {
      if (!isRecording) {
        isRecording = true;
        micBtn.classList.add("listening");
          micBtn.querySelector(".mic-label").textContent = translate("app.listening");
        startRecording(
          (text) => {
            isRecording = false;
            micBtn.classList.remove("listening");
            micBtn.querySelector(".mic-label").textContent = translate("ui.mic_label");
            sendChat(text);
          },
          (err) => {
            isRecording = false;
            micBtn.classList.remove("listening");
            micBtn.querySelector(".mic-label").textContent = translate("ui.mic_label");
            updateCaption(err);
          }
        );
      } else {
        isRecording = false;
        micBtn.classList.remove("listening");
        micBtn.querySelector(".mic-label").textContent = translate("ui.mic_label");
        stopRecording();
      }
    });
  }

  // Greeting trigger on first tap
  const startBtn = document.getElementById("btn-start-app");
  if (startBtn) {
    startBtn.addEventListener("click", () => {
      startBtn.classList.add("is-hidden");
      sendChat(translate("chat.start_message"));
    });
  }

  document.getElementById("chat-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const input = document.getElementById("chat-message");
    const message = input.value.trim();
    if (!message) return;
    input.value = "";
    sendChat(message);
  });

  // Modal close handlers
  document.querySelectorAll(".btn-modal-close").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      closeModal(e.currentTarget.closest(".modal"));
    });
  });

  document.getElementById("btn-print-card").addEventListener("click", () => window.print());
  window.addEventListener("keydown", (event) => {
    const activeModal = document.querySelector(".modal:not([hidden])");
    if (!activeModal) return;
    if (event.key === "Escape") {
      closeModal(activeModal);
    } else if (event.key === "Tab") {
      const focusable = activeModal.querySelectorAll("a[href], button:not([disabled])");
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeApp, { once: true });
} else {
  initializeApp();
}
