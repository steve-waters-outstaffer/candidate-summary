// src/services/apiService.js

import { getAuth } from 'firebase/auth';

/**
 * A wrapper around fetch that automatically adds the Firebase ID token
 * to the Authorization header as a Bearer token.
 *
 * @param {string} url - The URL to fetch
 * @param {Object} options - Fetch options (method, body, headers, etc.)
 * @returns {Promise<Response>} - The fetch response
 */
export const authFetch = async (url, options = {}) => {
  const auth = getAuth();
  const user = auth.currentUser;

  if (!user) {
    throw new Error('User is not authenticated');
  }

  // Get the fresh ID token
  const idToken = await user.getIdToken();

  // Ensure headers object exists
  const headers = options.headers || {};

  // Create a new options object with the Authorization header
  const authOptions = {
    ...options,
    headers: {
      ...headers,
      'Authorization': `Bearer ${idToken}`,
      'Content-Type': headers['Content-Type'] || 'application/json',
    },
  };

  // If the URL is relative, prepend the API base URL if available
  const baseUrl = import.meta.env.VITE_API_BASE_URL || '';
  const finalUrl = url.startsWith('http') ? url : `${baseUrl}${url}`;

  return fetch(finalUrl, authOptions);
};
