import React, { useState, useEffect } from 'react';
import {
    Box,
    Card,
    CardContent,
    TextField,
    Button,
    Typography,
    Alert,
    CircularProgress,
    Paper,
    Grid,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    Tabs,
    Tab,
    Divider
} from '@mui/material';
import {
    CheckCircle,
    Cancel,
    HelpOutline,
} from '@mui/icons-material';

const CustomColors = {
    SecretGarden: '#5a9a5a',
    DarkRed: '#b71c1c',
    DeepSkyBlue: '#00bfff',
    UIGrey500: '#9e9e9e',
    UIGrey300: '#e0e0e0',
    UIGrey100: '#f5f5f5',
};
const FontWeight = { Medium: 500 };
const Spacing = { Large: 3, Medium: 2, Small: 1 };

const MultipleCandidatesGenerator = () => {
    const [candidateUrls, setCandidateUrls] = useState(['', '', '', '', '']);
    const [formData, setFormData] = useState({
        client_name: '',
        outstaffer_platform_url: '',
        preferred_candidate: '',
        additional_context: '',
        prompt_type: ''
    });

    // Status tracking
    const [candidateStatuses, setCandidateStatuses] = useState({});
    const [jobStatus, setJobStatus] = useState({ status: 'pending', message: '', data: null });
    const [availablePrompts, setAvailablePrompts] = useState([]);
    const [generatedContent, setGeneratedContent] = useState('');
    const [loading, setLoading] = useState(false);
    const [alert, setAlert] = useState({ show: false, type: 'info', message: '' });
    const [view, setView] = useState('preview');

    // API Base URL from environment
    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

    useEffect(() => {
        fetchAvailablePrompts();
    }, []);

    const fetchAvailablePrompts = async () => {
        if (!API_BASE_URL) return;
        try {
            const response = await fetch(`${API_BASE_URL}/api/prompts?category=multiple`);
            if (response.ok) {
                const prompts = await response.json();
                setAvailablePrompts(prompts);
                if (prompts.length > 0) {
                    setFormData(prev => ({ ...prev, prompt_type: prompts[0].id }));
                }
            }
        } catch (error) {
            console.error('Error fetching prompts:', error);
        }
    };

    const handleInputChange = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    const handleCandidateUrlChange = (index, value) => {
        const newUrls = [...candidateUrls];
        newUrls[index] = value;
        setCandidateUrls(newUrls);

        // Reset candidate status when URL changes
        if (candidateStatuses[index]) {
            setCandidateStatuses(prev => ({
                ...prev,
                [index]: {
                    candidate: { status: 'pending', message: '', data: null },
                    resume: { status: 'pending', message: '', data: null },
                    interview: { status: 'pending', message: '', data: null }
                }
            }));
        }

        // Extract and validate job from first candidate URL
        if (index === 0 && value.trim()) {
            extractAndValidateJobFromUrl(value);
        }
    };

    const extractAndValidateJobFromUrl = (candidateUrl) => {
        // Extract job slug from candidate URL pattern: /candidate-sequence/{job_slug}/assigned_candidates/{id}/{candidate_slug}
        const regex = /candidate-sequence\/([^/]+)\/assigned_candidates\/\d+\/([^/]+)/;
        const match = candidateUrl.match(regex);

        if (match && match[1]) {
            const jobSlug = match[1];
            validateJob(jobSlug);
        } else {
            setJobStatus({
                status: 'error',
                message: 'Could not extract job from URL',
                data: null
            });
        }
    };

    const validateJob = async (jobSlug) => {
        setJobStatus({ status: 'loading', message: 'Confirming job...', data: null });

        try {
            const response = await fetch(`${API_BASE_URL}/api/test-job`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ job_slug: jobSlug })
            });

            if (response.ok) {
                const data = await response.json();
                setJobStatus({
                    status: 'success',
                    message: data.job_name,
                    data: data
                });
            } else {
                const errorData = await response.json();
                setJobStatus({
                    status: 'error',
                    message: errorData.error || 'Failed to validate job',
                    data: null
                });
            }
        } catch (error) {
            setJobStatus({
                status: 'error',
                message: 'Network error validating job',
                data: null
            });
        }
    };

    const validateCandidate = async (index) => {
        const url = candidateUrls[index];
        if (!url.trim()) return;

        // Initialize candidate status if not exists
        if (!candidateStatuses[index]) {
            setCandidateStatuses(prev => ({
                ...prev,
                [index]: {
                    candidate: { status: 'pending', message: '', data: null },
                    resume: { status: 'pending', message: '', data: null },
                    interview: { status: 'pending', message: '', data: null }
                }
            }));
        }

        // Update candidate status to loading
        setCandidateStatuses(prev => ({
            ...prev,
            [index]: {
                ...prev[index],
                candidate: { status: 'loading', message: 'Confirming candidate...', data: null }
            }
        }));

        try {
            const slug = url.split('/').pop();
            const response = await fetch(`${API_BASE_URL}/api/test-candidate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ candidate_slug: slug })
            });

            if (response.ok) {
                const data = await response.json();
                setCandidateStatuses(prev => ({
                    ...prev,
                    [index]: {
                        ...prev[index],
                        candidate: {
                            status: 'success',
                            message: data.candidate_name,
                            data: data
                        }
                    }
                }));

                // Auto-validate resume
                validateResume(index, slug);

                // Auto-validate interview if we have job data
                if (data.interview_id && jobStatus.data?.alpharun_job_id) {
                    validateInterview(index, data.interview_id, jobStatus.data.alpharun_job_id);
                }

            } else {
                const errorData = await response.json();
                setCandidateStatuses(prev => ({
                    ...prev,
                    [index]: {
                        ...prev[index],
                        candidate: {
                            status: 'error',
                            message: errorData.error || 'Failed to confirm candidate',
                            data: null
                        }
                    }
                }));
            }
        } catch (error) {
            setCandidateStatuses(prev => ({
                ...prev,
                [index]: {
                    ...prev[index],
                    candidate: {
                        status: 'error',
                        message: 'Network error',
                        data: null
                    }
                }
            }));
        }
    };

    const validateResume = async (index, candidateSlug) => {
        setCandidateStatuses(prev => ({
            ...prev,
            [index]: {
                ...prev[index],
                resume: { status: 'loading', message: 'Checking resume...', data: null }
            }
        }));

        try {
            const response = await fetch(`${API_BASE_URL}/api/test-resume`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ candidate_slug: candidateSlug })
            });

            if (response.ok) {
                const data = await response.json();
                setCandidateStatuses(prev => ({
                    ...prev,
                    [index]: {
                        ...prev[index],
                        resume: {
                            status: data.success ? 'success' : 'error',
                            message: data.success ? data.resume_name : data.message,
                            data: data
                        }
                    }
                }));
            } else {
                setCandidateStatuses(prev => ({
                    ...prev,
                    [index]: {
                        ...prev[index],
                        resume: {
                            status: 'error',
                            message: 'No resume on file',
                            data: null
                        }
                    }
                }));
            }
        } catch (error) {
            setCandidateStatuses(prev => ({
                ...prev,
                [index]: {
                    ...prev[index],
                    resume: {
                        status: 'error',
                        message: 'Network error',
                        data: null
                    }
                }
            }));
        }
    };

    const validateInterview = async (index, interviewId, alpharunJobId) => {
        setCandidateStatuses(prev => ({
            ...prev,
            [index]: {
                ...prev[index],
                interview: { status: 'loading', message: 'Checking interview...', data: null }
            }
        }));

        try {
            const response = await fetch(`${API_BASE_URL}/api/test-interview`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    interview_id: interviewId,
                    alpharun_job_id: alpharunJobId
                })
            });

            if (response.ok) {
                const data = await response.json();
                setCandidateStatuses(prev => ({
                    ...prev,
                    [index]: {
                        ...prev[index],
                        interview: {
                            status: 'success',
                            message: `Confirmed: ${data.candidate_name}`,
                            data: data
                        }
                    }
                }));
            } else {
                setCandidateStatuses(prev => ({
                    ...prev,
                    [index]: {
                        ...prev[index],
                        interview: {
                            status: 'error',
                            message: 'No interview found',
                            data: null
                        }
                    }
                }));
            }
        } catch (error) {
            setCandidateStatuses(prev => ({
                ...prev,
                [index]: {
                    ...prev[index],
                    interview: {
                        status: 'error',
                        message: 'Network error',
                        data: null
                    }
                }
            }));
        }
    };

    const generateContent = async () => {
        const validUrls = candidateUrls.filter(url => url.trim());
        if (validUrls.length === 0) {
            showAlert('error', 'Please provide at least one candidate URL');
            return;
        }

        setLoading(true);
        setAlert({ show: false });

        try {
            const response = await fetch(`${API_BASE_URL}/api/generate-multiple-candidates`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    candidate_urls: validUrls,
                    client_name: formData.client_name,
                    job_url: formData.outstaffer_platform_url,
                    preferred_candidate: formData.preferred_candidate,
                    additional_context: formData.additional_context,
                    prompt_type: formData.prompt_type
                })
            });

            if (response.ok) {
                const data = await response.json();
                setGeneratedContent(data.generated_content);

                let message = `Generated content for ${data.candidates_processed} candidates`;
                if (data.resumes_processed) {
                    message += ` (${data.resumes_processed} resumes processed)`;
                }
                if (data.interviews_processed) {
                    message += ` (${data.interviews_processed} interviews included)`;
                }
                if (data.candidates_failed > 0) {
                    message += ` (${data.candidates_failed} failed)`;
                }
                showAlert('success', message);
            } else {
                const errorData = await response.json();
                showAlert('error', errorData.error || 'Failed to generate content');
            }
        } catch (error) {
            console.error('Error generating content:', error);
            showAlert('error', 'Network error occurred');
        } finally {
            setLoading(false);
        }
    };

    const showAlert = (type, message) => {
        setAlert({ show: true, type, message });
        setTimeout(() => setAlert({ show: false, type: 'info', message: '' }), 5000);
    };

    const handleViewChange = (event, newValue) => {
        setView(newValue);
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'success': return <CheckCircle sx={{ color: CustomColors.SecretGarden }} />;
            case 'error': return <Cancel sx={{ color: CustomColors.DarkRed }} />;
            case 'loading': return <CircularProgress size={24} />;
            default: return <HelpOutline sx={{ color: CustomColors.UIGrey500 }} />;
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'success': return CustomColors.SecretGarden;
            case 'error': return CustomColors.DarkRed;
            case 'loading': return CustomColors.DeepSkyBlue;
            default: return CustomColors.UIGrey500;
        }
    };

    const getValidatedCandidateNames = () => {
        return Object.entries(candidateStatuses)
            .filter(([_, status]) => status?.candidate?.status === 'success')
            .map(([index, status]) => ({
                index: parseInt(index),
                name: status.candidate.data.candidate_name
            }));
    };

    const renderCandidateStatus = (index) => {
        const status = candidateStatuses[index];
        const hasUrl = candidateUrls[index].trim();

        if (!hasUrl) return null;

        return (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mt: 2, p: 2, border: '1px solid #eee', borderRadius: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Typography variant="body1" sx={{ fontWeight: FontWeight.Medium }}>Candidate Profile:</Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {getStatusIcon(status?.candidate?.status)}
                        <Typography variant="body2" sx={{ color: getStatusColor(status?.candidate?.status) }}>
                            {status?.candidate?.message || 'Pending confirmation'}
                        </Typography>
                    </Box>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Typography variant="body1" sx={{ fontWeight: FontWeight.Medium }}>Anna AI Interview:</Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {getStatusIcon(status?.interview?.status)}
                        <Typography variant="body2" sx={{ color: getStatusColor(status?.interview?.status) }}>
                            {status?.interview?.message || 'Pending candidate'}
                        </Typography>
                    </Box>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Typography variant="body1" sx={{ fontWeight: FontWeight.Medium }}>Candidate Resume:</Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {getStatusIcon(status?.resume?.status)}
                        <Typography variant="body2" sx={{ color: getStatusColor(status?.resume?.status) }}>
                            {status?.resume?.message || 'Pending candidate'}
                        </Typography>
                    </Box>
                </Box>
            </Box>
        );
    };

    const renderCandidateUrlField = (index) => {
        const hasValue = candidateUrls[index].trim();

        return (
            <Box key={index} sx={{ mb: 3 }}>
                <TextField
                    label={`RecruitCRM URL ${index + 1}`}
                    value={candidateUrls[index]}
                    onChange={(e) => handleCandidateUrlChange(index, e.target.value)}
                    fullWidth
                    variant="outlined"
                    placeholder="Paste URL from RecruitCRM here..."
                    sx={{ mb: 1 }}
                />
                <Button
                    variant="outlined"
                    onClick={() => validateCandidate(index)}
                    disabled={!hasValue || candidateStatuses[index]?.candidate?.status === 'loading'}
                    fullWidth
                >
                    {candidateStatuses[index]?.candidate?.status === 'loading' ? <CircularProgress size={16} /> : 'Parse URL & Confirm Details'}
                </Button>
                {renderCandidateStatus(index)}
            </Box>
        );
    };

    const getTotalCandidatesReady = () => {
        return Object.values(candidateStatuses).filter(status =>
            status?.candidate?.status === 'success'
        ).length;
    };

    const isGenerateDisabled = loading ||
        getTotalCandidatesReady() === 0 ||
        !formData.prompt_type ||
        jobStatus.status !== 'success';

    return (
        <Box>
            {alert.show && <Alert severity={alert.type} sx={{ mb: Spacing.Medium }}>{alert.message}</Alert>}

            <Grid container spacing={Spacing.Large}>
                <Grid item xs={12} md={5}>
                    <Card>
                        <CardContent>
                            <Typography variant="h4" sx={{ mb: Spacing.Medium }}>Input Data</Typography>

                            {/* Job Status Display */}
                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: Spacing.Medium, p: 2, border: '1px solid #eee', borderRadius: 1 }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                    <Typography variant="body1" sx={{ fontWeight: FontWeight.Medium }}>Job Description:</Typography>
                                    <Typography variant="body2" sx={{ color: getStatusColor(jobStatus.status) }}>
                                        {jobStatus.message || 'Pending first candidate URL'}
                                    </Typography>
                                </Box>
                            </Box>

                            {/* Candidate URLs */}
                            <Typography variant="h6" sx={{ mb: 2 }}>Candidates</Typography>
                            {candidateUrls.map((_, index) => renderCandidateUrlField(index))}

                            <Divider sx={{ my: Spacing.Medium }} />

                            {/* Email Details */}
                            <Typography variant="h6" sx={{ mb: 2 }}>Email Details</Typography>

                            <TextField
                                label="Client Name"
                                value={formData.client_name}
                                onChange={(e) => handleInputChange('client_name', e.target.value)}
                                fullWidth
                                sx={{ mb: 2 }}
                            />

                            <FormControl fullWidth sx={{ mb: 2 }}>
                                <InputLabel>Preferred Candidate</InputLabel>
                                <Select
                                    value={formData.preferred_candidate}
                                    onChange={(e) => handleInputChange('preferred_candidate', e.target.value)}
                                    label="Preferred Candidate"
                                >
                                    <MenuItem value="">
                                        <em>None</em>
                                    </MenuItem>
                                    {getValidatedCandidateNames().map(({ index, name }) => (
                                        <MenuItem key={index} value={name}>
                                            {name}
                                        </MenuItem>
                                    ))}
                                </Select>
                            </FormControl>

                            <TextField
                                label="Additional Context (Optional)"
                                value={formData.additional_context}
                                onChange={(e) => handleInputChange('additional_context', e.target.value)}
                                fullWidth
                                multiline
                                rows={4}
                                sx={{ mb: 2 }}
                            />

                            <TextField
                                label="Outstaffer Platform URL (Optional)"
                                value={formData.outstaffer_platform_url}
                                onChange={(e) => handleInputChange('outstaffer_platform_url', e.target.value)}
                                fullWidth
                                sx={{ mb: 2 }}
                                placeholder="Link to embed in email..."
                            />

                            <FormControl fullWidth sx={{ mb: 2 }}>
                                <InputLabel>Template</InputLabel>
                                <Select
                                    value={formData.prompt_type}
                                    onChange={(e) => handleInputChange('prompt_type', e.target.value)}
                                    label="Template"
                                >
                                    {availablePrompts.map((prompt) => (
                                        <MenuItem key={prompt.id} value={prompt.id}>
                                            {prompt.name}
                                        </MenuItem>
                                    ))}
                                </Select>
                            </FormControl>

                            <Button
                                variant="contained"
                                color="primary"
                                onClick={generateContent}
                                disabled={isGenerateDisabled}
                                fullWidth
                                sx={{ mb: 1 }}
                            >
                                {loading ? <CircularProgress size={24} /> : 'Generate Email'}
                            </Button>

                            <Typography variant="body2" sx={{ color: CustomColors.UIGrey500, textAlign: 'center' }}>
                                Ready: {getTotalCandidatesReady()} candidates confirmed
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>

                <Grid item xs={12} md={7}>
                    {generatedContent && (
                        <Card>
                            <CardContent>
                                <Typography variant="h4" sx={{ mb: Spacing.Medium }}>Generated Email</Typography>

                                <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
                                    <Tabs value={view} onChange={handleViewChange}>
                                        <Tab label="Preview" value="preview" />
                                        <Tab label="HTML" value="html" />
                                    </Tabs>
                                </Box>

                                {view === 'preview' && (
                                    <Paper
                                        sx={{
                                            p: Spacing.Medium,
                                            backgroundColor: CustomColors.UIGrey100,
                                            border: `1px solid ${CustomColors.UIGrey300}`,
                                            borderRadius: 2,
                                            maxHeight: '600px',
                                            overflow: 'auto'
                                        }}
                                    >
                                        <Box dangerouslySetInnerHTML={{ __html: generatedContent }} />
                                    </Paper>
                                )}

                                {view === 'html' && (
                                    <TextField
                                        fullWidth
                                        multiline
                                        rows={20}
                                        label="HTML Source (Copy to Email Client)"
                                        value={generatedContent}
                                        InputProps={{
                                            readOnly: true,
                                            sx: { fontFamily: 'monospace', fontSize: '12px' }
                                        }}
                                        onClick={(e) => e.target.select()}
                                    />
                                )}
                            </CardContent>
                        </Card>
                    )}
                </Grid>
            </Grid>
        </Box>
    );
};

export default MultipleCandidatesGenerator;