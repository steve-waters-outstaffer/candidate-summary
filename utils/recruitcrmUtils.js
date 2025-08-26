// utils/recruitcrmUtils.js

// Color constants matching the components
const CustomColors = {
    SecretGarden: '#5a9a5a',
    DarkRed: '#b71c1c',
    DeepSkyBlue: '#00bfff',
    UIGrey500: '#9e9e9e',
    UIGrey300: '#e0e0e0',
    UIGrey100: '#f5f5f5',
};

/**
 * URL Parsing Utilities
 */

/**
 * Parses a RecruitCRM candidate URL to extract job and candidate slugs
 * @param {string} url - The full RecruitCRM URL
 * @returns {object|null} - {jobSlug, candidateSlug} or null if parsing fails
 */
export const parseRecruitCrmUrl = (url) => {
    const regex = /candidate-sequence\/([^/]+)\/assigned_candidates\/\d+\/([^/]+)/;
    const match = url.match(regex);

    if (match && match[1] && match[2]) {
        return {
            jobSlug: match[1],
            candidateSlug: match[2]
        };
    }

    return null;
};

/**
 * Extracts the slug from any RecruitCRM URL (last path segment)
 * @param {string} url - The URL to extract slug from
 * @returns {string} - The extracted slug
 */
export const extractSlugFromUrl = (url) => {
    return url.split('/').pop();
};

/**
 * Status Management Utilities
 */

/**
 * Gets the color for a given status
 * @param {string} status - The status (success, error, loading, pending, warning)
 * @returns {string} - The corresponding color
 */
export const getStatusColor = (status) => {
    switch (status) {
        case 'success': return CustomColors.SecretGarden;
        case 'error': return CustomColors.DarkRed;
        case 'loading': return CustomColors.DeepSkyBlue;
        case 'warning': return '#ff9800';
        default: return CustomColors.UIGrey500;
    }
};

/**
 * Creates an initial status object for candidate validation
 * @returns {object} - Initial status structure
 */
export const createInitialCandidateStatus = () => ({
    candidate: { status: 'pending', message: '', data: null },
    resume: { status: 'pending', message: '', data: null },
    interview: { status: 'pending', message: '', data: null }
});

/**
 * Creates an initial status object for job validation
 * @returns {object} - Initial status structure
 */
export const createInitialJobStatus = () => ({
    status: 'pending',
    message: '',
    data: null
});

/**
 * API Validation Functions
 */

/**
 * Validates a candidate via the API
 * @param {string} slug - The candidate slug
 * @param {string} apiBaseUrl - The API base URL
 * @returns {Promise<object>} - API response data or error info
 */
