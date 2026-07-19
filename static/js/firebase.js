// static/js/firebase.js
// Firebase v10 ES Modules CDN

// Hugging Face's huggingface.co/spaces/... page loads this app inside an
// iframe. Sandboxed cross-origin iframes commonly block BOTH window.open()
// popups AND forced top-window navigation, so we can't reliably force our
// way out with a script — attempting window.top.location can throw a
// SecurityError and silently break the whole module if unguarded. Instead:
// detect the iframe safely, and show a real anchor-tag banner (real link
// clicks are allowed even in sandboxed iframes without any special
// permission) so the user has one guaranteed-working path to the direct URL.
try {
    if (window.top !== window.self) {
        const banner = document.createElement('div');
        banner.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:99999;background:linear-gradient(90deg,#6366f1,#8b5cf6);color:#fff;padding:12px 20px;text-align:center;font-family:sans-serif;font-size:14px;font-weight:600;box-shadow:0 2px 8px rgba(0,0,0,0.3);';
        const directUrl = window.self.location.href;
        banner.innerHTML = `Sign-in works best outside this preview. <a href="${directUrl}" target="_top" style="color:#fff;text-decoration:underline;">Open the app directly →</a>`;
        document.addEventListener('DOMContentLoaded', () => document.body.prepend(banner));
    }
} catch (e) {
    // Cross-origin access blocked entirely — ignore, rest of the app still loads normally.
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