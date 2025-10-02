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
    Collapse,
    FormControlLabel,
    Switch,
    FormControl,
    InputLabel,
    Select,
    MenuItem
} from '@mui/material';
import {
    CheckCircle,
    Cancel,
    HelpOutline,
    Refresh,
    ThumbUp,
    ThumbDown
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';

// --- Placeholder values for theme ---
const CustomColors = {
    SecretGarden: '#5a9a5a',
    DarkRed: '#b71c1c',
    DeepSkyBlue: '#00bfff',
    UIGrey500: '#9e9e9e',
    UIGrey300: '#e0e0e0',
    UIGrey100: '#f5f5f5',
    MidnightBlue: '#191970',
};
const FontWeight = { Medium: 500 };
const Spacing = { Large: 3, Medium: 2, Small: 1, Default: 1 };
// --- END ---

const CandidateSummaryGenerator = () => {
    const { loginWithGoogle } = useAuth();
    const [formData, setFormData] = useState({
        candidate_slug: '',
        job_slug: '',
        alpharun_job_id: '',
        interview_id: '',
        additional_context: '',
        fireflies_url: ''
    });

    const [recruitCrmUrl, setRecruitCrmUrl] = useState('');
    const [firefliesUrl, setFirefliesUrl] = useState('');

    const [apiStatus, setApiStatus] = useState({
        candidate: { status: 'pending', message: '', data: null },
        job: { status: 'pending', message: '', data: null },
        interview: { status: 'pending', message: '', data: null },
        fireflies: { status: 'pending', message: '', data: null },
        resume: { status: 'pending', message: '', data: null }
    });

    const [prompts, setPrompts] = useState([]);
    const [selectedPrompt, setSelectedPrompt] = useState('');
    
    // Email draft feature state
    const [createEmailDraft, setCreateEmailDraft] = useState(false);
    const [emailPrompts, setEmailPrompts] = useState([]);
    const [selectedEmailPrompt, setSelectedEmailPrompt] = useState('');
    const [generatedEmailHtml, setGeneratedEmailHtml] = useState('');
    const [creatingDraft, setCreatingDraft] = useState(false);
    const [draftUrl, setDraftUrl] = useState('');

    const [generatedHtml, setGeneratedHtml] = useState('');
    const [loading, setLoading] = useState(false);
    const [pushing, setPushing] = useState(false);
    const [alert, setAlert] = useState({ show: false, type: 'info', message: '' });
    const [view, setView] = useState('preview');
    const [includeFireflies, setIncludeFireflies] = useState(false);
    const [proceedWithoutInterview, setProceedWithoutInterview] = useState(false);


    const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
    const [showFeedbackComment, setShowFeedbackComment] = useState(false);
    const [feedbackComment, setFeedbackComment] = useState('');

    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

    useEffect(() => {
        const fetchPrompts = async () => {
            if (!API_BASE_URL) return;
            try {
                // Fetch summary prompts
                const summaryResponse = await fetch(`${API_BASE_URL}/api/prompts?type=summary`);
                if (!summaryResponse.ok) throw new Error('Failed to fetch summary prompts');
                const summaryData = await summaryResponse.json();
                setPrompts(summaryData);
                if (summaryData.length > 0) {
                    const defaultPrompt = summaryData.find(p => p.id === 'recruitment.detailed-v2') || summaryData[0];
                    setSelectedPrompt(defaultPrompt.id);
                }
                
                // Fetch email prompts
                const emailResponse = await fetch(`${API_BASE_URL}/api/prompts?type=email`);
                if (!emailResponse.ok) throw new Error('Failed to fetch email prompts');
                const emailData = await emailResponse.json();
                setEmailPrompts(emailData);
                if (emailData.length > 0) {
                    setSelectedEmailPrompt(emailData[0].id);
                }
            } catch (error) {
                showAlert('error', `Could not load summary types: ${error.message}`);
            }
        };
        fetchPrompts();
    }, [API_BASE_URL]);

    useEffect(() => {
        if (apiStatus.candidate.status === 'success' && formData.candidate_slug) {
            testApi('resume', { candidate_slug: formData.candidate_slug });
        }
    }, [apiStatus.candidate.status, formData.candidate_slug]);

    useEffect(() => {
        const interviewData = apiStatus.interview.data;
        if (interviewData?.success) {
            setFormData(prev => ({
                ...prev,
                interview_id: interviewData.interview_id || prev.interview_id,
                alpharun_job_id: interviewData.alpharun_job_id || prev.alpharun_job_id
            }));
        }
    }, [apiStatus.interview.data]);

    const testApi = async (apiType, payload) => {
        if (!API_BASE_URL) return;
        setApiStatus(prev => ({ ...prev, [apiType]: { status: 'loading', message: 'Confirming...', data: null } }));
        try {
            const response = await fetch(`${API_BASE_URL}/api/test-${apiType}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            if (response.ok && data.success) {
                setApiStatus(prev => ({ ...prev, [apiType]: { status: 'success', message: data.message, data: data } }));
            } else {
                setApiStatus(prev => ({ ...prev, [apiType]: { status: 'error', message: data.error || data.message, data: null } }));
            }
        } catch (error) {
            setApiStatus(prev => ({ ...prev, [apiType]: { status: 'error', message: `Network error: ${error.message}`, data: null } }));
        }
    };

    const handleParseAndConfirm = () => {
        if (!recruitCrmUrl) {
            showAlert('error', 'Please paste the RecruitCRM URL first.');
            return;
        }

        const regex = /candidate-sequence\/([^/]+)\/assigned_candidates\/\d+\/([^/]+)/;
        const match = recruitCrmUrl.match(regex);

        if (match && match[1] && match[2]) {
            const jobSlug = match[1];
            const candidateSlug = match[2];

            showAlert('info', 'URL parsed. Confirming Job, Candidate & Interview...');

            setFormData(prev => ({
                ...prev,
                job_slug: jobSlug,
                candidate_slug: candidateSlug
            }));

            testApi('job', { job_slug: jobSlug });
            testApi('candidate', { candidate_slug: candidateSlug });
            testApi('interview', { candidate_slug: candidateSlug, job_slug: jobSlug });
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
            fireflies: { status: 'pending', message: '', data: null },
            resume: { status: 'pending', message: '', data: null }
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
        setGeneratedEmailHtml('');
        setDraftUrl('');
        setFeedbackSubmitted(false);
        setShowFeedbackComment(false);
        setFeedbackComment('');
        setIncludeFireflies(false);
        setProceedWithoutInterview(false);
        setCreateEmailDraft(false);
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

        const baseApisSuccess = apiStatus.candidate.status === 'success' && apiStatus.job.status === 'success';
        const interviewApiSuccess = apiStatus.interview.status === 'success' || proceedWithoutInterview;
        const firefliesApiSuccess = !includeFireflies || apiStatus.fireflies.status === 'success';

        if (!baseApisSuccess || !interviewApiSuccess || !firefliesApiSuccess) {
            showAlert('error', 'Please ensure all required details are confirmed successfully.');
            return;
        }
        if (!selectedPrompt) {
            showAlert('error', 'Please select a summary type.');
            return;
        }
        if (createEmailDraft && !selectedEmailPrompt) {
            showAlert('error', 'Please select an email template.');
            return;
        }
        
        setLoading(true);
        setFeedbackSubmitted(false);
        setShowFeedbackComment(false);
        setFeedbackComment('');
        setDraftUrl('');
        
        try {
            const basePayload = { ...formData };
            if (!includeFireflies) {
                delete basePayload.fireflies_url;
            }
            if (proceedWithoutInterview) {
                delete basePayload.interview_id;
                delete basePayload.alpharun_job_id;
            }

            // Generate summary (and optionally email) in parallel
            const requests = [
                fetch(`${API_BASE_URL}/api/generate-summary`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ...basePayload, prompt_type: selectedPrompt })
                })
            ];

            if (createEmailDraft) {
                requests.push(
                    fetch(`${API_BASE_URL}/api/generate-summary`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ ...basePayload, prompt_type: selectedEmailPrompt })
                    })
                );
            }

            const responses = await Promise.all(requests);
            const [summaryResponse, emailResponse] = responses;
            
            const summaryData = await summaryResponse.json();
            if (summaryData.success) {
                setGeneratedHtml(summaryData.html_summary);
                showAlert('success', 'Summary generated successfully!');
            } else {
                showAlert('error', summaryData.error || 'Failed to generate summary');
                setLoading(false);
                return;
            }

            if (createEmailDraft && emailResponse) {
                const emailData = await emailResponse.json();
                if (emailData.success) {
                    setGeneratedEmailHtml(emailData.html_summary);
                } else {
                    showAlert('warning', 'Summary generated but email failed: ' + (emailData.error || 'Unknown error'));
                }
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

    const createGmailDraft = async () => {
        if (!API_BASE_URL) return;

        if (!generatedEmailHtml) {
            showAlert('error', 'No email content to create draft');
            return;
        }

        // Check for existing access token
        let accessToken = sessionStorage.getItem('google_access_token');
        
        // If no token, prompt user to re-authenticate with Gmail scope
        if (!accessToken) {
            try {
                showAlert('info', 'Requesting Gmail permissions...');
                await loginWithGoogle();
                accessToken = sessionStorage.getItem('google_access_token');
                
                if (!accessToken) {
                    showAlert('error', 'Failed to get Gmail permissions. Please try again.');
                    return;
                }
            } catch (error) {
                showAlert('error', 'Failed to authenticate with Google: ' + error.message);
                return;
            }
        }

        // Extract candidate name and job title for subject
        const candidateName = apiStatus.candidate.data?.candidate_name || 'Candidate';
        const jobTitle = apiStatus.job.data?.job_name || 'Position';
        const subject = `${candidateName} - ${jobTitle}`;

        setCreatingDraft(true);
        try {
            const response = await fetch(`${API_BASE_URL}/api/create-gmail-draft`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    access_token: accessToken,
                    subject: subject,
                    html_body: generatedEmailHtml,
                    to_email: '' // Leave blank for user to fill
                })
            });

            const data = await response.json();

            if (data.success) {
                setDraftUrl(data.draft_url);
                showAlert('success', 'Gmail draft created successfully!');
            } else {
                // If token expired, clear it and ask user to try again
                if (data.error?.includes('invalid') || data.error?.includes('expired')) {
                    sessionStorage.removeItem('google_access_token');
                    showAlert('error', 'Gmail session expired. Please click "Create Draft" again to re-authenticate.');
                } else {
                    showAlert('error', data.error || 'Failed to create Gmail draft');
                }
            }
        } catch (error) {
            showAlert('error', 'Network error: ' + error.message);
        } finally {
            setCreatingDraft(false);
        }
    };

    const handleFeedbackSubmit = async (rating) => {
        if (!API_BASE_URL) return;
        const payload = {
            rating: rating,
            comments: feedbackComment,
            prompt_type: selectedPrompt,
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
        !(apiStatus.candidate.status === 'success' && apiStatus.job.status === 'success') ||
        !(apiStatus.interview.status === 'success' || proceedWithoutInterview) ||
        !(!includeFireflies || apiStatus.fireflies.status === 'success');

    const showProceedWithoutInterviewSwitch = apiStatus.candidate.status !== 'pending' &&
        apiStatus.job.status !== 'pending' &&
        apiStatus.interview.status !== 'success' &&
        apiStatus.interview.status !== 'loading';

    return (
        <Box>
            {alert.show && <Alert severity={alert.type} sx={{ mb: Spacing.Medium }}>{alert.message}</Alert>}
            <Grid container spacing={Spacing.Large}>
                <Grid item xs={12} md={5}>
                    <Card>
                        <CardContent>
                            <Typography variant="h4" sx={{ mb: Spacing.Medium }}>Input Data</Typography>
                            <Box sx={{ position: 'relative', mb: Spacing.Medium }}>
                                <TextField fullWidth label="RecruitCRM URL" name="recruitCrmUrl" value={recruitCrmUrl} onChange={(e) => { setRecruitCrmUrl(e.target.value); if (apiStatus.candidate.status !== 'pending' || apiStatus.job.status !== 'pending' || apiStatus.interview.status !== 'pending') { resetApiStatus(); } }} sx={{ mb: Spacing.Small }} placeholder="Paste URL from RecruitCRM here..." required />
                                <Button fullWidth variant="outlined" onClick={handleParseAndConfirm} disabled={!recruitCrmUrl}>Parse URL & Confirm Details</Button>
                            </Box>
                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: Spacing.Medium, p: 2, border: '1px solid #eee', borderRadius: 1 }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}><Typography variant="body1" sx={{fontWeight: FontWeight.Medium}}>Job Description:</Typography><Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>{getStatusIcon(apiStatus.job.status)}<Typography variant="body2" sx={{ color: getStatusColor(apiStatus.job.status) }}>{apiStatus.job.data?.job_name || apiStatus.job.message || 'Pending URL Parse'}</Typography></Box></Box>
                                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}><Typography variant="body1" sx={{fontWeight: FontWeight.Medium}}>Candidate Profile:</Typography><Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>{getStatusIcon(apiStatus.candidate.status)}<Typography variant="body2" sx={{ color: getStatusColor(apiStatus.candidate.status) }}>{apiStatus.candidate.data?.candidate_name || apiStatus.candidate.message || 'Pending URL Parse'}</Typography></Box></Box>
                                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}><Typography variant="body1" sx={{fontWeight: FontWeight.Medium}}>Anna Ai Interview:</Typography><Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>{getStatusIcon(apiStatus.interview.status)}<Typography variant="body2" sx={{ color: getStatusColor(apiStatus.interview.status) }}>{ (apiStatus.interview.data?.candidate_name && `Confirmed: ${apiStatus.interview.data.candidate_name}`) || apiStatus.interview.message || 'Pending IDs'}</Typography></Box></Box>
                                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}><Typography variant="body1" sx={{fontWeight: FontWeight.Medium}}>Candidate Resume:</Typography><Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>{getStatusIcon(apiStatus.resume.status)}<Typography variant="body2" sx={{ color: getStatusColor(apiStatus.resume.status) }}>{apiStatus.resume.data?.resume_name || apiStatus.resume.message || 'Pending Candidate'}</Typography></Box></Box>
                            </Box>

                            {showProceedWithoutInterviewSwitch && (
                                <FormControlLabel
                                    control={<Switch checked={proceedWithoutInterview} onChange={(e) => setProceedWithoutInterview(e.target.checked)} name="proceedWithoutInterview" />}
                                    label="Proceed without Anna AI Interview"
                                    sx={{ mb: Spacing.Small }}
                                />
                            )}

                            <Divider sx={{ my: Spacing.Medium }} />
                            <FormControlLabel control={<Switch checked={includeFireflies} onChange={(e) => setIncludeFireflies(e.target.checked)} name="includeFireflies" />} label="Include Fireflies.ai Transcript" sx={{ mb: Spacing.Small }} />
                            <Collapse in={includeFireflies}>
                                <Box sx={{ mb: Spacing.Medium, mt: Spacing.Small }}>
                                    <TextField fullWidth label="Fireflies.ai Transcript URL" value={firefliesUrl} onChange={(e) => setFirefliesUrl(e.target.value)} sx={{ mb: Spacing.Small }} />
                                    <Button fullWidth variant="outlined" onClick={handleFirefliesConfirm} disabled={!firefliesUrl}>Confirm Transcript</Button>
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
                            <TextField fullWidth multiline rows={4} label="Additional Context (Optional)" name="additional_context" value={formData.additional_context} onChange={handleInputChange} sx={{ mb: Spacing.Medium }} />
                            <FormControl fullWidth sx={{ mb: Spacing.Large }}>
                                <InputLabel id="prompt-select-label">Summary Type</InputLabel>
                                <Select labelId="prompt-select-label" value={selectedPrompt} label="Summary Type" onChange={(e) => setSelectedPrompt(e.target.value)} disabled={prompts.length === 0}>
                                    {prompts.map((prompt) => (<MenuItem key={prompt.id} value={prompt.id}>{prompt.name}</MenuItem>))}
                                </Select>
                            </FormControl>
                            
                            <Divider sx={{ my: Spacing.Medium }} />
                            
                            <FormControlLabel 
                                control={<Switch checked={createEmailDraft} onChange={(e) => setCreateEmailDraft(e.target.checked)} name="createEmailDraft" />} 
                                label="Create Email Draft in Gmail" 
                                sx={{ mb: Spacing.Small }} 
                            />
                            
                            <Collapse in={createEmailDraft}>
                                <FormControl fullWidth sx={{ mb: Spacing.Large }}>
                                    <InputLabel id="email-prompt-select-label">Email Template</InputLabel>
                                    <Select 
                                        labelId="email-prompt-select-label" 
                                        value={selectedEmailPrompt} 
                                        label="Email Template" 
                                        onChange={(e) => setSelectedEmailPrompt(e.target.value)} 
                                        disabled={emailPrompts.length === 0}
                                    >
                                        {emailPrompts.map((prompt) => (
                                            <MenuItem key={prompt.id} value={prompt.id}>{prompt.name}</MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                            </Collapse>
                            
                            <Box sx={{ display: 'flex', gap: Spacing.Default, alignItems: 'center', flexWrap: 'wrap' }}>
                                <Button variant="contained" onClick={generateSummary} disabled={isGenerateDisabled}>{loading ? <CircularProgress size={24} /> : 'Generate Summary'}</Button>
                                <Button variant="text" startIcon={<Refresh />} onClick={resetApiStatus}>Reset</Button>
                            </Box>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} md={7}>
                    {generatedHtml && (
                        <Card>
                            <CardContent>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: Spacing.Medium, flexWrap: 'wrap', gap: 1 }}>
                                    <Typography variant="h4">
                                        Candidate Ai Summary
                                    </Typography>
                                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                                        <Button variant="contained" color="success" onClick={pushToRecruitCRM} disabled={pushing}>
                                            {pushing ? <CircularProgress size={24} /> : 'Push to RecruitCRM'}
                                        </Button>
                                        {generatedEmailHtml && (
                                            <Button variant="contained" color="primary" onClick={createGmailDraft} disabled={creatingDraft}>
                                                {creatingDraft ? <CircularProgress size={24} /> : 'Create Draft in Gmail'}
                                            </Button>
                                        )}
                                    </Box>
                                </Box>
                                
                                {draftUrl && (
                                    <Alert severity="success" sx={{ mb: 2 }}>
                                        Gmail draft created! <a href={draftUrl} target="_blank" rel="noopener noreferrer">Open in Gmail</a>
                                    </Alert>
                                )}

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