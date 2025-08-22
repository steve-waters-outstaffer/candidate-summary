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
    Divider,
    Paper,
    Grid,
    Tabs,
    Tab,
    Switch,
    FormControlLabel,
    Collapse
} from '@mui/material';
import {
    CheckCircle,
    Cancel,
    HelpOutline,
    Refresh,
    ThumbUp,
    ThumbDown
} from '@mui/icons-material';

// --- FIX: Replaced missing theme import with placeholder values ---
// In a real project, these would come from your theme file (e.g., '../theme')
const CustomColors = {
    SecretGarden: '#5a9a5a',
    DarkRed: '#b71c1c',
    DeepSkyBlue: '#00bfff',
    UIGrey500: '#9e9e9e',
    UIGrey300: '#e0e0e0',
    UIGrey100: '#f5f5f5',
    MidnightBlue: '#191970',
};
const FontWeight = {
    Medium: 500,
};
const Spacing = {
    Large: 3,
    Medium: 2,
    Small: 1,
    Default: 1,
};
// --- END FIX ---

const CandidateSummaryGenerator = () => {
    const [formData, setFormData] = useState({
        candidate_slug: '',
        job_slug: '',
        alpharun_job_id: '',
        interview_id: '',
        additional_context: '',
        fireflies_url: '' // New state for Fireflies URL
    });

    const [recruitCrmUrl, setRecruitCrmUrl] = useState('');
    const [firefliesUrl, setFirefliesUrl] = useState(''); // Separate state for the input field

    const [apiStatus, setApiStatus] = useState({
        candidate: { status: 'pending', message: '', data: null },
        job: { status: 'pending', message: '', data: null },
        interview: { status: 'pending', message: '', data: null },
        fireflies: { status: 'pending', message: '', data: null } // New status for Fireflies
    });

    const [generatedHtml, setGeneratedHtml] = useState('');
    const [loading, setLoading] = useState(false);
    const [pushing, setPushing] = useState(false);
    const [alert, setAlert] = useState({ show: false, type: 'info', message: '' });
    const [view, setView] = useState('preview');
    const [isAnonymous, setIsAnonymous] = useState(false);
    const [includeFireflies, setIncludeFireflies] = useState(false); // State for the switch

    // --- NEW: State for feedback loop ---
    const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
    const [showFeedbackComment, setShowFeedbackComment] = useState(false);
    const [feedbackComment, setFeedbackComment] = useState('');


    // --- FIX: Replaced placeholder URL with a valid local development URL ---
    // This should point to your running Flask backend.
    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

    useEffect(() => {
        const candidateData = apiStatus.candidate.data;
        const jobData = apiStatus.job.data;

        if (candidateData?.success && candidateData.interview_id) {
            setFormData(prev => ({ ...prev, interview_id: candidateData.interview_id }));
        }

        if (jobData?.success && jobData.alpharun_job_id) {
            setFormData(prev => ({ ...prev, alpharun_job_id: jobData.alpharun_job_id }));
        }
    }, [apiStatus.candidate.data, apiStatus.job.data]);

    useEffect(() => {
        const { interview_id, alpharun_job_id } = formData;

        if (interview_id && alpharun_job_id && apiStatus.interview.status === 'pending') {
            testApi('interview', { interview_id, alpharun_job_id });
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [formData.interview_id, formData.alpharun_job_id]);

    useEffect(() => {
        if (!API_BASE_URL) {
            showAlert('error', 'Configuration Error: The API URL is not set. Please check the application configuration.');
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);


    const testApi = async (apiType, payload) => {
        if (!API_BASE_URL) return;

        setApiStatus(prev => ({
            ...prev,
            [apiType]: { status: 'loading', message: 'Confirming...', data: null }
        }));

        try {
            const response = await fetch(`${API_BASE_URL}/api/test-${apiType}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (data.success) {
                setApiStatus(prev => ({
                    ...prev,
                    [apiType]: { status: 'success', message: data.message, data: data }
                }));
            } else {
                setApiStatus(prev => ({
                    ...prev,
                    [apiType]: { status: 'error', message: data.error, data: null }
                }));
            }
        } catch (error) {
            setApiStatus(prev => ({
                ...prev,
                [apiType]: { status: 'error', message: `Network error: ${error.message}`, data: null }
            }));
        }
    };

    const handleParseAndConfirm = () => {
        if (!recruitCrmUrl) {
            showAlert('error', 'Please paste the RecruitCRM URL first.');
            return;
        }

        const regex = /candidate-sequence\/([^\/]+)\/assigned_candidates\/\d+\/([^\/]+)/;
        const match = recruitCrmUrl.match(regex);

        if (match && match[1] && match[2]) {
            const jobSlug = match[1];
            const candidateSlug = match[2];

            showAlert('info', 'URL parsed. Confirming Job and Candidate...');

            setFormData(prev => ({
                ...prev,
                job_slug: jobSlug,
                candidate_slug: candidateSlug
            }));

            testApi('job', { job_slug: jobSlug });
            testApi('candidate', { candidate_slug: candidateSlug });
        } else {
            showAlert('error', 'Could not parse the URL. Please check the format and try again.');
        }
    };

    const handleFirefliesConfirm = () => {
        if (!firefliesUrl) {
            showAlert('error', 'Please paste the Fireflies URL first.');
            return;
        }
        setFormData(prev => ({ ...prev, fireflies_url: firefliesUrl }));
        testApi('fireflies', { transcript_url: firefliesUrl });
    };

    const resetApiStatus = () => {
        setApiStatus({
            candidate: { status: 'pending', message: '', data: null },
            job: { status: 'pending', message: '', data: null },
            interview: { status: 'pending', message: '', data: null },
            fireflies: { status: 'pending', message: '', data: null }
        });
        setRecruitCrmUrl('');
        setFirefliesUrl('');
        setFormData({
            candidate_slug: '',
            job_slug: '',
            alpharun_job_id: '',
            interview_id: '',
            additional_context: '',
            fireflies_url: ''
        });
        setGeneratedHtml('');
        setFeedbackSubmitted(false);
        setShowFeedbackComment(false);
        setFeedbackComment('');
        setIncludeFireflies(false);
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

    const showAlert = (type, message) => {
        setAlert({ show: true, type, message });
        setTimeout(() => setAlert({ show: false, type: 'info', message: '' }), 5000);
    };

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const generateSummary = async () => {
        if (!API_BASE_URL) return;

        const baseApisSuccess = apiStatus.candidate.status === 'success' &&
            apiStatus.job.status === 'success' &&
            apiStatus.interview.status === 'success';

        const firefliesApiSuccess = !includeFireflies || apiStatus.fireflies.status === 'success';

        if (!baseApisSuccess || !firefliesApiSuccess) {
            showAlert('error', 'Please ensure all required details are confirmed successfully before generating.');
            return;
        }

        setLoading(true);
        setFeedbackSubmitted(false);
        setShowFeedbackComment(false);
        setFeedbackComment('');

        try {
            const prompt_type = isAnonymous ? 'anonymous.detailed' : 'recruitment.detailed';

            const payload = { ...formData, prompt_type: prompt_type };
            if (!includeFireflies) {
                delete payload.fireflies_url;
            }

            const response = await fetch(`${API_BASE_URL}/api/generate-summary`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (data.success) {
                setGeneratedHtml(data.html_summary);
                showAlert('success', 'Summary generated successfully!');
            } else {
                showAlert('error', data.error || 'Failed to generate summary');
            }
        } catch (error) {
            showAlert('error', 'Network error: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    const pushToRecruitCRM = async () => {
        if (!API_BASE_URL) return;

        if (!generatedHtml || !formData.candidate_slug) {
            showAlert('error', 'No summary to push or missing candidate information');
            return;
        }

        setPushing(true);
        try {
            const response = await fetch(`${API_BASE_URL}/api/push-to-recruitcrm`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    candidate_slug: formData.candidate_slug,
                    html_summary: generatedHtml
                })
            });

            const data = await response.json();

            if (data.success) {
                showAlert('success', 'Summary pushed to RecruitCRM successfully!');
            } else {
                showAlert('error', data.error || 'Failed to push to RecruitCRM');
            }
        } catch (error) {
            showAlert('error', 'Network error: ' + error.message);
        } finally {
            setPushing(false);
        }
    };

    const handleFeedbackSubmit = async (rating) => {
        if (!API_BASE_URL) return;

        const payload = {
            rating: rating,
            comments: feedbackComment,
            prompt_type: isAnonymous ? 'anonymous.detailed' : 'recruitment.detailed',
            generated_summary_html: generatedHtml,
            candidate_slug: formData.candidate_slug,
            job_slug: formData.job_slug
        };

        try {
            const response = await fetch(`${API_BASE_URL}/api/log-feedback`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                showAlert('success', 'Thank you for your feedback!');
                setFeedbackSubmitted(true);
            } else {
                const data = await response.json();
                showAlert('error', data.error || 'Failed to submit feedback.');
            }
        } catch (error) {
            showAlert('error', `Network error: ${error.message}`);
        }
    };

    const handleViewChange = (event, newValue) => {
        setView(newValue);
    };

    const isGenerateDisabled = loading ||
        !(apiStatus.candidate.status === 'success' &&
            apiStatus.job.status === 'success' &&
            apiStatus.interview.status === 'success' &&
            (!includeFireflies || apiStatus.fireflies.status === 'success'));

    return (
        <Box sx={{mx: 'auto', p: Spacing.Large }}>
            <Typography variant="h2" sx={{ mb: Spacing.Large, color: CustomColors.MidnightBlue }}>
                Candidate Summary Generator
            </Typography>

            {alert.show && (
                <Alert severity={alert.type} sx={{ mb: Spacing.Medium }}>
                    {alert.message}
                </Alert>
            )}

            <Grid container spacing={Spacing.Large}>
                <Grid item xs={12} md={5}>
                    <Card>
                        <CardContent>
                            <Typography variant="h4" sx={{ mb: Spacing.Medium }}>
                                Input Data
                            </Typography>

                            <Box sx={{ position: 'relative', mb: Spacing.Medium }}>
                                <TextField
                                    fullWidth
                                    label="RecruitCRM URL"
                                    name="recruitCrmUrl"
                                    value={recruitCrmUrl}
                                    onChange={(e) => {
                                        setRecruitCrmUrl(e.target.value);
                                        if (apiStatus.candidate.status !== 'pending' || apiStatus.job.status !== 'pending' || apiStatus.interview.status !== 'pending') {
                                            resetApiStatus();
                                        }
                                    }}
                                    sx={{ mb: Spacing.Small }}
                                    placeholder="Paste URL from RecruitCRM here..."
                                    required
                                />
                                <Button
                                    fullWidth
                                    variant="outlined"
                                    onClick={handleParseAndConfirm}
                                    disabled={!recruitCrmUrl}
                                >
                                    Parse URL & Confirm Details
                                </Button>
                            </Box>

                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: Spacing.Medium, p: 2, border: '1px solid #eee', borderRadius: 1 }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                    <Typography variant="body1" sx={{fontWeight: FontWeight.Medium}}>Job:</Typography>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                        {getStatusIcon(apiStatus.job.status)}
                                        <Typography variant="body2" sx={{ color: getStatusColor(apiStatus.job.status) }}>
                                            {apiStatus.job.data?.job_name || apiStatus.job.message || 'Pending URL Parse'}
                                        </Typography>
                                    </Box>
                                </Box>
                                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                    <Typography variant="body1" sx={{fontWeight: FontWeight.Medium}}>Candidate:</Typography>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                        {getStatusIcon(apiStatus.candidate.status)}
                                        <Typography variant="body2" sx={{ color: getStatusColor(apiStatus.candidate.status) }}>
                                            {apiStatus.candidate.data?.candidate_name || apiStatus.candidate.message || 'Pending URL Parse'}
                                        </Typography>
                                    </Box>
                                </Box>
                                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                    <Typography variant="body1" sx={{fontWeight: FontWeight.Medium}}>Interview:</Typography>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                        {getStatusIcon(apiStatus.interview.status)}
                                        <Typography variant="body2" sx={{ color: getStatusColor(apiStatus.interview.status) }}>
                                            { (apiStatus.interview.data?.candidate_name && `Confirmed: ${apiStatus.interview.data.candidate_name}`) || apiStatus.interview.message || 'Pending IDs'}
                                        </Typography>
                                    </Box>
                                </Box>
                            </Box>

                            <Divider sx={{ my: Spacing.Medium }} />

                            {/* --- NEW: Fireflies Section --- */}
                            <FormControlLabel
                                control={
                                    <Switch
                                        checked={includeFireflies}
                                        onChange={(e) => setIncludeFireflies(e.target.checked)}
                                        name="includeFireflies"
                                    />
                                }
                                label="Include Fireflies.ai Transcript"
                                sx={{ mb: Spacing.Small }}
                            />
                            <Collapse in={includeFireflies}>
                                <Box sx={{ mb: Spacing.Medium, mt: Spacing.Small }}>
                                    <TextField
                                        fullWidth
                                        label="Fireflies.ai Transcript URL"
                                        value={firefliesUrl}
                                        onChange={(e) => setFirefliesUrl(e.target.value)}
                                        sx={{ mb: Spacing.Small }}
                                    />
                                    <Button
                                        fullWidth
                                        variant="outlined"
                                        onClick={handleFirefliesConfirm}
                                        disabled={!firefliesUrl}
                                    >
                                        Confirm Transcript
                                    </Button>
                                </Box>
                                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', p: 2, border: '1px solid #eee', borderRadius: 1, mb: Spacing.Medium }}>
                                    <Typography variant="body1" sx={{fontWeight: FontWeight.Medium}}>Transcript:</Typography>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                        {getStatusIcon(apiStatus.fireflies.status)}
                                        <Typography variant="body2" sx={{ color: getStatusColor(apiStatus.fireflies.status) }}>
                                            {apiStatus.fireflies.data?.meeting_title || apiStatus.fireflies.message || 'Pending URL'}
                                        </Typography>
                                    </Box>
                                </Box>
                            </Collapse>
                            <Divider sx={{ my: Spacing.Medium }} />


                            <TextField
                                fullWidth
                                multiline
                                rows={4}
                                label="Additional Context (Optional)"
                                name="additional_context"
                                value={formData.additional_context}
                                onChange={handleInputChange}
                                sx={{ mb: Spacing.Medium }}
                            />

                            <FormControlLabel
                                control={
                                    <Switch
                                        checked={isAnonymous}
                                        onChange={(e) => setIsAnonymous(e.target.checked)}
                                        name="anonymousSwitch"
                                        color="primary"
                                    />
                                }
                                label="Anonymous Reverse Sales Summary"
                                sx={{ mb: Spacing.Large, display: 'block' }}
                            />

                            <Box sx={{ display: 'flex', gap: Spacing.Default, alignItems: 'center', flexWrap: 'wrap' }}>
                                <Button
                                    variant="contained"
                                    onClick={generateSummary}
                                    disabled={isGenerateDisabled}
                                >
                                    {loading ? <CircularProgress size={24} /> : 'Generate Summary'}
                                </Button>
                                <Button variant="text" startIcon={<Refresh />} onClick={resetApiStatus}>
                                    Reset
                                </Button>
                            </Box>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} md={7}>
                    {generatedHtml && (
                        <Card>
                            <CardContent>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: Spacing.Medium }}>
                                    <Typography variant="h4">
                                        Candidate Ai Summary
                                    </Typography>
                                    <Button variant="contained" color="success" onClick={pushToRecruitCRM} disabled={pushing}>
                                        {pushing ? <CircularProgress size={24} /> : 'Push to RecruitCRM'}
                                    </Button>
                                </Box>

                                <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
                                    <Tabs value={view} onChange={handleViewChange} aria-label="summary view tabs">
                                        <Tab label="Preview" value="preview" />
                                        <Tab label="HTML" value="html" />
                                    </Tabs>
                                </Box>

                                {view === 'preview' && (
                                    <Paper sx={{ p: Spacing.Medium, backgroundColor: CustomColors.UIGrey100, border: `1px solid ${CustomColors.UIGrey300}`, borderRadius: 2 }}>
                                        <Box dangerouslySetInnerHTML={{ __html: generatedHtml }} />
                                    </Paper>
                                )}

                                {view === 'html' && (
                                    <TextField
                                        fullWidth
                                        multiline
                                        rows={75}
                                        label="HTML Source (Copy to ATS)"
                                        value={generatedHtml}
                                        InputProps={{
                                            readOnly: true,
                                            sx: { fontFamily: 'monospace', fontSize: '12px' }
                                        }}
                                        onClick={(e) => e.target.select()}
                                    />
                                )}

                                {/* --- NEW FEEDBACK SECTION --- */}
                                <Box sx={{ mt: 2, p: 2, border: `1px solid ${CustomColors.UIGrey300}`, borderRadius: 2, backgroundColor: '#fafafa' }}>
                                    {feedbackSubmitted ? (
                                        <Typography variant="body1" sx={{ color: CustomColors.SecretGarden, fontWeight: FontWeight.Medium, textAlign: 'center' }}>
                                            Thanks for your feedback!
                                        </Typography>
                                    ) : (
                                        <>
                                            <Typography variant="body2" sx={{ mb: 1, fontWeight: FontWeight.Medium, textAlign: 'center' }}>
                                                Was this summary helpful?
                                            </Typography>
                                            <Box sx={{ display: 'flex', justifyContent: 'center', gap: 1 }}>
                                                <Button variant="outlined" startIcon={<ThumbUp />} onClick={() => handleFeedbackSubmit('good')}>
                                                    Good
                                                </Button>
                                                <Button variant="outlined" color="error" startIcon={<ThumbDown />} onClick={() => setShowFeedbackComment(true)}>
                                                    Bad
                                                </Button>
                                            </Box>
                                            <Collapse in={showFeedbackComment}>
                                                <Box sx={{ mt: 2 }}>
                                                    <TextField
                                                        fullWidth
                                                        multiline
                                                        rows={3}
                                                        label="What was wrong with the summary?"
                                                        value={feedbackComment}
                                                        onChange={(e) => setFeedbackComment(e.target.value)}
                                                    />
                                                    <Button
                                                        variant="contained"
                                                        color="error"
                                                        sx={{ mt: 1 }}
                                                        onClick={() => handleFeedbackSubmit('bad')}
                                                    >
                                                        Submit Feedback
                                                    </Button>
                                                </Box>
                                            </Collapse>
                                        </>
                                    )}
                                </Box>
                            </CardContent>
                        </Card>
                    )}
                </Grid>
            </Grid>
        </Box>
    );
};

export default CandidateSummaryGenerator;
