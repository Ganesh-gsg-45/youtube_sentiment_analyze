// static/js/auth.js
import { auth, db } from './firebase.js';
import {
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword,
    signOut,
    GoogleAuthProvider,
    signInWithPopup
} from "https://www.gstatic.com/firebasejs/10.7.0/firebase-auth.js";
import { doc, setDoc } from "https://www.gstatic.com/firebasejs/10.7.0/firebase-firestore.js";

const FB_COOKIE_NAME = "fb_id_token";

// Google provider
const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({ prompt: 'select_account' });

/**
 * Save user profile to Firestore after any OAuth sign-in
 * @param {import('firebase/auth').User} user
 * @param {string} providerHint
 */
async function saveUserProfile(user, providerHint) {
    try {
        await setDoc(doc(db, "users", user.uid), {
            name: user.displayName || user.email?.split('@')[0] || 'User',
            email: user.email,
            photoURL: user.photoURL || null,
            provider: user.providerData?.[0]?.providerId || providerHint
        }, { merge: true });
    } catch (e) {
        console.warn("Could not save user profile to Firestore:", e?.message || e);
    }
}

/**
 * Write the Firebase ID token into a cookie the Flask backend can read.
 * Called immediately after every successful sign-in, BEFORE redirecting,
 * so the very next server request (to "/") is already authenticated —
 * we don't rely on onIdTokenChanged firing first on the next page.
 * @param {import('firebase/auth').User} user
 */
export async function setSessionCookie(user) {
    const token = await user.getIdToken();
    // Not HttpOnly (JS needs to set/clear it) — SameSite=Lax is fine since
    // this is same-site navigation (login page -> app, both on the same origin).
    // Secure only works over HTTPS — browsers silently DROP the cookie if you
    // set Secure on plain http:// (e.g. local dev on 127.0.0.1:5000), which
    // causes an infinite login<->redirect loop. Only add it when actually on HTTPS.
    const isHttps = window.location.protocol === "https:";
    let cookie = `${FB_COOKIE_NAME}=${token}; path=/; max-age=3600; SameSite=Lax`;
    if (isHttps) cookie += "; Secure";
    document.cookie = cookie;
}

/**
 * Clear the session cookie (called on logout).
 */
export function clearSessionCookie() {
    const isHttps = window.location.protocol === "https:";
    let cookie = `${FB_COOKIE_NAME}=; path=/; max-age=0; SameSite=Lax`;
    if (isHttps) cookie += "; Secure";
    document.cookie = cookie;
}

/**
 * Log in an existing user with email/password
 * @param {string} email
 * @param {string} password
 */
export async function loginUser(email, password) {
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    await setSessionCookie(userCredential.user);
    console.log("Logged in:", userCredential.user.email);
    return userCredential;
}

/**
 * Sign up a new user with email/password
 * @param {string} email
 * @param {string} password
 */
export async function signupUser(email, password) {
    const userCredential = await createUserWithEmailAndPassword(auth, email, password);
    await setSessionCookie(userCredential.user);
    console.log("Signed up:", userCredential.user.email);
    return userCredential;
}

/**
 * Log out the current user
 */
export async function logoutUser() {
    clearSessionCookie();
    await signOut(auth);
    console.log("Logged out");
    window.location.href = "/login";
}

/**
 * Sign in with Google via popup.
 * Popup is used instead of redirect because the redirect flow requires
 * cross-domain storage between this app's domain (hf.space) and Firebase's
 * authDomain (firebaseapp.com) — browsers increasingly block that as
 * third-party storage, which silently breaks the redirect round-trip.
 * Popup communicates the result back via postMessage instead, which isn't
 * affected by that restriction.
 * @returns {Promise<import('firebase/auth').UserCredential>}
 */
export async function googleLogin() {
    const result = await signInWithPopup(auth, googleProvider);
    await saveUserProfile(result.user, 'google.com');
    await setSessionCookie(result.user);
    console.log("Google sign-in successful:", result.user.email);
    return result;
}