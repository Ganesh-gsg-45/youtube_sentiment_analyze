// static/js/firebase.js
// Firebase v10 ES Modules CDN

// Hugging Face's huggingface.co/spaces/... page loads this app inside an
// iframe. Browsers block window.open() popups (used for Google/GitHub
// sign-in) triggered from inside a cross-origin iframe, since HF's wrapper
// doesn't grant the iframe "allow=popups" permission. Detect that case and
// force the whole browser tab to navigate to this app's own direct URL
// (top-level, no iframe) BEFORE any auth code runs, so popup sign-in works
// regardless of which URL the user originally landed on.
if (window.top !== window.self) {
    window.top.location.href = window.self.location.href;
}

import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.0/firebase-app.js";
import { getAuth, setPersistence, browserLocalPersistence } from "https://www.gstatic.com/firebasejs/10.7.0/firebase-auth.js";
import { getFirestore } from "https://www.gstatic.com/firebasejs/10.7.0/firebase-firestore.js";

const firebaseConfig = {
  apiKey: "AIzaSyAzOY1qwVWob-UaBajCtqtOIOttcVR07O0",
  authDomain: "sentimentscope-ced63.firebaseapp.com",
  projectId: "sentimentscope-ced63",
  storageBucket: "sentimentscope-ced63.firebasestorage.app",
  messagingSenderId: "540827411433",
  appId: "1:540827411433:web:232014e2a094d72757e178",
  measurementId: "G-TQBZP6VZ5Z"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);

await setPersistence(auth, browserLocalPersistence).catch((error) => {
  console.warn("Firebase persistence warning:", error?.message || error);
});

export { auth, db, app };