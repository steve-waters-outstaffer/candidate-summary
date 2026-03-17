// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";
// import { getAnalytics, isSupported } from "firebase/analytics";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Environment-aware configuration
// These are injected at build time via Vite
const firebaseConfig = {
    apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
    authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
    projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
    storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
    messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
    appId: import.meta.env.VITE_FIREBASE_APP_ID,
    measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID
};

// Backend API URL (injected at build time)
export const BACKEND_URL = import.meta.env.VITE_BACKEND_URL;
export const ENVIRONMENT = import.meta.env.VITE_ENVIRONMENT || 'production';
export const SEGMENT_WRITE_KEY = import.meta.env.VITE_SEGMENT_WRITE_KEY;

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firestore
const db = getFirestore(app);

// Analytics disabled for now (was causing slow page loads)
const analytics = null;

// Export app and db for use in other files
export { app, db, analytics };
