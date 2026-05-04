// static/js/auth.js
import { auth } from './firebase.js';
import { 
    signInWithEmailAndPassword, 
    createUserWithEmailAndPassword, 
    signOut,
    GoogleAuthProvider,
    signInWithPopup
} from "https://www.gstatic.com/firebasejs/10.7.0/firebase-auth.js";
import { getFirestore, doc, setDoc } from "https://www.gstatic.com/firebasejs/10.7.0/firebase-firestore.js";

const provider = new GoogleAuthProvider();
const db = getFirestore();

/**
 * Log in an existing user
 * @param {string} email 
 * @param {string} password 
 */
export async function loginUser(email, password) {
    try {
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        console.log("Logged in:", userCredential.user);
        window.location.href = "/";
    } catch (error) {
        console.error("Login Error:", error.code, error.message);
        alert("Login failed: " + error.message);
    }
}

/**
 * Sign up a new user
 * @param {string} email 
 * @param {string} password 
 */
export async function signupUser(email, password) {
    try {
        const userCredential = await createUserWithEmailAndPassword(auth, email, password);
        console.log("Signed up:", userCredential.user);
        window.location.href = "/";
    } catch (error) {
        console.error("Signup Error:", error.code, error.message);
        alert("Signup failed: " + error.message);
    }
}

/**
 * Log out the current user
 */
export async function logoutUser() {
    try {
        await signOut(auth);
        console.log("Logged out");
        window.location.href = "/login";
    } catch (error) {
        console.error("Logout Error:", error);
    }
}

/**
 * Log in with Google
 */
export async function googleLogin() {
    try {
        const result = await signInWithPopup(auth, provider);
        console.log("Logged in with Google:", result.user);
        
        // Store user in Firestore
        await setDoc(doc(db, "users", result.user.uid), {
            name: result.user.displayName,
            email: result.user.email
        });
        
        window.location.href = "/";
    } catch (error) {
        console.error("Google Login Error:", error.code, error.message);
        alert("Google Login failed: " + error.message);
    }
}

