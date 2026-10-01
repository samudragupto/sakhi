/**
 * UI Rendering and DOM Manipulation Module
 */

import { playTTS } from "./audio.js";

const t = (key) => window.sakhiTranslate(key);

export function updateCaption(text) {
  const box = document.getElementById("live-caption");
  if (box) {
    box.textContent = text;
  }
}

export function updateProgress(stepIndex) {
  const dots = document.querySelectorAll(".progress-dots .dot");
  dots.forEach((dot, idx) => {
    dot.classList.remove("active", "completed");
    if (idx < stepIndex) {
      dot.classList.add("completed");
    } else if (idx === stepIndex) {
      dot.classList.add("active");
    }
  });
  const progress = document.querySelector(".progress-dots");
  progress.setAttribute("aria-valuenow", String(Math.max(1, Math.min(stepIndex + 1, dots.length))));
}

export function renderQuickReplies(replies, onSelect) {
  const container = document.getElementById("quick-replies-container");
  container.replaceChildren();
  if (!replies || replies.length === 0) return;

  const isYesNo = replies.length === 2 && replies.some((reply) => reply.value === window.sakhiLocale.app.yes);
  container.className = isYesNo ? "decision-grid" : "cards-grid";

  replies.forEach((r) => {
    const option = document.createElement("div");
    option.className = "reply-option";
    const btn = document.createElement("button");
    btn.className = isYesNo
      ? (r.value === window.sakhiLocale.app.yes ? "btn-decision btn-yes" : "btn-decision btn-no")
      : "choice-card";
    btn.setAttribute("type", "button");
    btn.setAttribute("aria-label", r.label_hi);

    const labelSpan = document.createElement("span");
    labelSpan.textContent = r.label_hi;

    const speakerBtn = document.createElement("button");
    speakerBtn.type = "button";
    speakerBtn.textContent = "🔊";
    speakerBtn.className = "reply-speak";
    speakerBtn.setAttribute("aria-label", `${t("ui.speak_reply")}: ${r.label_hi}`);
    speakerBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      playTTS(r.label_hi);
    });

    btn.appendChild(labelSpan);
    btn.addEventListener("click", () => {
      onSelect(r.value);
    });

    option.append(btn, speakerBtn);
    container.appendChild(option);
  });
}

export function renderResult(data, onShowOfficerCard, onFindAnganwadi) {
  const container = document.getElementById("screen-result");
  const quickContainer = document.getElementById("quick-replies-container");
  quickContainer.replaceChildren();

  const isEligible = data.eligible;
  const box = document.createElement("div");
  box.className = isEligible ? "result-box" : "result-box ineligible";

  const title = document.createElement("h2");
  title.textContent = isEligible ? `✅ ${t("ui.eligible_title")}` : `ℹ️ ${t("ui.ineligible_title")}`;

  const amount = document.createElement("div");
  amount.className = "benefit-amount";
  amount.textContent = isEligible ? `₹${data.benefit_amount_inr.toLocaleString("en-IN")}` : "₹0";

  const reason = document.createElement("p");
  reason.textContent = data.reason_hi;
  reason.className = "result-reason";

  box.appendChild(title);
  box.appendChild(amount);
  box.appendChild(reason);

  if (isEligible && data.required_documents) {
    const docTitle = document.createElement("h3");
    docTitle.textContent = `📋 ${t("ui.document_list_title")}`;
    docTitle.className = "result-document-title";

    const docList = document.createElement("ul");
    docList.className = "doc-list";

    const docMap = window.sakhiLocale.ui.document_names;

    data.required_documents.forEach((docId) => {
      const li = document.createElement("li");
      li.className = "doc-item";

      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.id = `doc-${docId}`;
      cb.setAttribute("aria-label", docMap[docId] || docId);

      const label = document.createElement("label");
      label.htmlFor = `doc-${docId}`;
      label.textContent = docMap[docId] || docId;

      li.appendChild(cb);
      li.appendChild(label);
      docList.appendChild(li);
    });

    box.appendChild(docTitle);
    box.appendChild(docList);
  }

  // Action Buttons
  const actionsDiv = document.createElement("div");
  actionsDiv.className = "result-actions";

  const btnCard = document.createElement("button");
  btnCard.className = "choice-card";
  btnCard.textContent = `📜 ${window.sakhiLocale.app.show_officer}`;
  btnCard.addEventListener("click", onShowOfficerCard);

  const btnMap = document.createElement("button");
  btnMap.className = "choice-card";
  btnMap.textContent = `📍 ${window.sakhiLocale.app.find_anganwadi}`;
  btnMap.addEventListener("click", onFindAnganwadi);

  actionsDiv.appendChild(btnCard);
  actionsDiv.appendChild(btnMap);
  box.appendChild(actionsDiv);

  container.replaceChildren();
  container.appendChild(box);
  container.hidden = false;
}
