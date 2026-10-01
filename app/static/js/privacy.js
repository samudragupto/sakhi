/**
 * Privacy Mode, Panic Screen Swap, and Instant Data Erasure Module
 */

import { cancelRecording, stopAudio } from "./audio.js";

let isHidden = false;

export function setupPrivacyHandlers(onSessionWiped) {
  const btnHide = document.getElementById("btn-hide");
  const btnWipe = document.getElementById("btn-wipe");
  const screenRecipe = document.getElementById("screen-recipe");
  const mainAppContainer = document.getElementById("app-viewport");

  function triggerPanicHide() {
    stopAudio();
    if (cancelRecording()) window.dispatchEvent(new Event("sakhi:recording-cancelled"));
    isHidden = !isHidden;
    if (isHidden) {
      mainAppContainer.hidden = true;
      screenRecipe.hidden = false;
      btnHide.querySelector("span:last-child").textContent = window.sakhiLocale.app.back;
      btnHide.setAttribute("aria-label", window.sakhiTranslate("ui.return_aria"));
    } else {
      screenRecipe.hidden = true;
      mainAppContainer.hidden = false;
      btnHide.querySelector("span:last-child").textContent = window.sakhiLocale.app.hide;
      btnHide.setAttribute("aria-label", window.sakhiTranslate("ui.hide_aria"));
    }
  }

  if (btnHide) {
    btnHide.addEventListener("click", triggerPanicHide);
  }

  // Escape key triggers panic hide
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (document.querySelector(".modal:not([hidden])")) return;
      triggerPanicHide();
    }
  });

  // Triple-tap gesture on mobile triggers panic hide
  let tapCount = 0;
  let tapTimer = null;
  window.addEventListener("touchend", () => {
    tapCount++;
    if (tapCount === 3) {
      triggerPanicHide();
      tapCount = 0;
      clearTimeout(tapTimer);
    } else {
      clearTimeout(tapTimer);
      tapTimer = setTimeout(() => {
        tapCount = 0;
      }, 500);
    }
  });

  // Data Wipe
  if (btnWipe) {
    btnWipe.addEventListener("click", async () => {
      const sessionId = sessionStorage.getItem("sakhi_session_id");
      if (sessionId) {
        try {
          await fetch(`/api/v1/session?session_id=${encodeURIComponent(sessionId)}`, {
            method: "DELETE",
          });
        } catch {}
      }
      sessionStorage.clear();
      stopAudio();
      if (cancelRecording()) window.dispatchEvent(new Event("sakhi:recording-cancelled"));
      if (onSessionWiped) {
        onSessionWiped();
      }
    });
  }
}
