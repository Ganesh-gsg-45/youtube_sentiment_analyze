// static/js/auth.js
import { auth, db } from './firebase.js';
import {
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword,
    signOut,
    GoogleAuthProvider,
    GithubAuthProvider,
    signInWithPopup
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
    await setDoc(doc(db, "users", user.uid), {
        name: user.displayName || user.email?.split('@')[0] || 'User',
        email: user.email,
        photoURL: user.photoURL || null,
        provider: user.providerData?.[0]?.providerId || providerHint
    }, { merge: true });
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
 * Sign in with Google via popup
 */
export async function googleLogin() {
    const result = await signInWithPopup(auth, googleProvider);
    await saveUserProfile(result.user, 'google.com');
    console.log("Google sign-in:", result.user);
    return result;
}

/**
 * Sign in with GitHub via popup
 */
export async function githubLogin() {
    const result = await signInWithPopup(auth, githubProvider);
    await saveUserProfile(result.user, 'github.com');
    console.log("GitHub sign-in:", result.user);
    return result;
}

/**
 * No-op kept for backwards compatibility — popup flow no longer needs redirect handling
 */
export async function handleGoogleRedirectResult() {
    return null;
}

