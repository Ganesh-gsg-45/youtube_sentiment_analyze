// static/js/auth.js
import { auth, db } from './firebase.js';
import {
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword,
    signOut,
    GoogleAuthProvider,
    signInWithRedirect,
    getRedirectResult
} from "https://www.gstatic.com/firebasejs/10.7.0/firebase-auth.js";
import { doc, setDoc } from "https://www.gstatic.com/firebasejs/10.7.0/firebase-firestore.js";

const provider = new GoogleAuthProvider();
provider.setCustomParameters({ prompt: 'select_account' });

/**
 * Log in an existing user
 * @param {string} email
 * @param {string} password
 */
export async function loginUser(email, password) {
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    console.log("Logged in:", userCredential.user);
    return userCredential;
}

/**
 * Sign up a new user
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
 * Log in with Google using a redirect flow
 */
export async function googleLogin() {
    await signInWithRedirect(auth, provider);
}

/**
 * Handle the redirect result after Google authentication completes
 */
export async function handleGoogleRedirectResult() {
    const result = await getRedirectResult(auth);

    if (!result?.user) {
        return null;
    }

    await setDoc(doc(db, "users", result.user.uid), {
        name: result.user.displayName || result.user.email?.split('@')[0] || 'User',
        email: result.user.email,
        provider: result.user.providerData?.[0]?.providerId || 'google.com'
    }, { merge: true });

    return result;
}

