/**
 * Audio Recording and Text-To-Speech Playback Module
 */

let mediaRecorder = null;
let audioChunks = [];
let currentAudio = null;
let currentObjectUrl = null;
let recordingRequest = 0;
let recordingPending = false;

function speakWithBrowser(text) {
  if ("speechSynthesis" in window) {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "hi-IN";
    utterance.rate = 0.9;
    window.speechSynthesis.speak(utterance);
  }
}

export async function playTTS(text) {
  if (!text) return;
  stopAudio();

  try {
    const res = await fetch("/api/v1/voice/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text, speaking_rate: 0.9 }),
    });

    if (res.ok) {
      const blob = await res.blob();
      currentObjectUrl = URL.createObjectURL(blob);
      currentAudio = new Audio(currentObjectUrl);
      currentAudio.play().catch(() => speakWithBrowser(text));
      return;
    }
  } catch {
    // Browser speech synthesis below is the offline audio fallback.
  }

  // Fallback to browser Web Speech API
  speakWithBrowser(text);
}

export function stopAudio() {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }
  if (currentObjectUrl) {
    URL.revokeObjectURL(currentObjectUrl);
    currentObjectUrl = null;
  }
  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
}

export async function startRecording(onTranscribeSuccess, onError) {
  const requestId = ++recordingRequest;
  recordingPending = true;
  audioChunks = [];
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    if (requestId !== recordingRequest) {
      stream.getTracks().forEach((track) => track.stop());
      return;
    }
    mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
    recordingPending = false;

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data);
      }
    };

    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
      const formData = new FormData();
      formData.append("file", audioBlob, "recording.webm");

      try {
        const res = await fetch("/api/v1/voice/transcribe", {
          method: "POST",
          body: formData,
        });
        if (res.ok) {
          const data = await res.json();
          onTranscribeSuccess(data.text);
        } else {
          onError(window.sakhiTranslate("ui.speech_unavailable"));
        }
      } catch (err) {
        onError(window.sakhiTranslate("ui.connection_unavailable"));
      }
    };

    mediaRecorder.start();
  } catch {
    if (requestId === recordingRequest) {
      recordingPending = false;
      onError(window.sakhiTranslate("ui.microphone_permission"));
    }
  }
}

export function cancelRecording() {
  const wasActive = Boolean(mediaRecorder) || recordingPending;
  recordingRequest++;
  recordingPending = false;
  if (!mediaRecorder) return wasActive;

  const recorder = mediaRecorder;
  mediaRecorder = null;
  audioChunks = [];
  recorder.ondataavailable = null;
  recorder.onstop = null;
  if (recorder.state !== "inactive") recorder.stop();
  recorder.stream.getTracks().forEach((track) => track.stop());
  return true;
}

export function stopRecording() {
  if (!mediaRecorder && recordingPending) {
    if (cancelRecording()) window.dispatchEvent(new Event("sakhi:recording-cancelled"));
    return;
  }
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach((track) => track.stop());
  }
}