export const validateCandidateApi = async (slug, apiBaseUrl) => {
    try {
        const response = await fetch(`${apiBaseUrl}/api/test-candidate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ candidate_slug: slug })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            return {
                success: true,
                status: 'success',
                message: data.candidate_name,
                data: data
            };
        } else {
            return {
                success: false,
                status: 'error',
                message: data.error || 'Failed to confirm candidate',
                data: null
            };
        }
    } catch (error) {
        return {
            success: false,
            status: 'error',
            message: 'Network error',
            data: null
        };
    }
};

/**
 * Validates a job via the API
 * @param {string} slug - The job slug
 * @param {string} apiBaseUrl - The API base URL
 * @returns {Promise<object>} - API response data or error info
 */
export const validateJobApi = async (slug, apiBaseUrl) => {
    try {
        const response = await fetch(`${apiBaseUrl}/api/test-job`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ job_slug: slug })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            return {
                success: true,
                status: 'success',
                message: data.job_name,
                data: data
            };
        } else {
            return {
                success: false,
                status: 'error',
                message: data.error || 'Failed to validate job',
                data: null
            };
        }
    } catch (error) {
        return {
            success: false,
            status: 'error',
            message: 'Network error validating job',
            data: null
        };
    }
};

/**
 * Validates a candidate's resume via the API
 * @param {string} candidateSlug - The candidate slug
 * @param {string} apiBaseUrl - The API base URL
 * @returns {Promise<object>} - API response data or error info
 */
export const validateResumeApi = async (candidateSlug, apiBaseUrl) => {
    try {
        const response = await fetch(`${apiBaseUrl}/api/test-resume`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ candidate_slug: candidateSlug })
        });

        const data = await response.json();

        if (response.ok) {
            return {
                success: data.success,
                status: data.success ? 'success' : 'error',
                message: data.success ? data.resume_name : data.message,
                data: data
            };
        } else {
            return {
                success: false,
                status: 'error',
                message: 'No resume on file',
                data: null
            };
        }
    } catch (error) {
        return {
            success: false,
            status: 'error',
            message: 'Network error',
            data: null
        };
    }
};

/**
 * Validates an interview via the API
 * @param {string} interviewId - The interview ID
 * @param {string} alpharunJobId - The AlphaRun job ID
 * @param {string} apiBaseUrl - The API base URL
 * @returns {Promise<object>} - API response data or error info
 */
export const validateInterviewApi = async (interviewId, alpharunJobId, apiBaseUrl) => {
    try {
        const response = await fetch(`${apiBaseUrl}/api/test-interview`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                interview_id: interviewId,
                alpharun_job_id: alpharunJobId
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            return {
                success: true,
                status: 'success',
                message: `Confirmed: ${data.candidate_name}`,
                data: data
            };
        } else {
            return {
                success: false,
                status: 'error',
                message: 'No interview found',
                data: null
            };
        }
    } catch (error) {
        return {
            success: false,
            status: 'error',
            message: 'Network error',
            data: null
        };
    }
};

/**
 * Validates Fireflies transcript via the API
 * @param {string} transcriptUrl - The Fireflies transcript URL
 * @param {string} apiBaseUrl - The API base URL
 * @returns {Promise<object>} - API response data or error info
 */
export const validateFirefliesApi = async (transcriptUrl, apiBaseUrl) => {
    try {
        const response = await fetch(`${apiBaseUrl}/api/test-fireflies`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ transcript_url: transcriptUrl })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            return {
                success: true,
                status: 'success',
                message: data.meeting_title,
                data: data
            };
        } else {
            return {
                success: false,
                status: 'error',
                message: data.error || 'Failed to fetch transcript data',
                data: null
            };
        }
    } catch (error) {
        return {
            success: false,
            status: 'error',
            message: 'Network error',
            data: null
        };
    }
};

/**
 * Helper Functions
 */

/**
 * Checks if all required validations are successful for generating summary
 * @param {object} candidateStatus - Candidate API status
 * @param {object} jobStatus - Job API status
 * @param {object} interviewStatus - Interview API status (optional)
 * @param {boolean} proceedWithoutInterview - Whether to proceed without interview
 * @param {object} firefliesStatus - Fireflies status (optional)
 * @param {boolean} includeFireflies - Whether Fireflies is required
 * @returns {boolean} - Whether ready to generate
 */
export const isReadyToGenerate = (
    candidateStatus,
    jobStatus,
    interviewStatus = null,
    proceedWithoutInterview = false,
    firefliesStatus = null,
    includeFireflies = false
) => {
    const baseApisSuccess = candidateStatus?.status === 'success' && jobStatus?.status === 'success';
    const interviewApiSuccess = interviewStatus?.status === 'success' || proceedWithoutInterview;
    const firefliesApiSuccess = !includeFireflies || firefliesStatus?.status === 'success';

    return baseApisSuccess && interviewApiSuccess && firefliesApiSuccess;
};

/**
 * Gets validated candidate names from multiple candidate statuses (for dropdown)
 * @param {object} candidateStatuses - Object containing all candidate statuses
 * @returns {Array} - Array of {index, name} objects for valid candidates
 */
export const getValidatedCandidateNames = (candidateStatuses) => {
    return Object.entries(candidateStatuses)
        .filter(([_, status]) => status?.candidate?.status === 'success')
        .map(([index, status]) => ({
            index: parseInt(index),
            name: status.candidate.data.candidate_name
        }));
};

/**
 * Counts the number of successfully validated candidates
 * @param {object} candidateStatuses - Object containing all candidate statuses
 * @returns {number} - Count of ready candidates
 */
export const getTotalCandidatesReady = (candidateStatuses) => {
    return Object.values(candidateStatuses).filter(status =>
        status?.candidate?.status === 'success'
    ).length;
};

/**
 * Alert Management
 */

/**
 * Creates a standardized alert object
 * @param {string} type - Alert type (success, error, info, warning)
 * @param {string} message - Alert message
 * @returns {object} - Alert object for state
 */
export const createAlert = (type, message) => ({
    show: true,
    type,
    message
});

/**
 * Creates an empty/hidden alert state
 * @returns {object} - Hidden alert object
 */
export const createEmptyAlert = () => ({
    show: false,
    type: 'info',
    message: ''
});

/**
 * Prompts Management
 */

/**
 * Fetches available prompts from the API
 * @param {string} apiBaseUrl - The API base URL
 * @param {string} category - The prompt category ('single' or 'multiple')
 * @returns {Promise<Array>} - Array of available prompts
 */
export const fetchAvailablePrompts = async (apiBaseUrl, category = 'single') => {
    try {
        const response = await fetch(`${apiBaseUrl}/api/prompts?category=${category}`);
        if (response.ok) {
            return await response.json();
        }
        return [];
    } catch (error) {
        console.error('Error fetching prompts:', error);
        return [];
    }
};