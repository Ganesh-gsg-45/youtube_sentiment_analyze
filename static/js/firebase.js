// static/js/firebase.js
// Firebase v10 ES Modules CDN

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

