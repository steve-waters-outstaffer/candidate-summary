// src/services/authService.js
import {
    getAuth,
    signOut,
    sendPasswordResetEmail,
    updateProfile,
    updateEmail,
    updatePassword
} from 'firebase/auth';
import { app } from '../firebase';

const auth = getAuth(app);

// Log out the current user
export const logoutUser = async () => {
    return signOut(auth);
};

// Send password reset email
export const resetPassword = async (email) => {
    return sendPasswordResetEmail(auth, email);
};

// Update user profile
export const updateUserProfile = async (displayName, photoURL) => {
    if (!auth.currentUser) throw new Error('No user is signed in');

    return updateProfile(auth.currentUser, {
        displayName: displayName || auth.currentUser.displayName,
        photoURL: photoURL || auth.currentUser.photoURL
    });
};

// Update user email
export const updateUserEmail = async (email) => {
    if (!auth.currentUser) throw new Error('No user is signed in');

    return updateEmail(auth.currentUser, email);
};

// Update user password
export const updateUserPassword = async (newPassword) => {
    if (!auth.currentUser) throw new Error('No user is signed in');

    return updatePassword(auth.currentUser, newPassword);
};