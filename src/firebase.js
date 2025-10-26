// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics, isSupported } from "firebase/analytics";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
    apiKey: "AIzaSyDmlUccTk6LkBOWkc52G8_Cit1E90orCm8",
    authDomain: "candidate-summary-ai.firebaseapp.com",
    projectId: "candidate-summary-ai",
    storageBucket: "candidate-summary-ai.firebasestorage.app",
    messagingSenderId: "14026519729",
    appId: "1:14026519729:web:c29812bac9678a695ade90",
    measurementId: "G-PV7CQCD0BX"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Analytics only if supported
let analytics = null;
isSupported().then(yes => {
    if (yes) {
        analytics = getAnalytics(app);
    }
}).catch(() => {
    // Analytics not supported, silently continue
});

// Export app for use in other files
export { app, analytics };