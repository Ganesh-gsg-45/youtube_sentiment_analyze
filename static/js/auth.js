// static/js/auth.js
import { auth, db } from './firebase.js';
import {
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword,
    signOut,
    GoogleAuthProvider,
    GithubAuthProvider,
    signInWithRedirect,
    getRedirectResult
} from "https://www.gstatic.com/firebasejs/10.7.0/firebase-auth.js";
import { doc, setDoc } from "https://www.gstatic.com/firebasejs/10.7.0/firebase-firestore.js";

// Google provider
const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({ prompt: 'select_account' });

// GitHub provider
const githubProvider = new GithubAuthProvider();
githubProvider.addScope('read:user');
githubProvider.addScope('user:email');

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
 * Log in an existing user with email/password
 * @param {string} email
 * @param {string} password
 */
export async function loginUser(email, password) {
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    console.log("Logged in:", userCredential.user);
    return userCredential;
}

/**
 * Sign up a new user with email/password
 * @param {string} email
 * @param {string} password
 */
export async function signupUser(email, password) {
    const userCredential = await createUserWithEmailAndPassword(auth, email, password);
    console.log("Signed up:", userCredential.user);
    return userCredential;
}

/**
 * Log out the current user
 */
export async function logoutUser() {
    await signOut(auth);
    console.log("Logged out");
    window.location.href = "/login";
}

/**
 * Sign in with Google via redirect (avoids popup-blocked errors).
 * The browser navigates to Google, then returns to the same page.
 * Call handleRedirectResult() on page load to capture the sign-in result.
 */
export async function googleLogin() {
    await signInWithRedirect(auth, googleProvider);
    // Page navigates away — nothing executes after this
}

/**
 * Sign in with GitHub via redirect (avoids popup-blocked errors).
 */
export async function githubLogin() {
    await signInWithRedirect(auth, githubProvider);
    // Page navigates away — nothing executes after this
}

/**
 * Call this on every page load BEFORE setting up onAuthStateChanged.
 * Captures the OAuth credential after the browser returns from the redirect.
 * @returns {Promise<import('firebase/auth').UserCredential | null>}
 */
export async function handleRedirectResult() {
    try {
        const result = await getRedirectResult(auth);
        if (result && result.user) {
            const provider = result.providerId || result.user.providerData?.[0]?.providerId || 'oauth';
            await saveUserProfile(result.user, provider);
            console.log("OAuth redirect sign-in successful:", result.user.email);
            return result;
        }
        return null;
    } catch (err) {
        console.error("OAuth redirect result error:", err?.code, err?.message);
        throw err;
    }
}
