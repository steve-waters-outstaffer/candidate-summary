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
    Divider,
    FormGroup,
    FormControlLabel,
    Switch,
    Accordion,
    AccordionSummary,
    AccordionDetails,
    Tooltip
} from '@mui/material';
import {
    CheckCircle,
    Cancel,
    HelpOutline,
    ExpandMore as ExpandMoreIcon,
    CloudUpload as CloudUploadIcon,
    Error as ErrorIcon
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

    // --- NEW: State for new features ---
    const [generateSummaries, setGenerateSummaries] = useState(false);
    const [generateEmail, setGenerateEmail] = useState(true);
    const [autoPush, setAutoPush] = useState(false);
    const [singlePrompts, setSinglePrompts] = useState([]);
    const [selectedSinglePrompt, setSelectedSinglePrompt] = useState('');
    const [generatedSummaries, setGeneratedSummaries] = useState(null);
    const [pushStatuses, setPushStatuses] = useState({});

    // Status tracking
    const [candidateStatuses, setCandidateStatuses] = useState({});
    const [jobStatus, setJobStatus] = useState({ status: 'pending', message: '', data: null });
    const [availablePrompts, setAvailablePrompts] = useState([]);
    const [generatedContent, setGeneratedContent] = useState('');
    const [loading, setLoading] = useState(false);
    const [alert, setAlert] = useState({ show: false, type: 'info', message: '' });
    const [view, setView] = useState('preview');

    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

    useEffect(() => {
        fetchAvailablePrompts('multiple', setAvailablePrompts, (p) => setFormData(prev => ({ ...prev, prompt_type: p })));
        fetchAvailablePrompts('single', setSinglePrompts, setSelectedSinglePrompt);
    }, []);

    const fetchAvailablePrompts = async (category, setter, defaultSetter) => {
        if (!API_BASE_URL) return;
        try {
            const response = await fetch(`${API_BASE_URL}/api/prompts?category=${category}`);
            if (response.ok) {
                const prompts = await response.json();
                setter(prompts);
                if (prompts.length > 0) {
                    defaultSetter(prompts[0].id);
                }
            }
        } catch (error) {
            console.error(`Error fetching ${category} prompts:`, error);
        }
    };

    const handleInputChange = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    const handleCandidateUrlChange = (index, value) => {
        const newUrls = [...candidateUrls];
        newUrls[index] = value;
        setCandidateUrls(newUrls);

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

        if (index === 0 && value.trim()) {
            extractAndValidateJobFromUrl(value);
        }
    };

    const extractAndValidateJobFromUrl = (candidateUrl) => {
        const regex = /candidate-sequence\/([^/]+)\/assigned_candidates\/\d+\/([^/]+)/;
        const match = candidateUrl.match(regex);

        if (match && match[1]) {
            validateJob(match[1]);
        } else {
            setJobStatus({ status: 'error', message: 'Could not extract job from URL', data: null });
        }
    };

    const validateJob = async (jobSlug) => {
        setJobStatus({ status: 'loading', message: 'Confirming job...', data: { slug: jobSlug } });
        try {
            const response = await fetch(`${API_BASE_URL}/api/test-job`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ job_slug: jobSlug })
            });

            if (response.ok) {
                const data = await response.json();
                setJobStatus({ status: 'success', message: data.job_name, data: data });
            } else {
                const errorData = await response.json();
                setJobStatus({ status: 'error', message: errorData.error || 'Failed to validate job', data: null });
            }
        } catch (error) {
            setJobStatus({ status: 'error', message: 'Network error validating job', data: null });
        }
    };

    const validateCandidate = async (index) => {
        const url = candidateUrls[index];
        if (!url.trim()) return;

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
                setCandidateStatuses(prev => ({ ...prev, [index]: { ...prev[index], candidate: { status: 'success', message: data.candidate_name, data: data } } }));
                validateResume(index, slug);
                if (data.interview_id && jobStatus.data?.alpharun_job_id) {
                    validateInterview(index, data.interview_id, jobStatus.data.alpharun_job_id);
                }
            } else {
                const errorData = await response.json();
                setCandidateStatuses(prev => ({ ...prev, [index]: { ...prev[index], candidate: { status: 'error', message: errorData.error || 'Failed to confirm', data: null } } }));
            }
        } catch (error) {
            setCandidateStatuses(prev => ({ ...prev, [index]: { ...prev[index], candidate: { status: 'error', message: 'Network error', data: null } } }));
        }
    };

    const validateResume = async (index, candidateSlug) => {
        setCandidateStatuses(prev => ({
            ...prev,
            [index]: { ...prev[index], resume: { status: 'loading', message: 'Checking resume...', data: null } }
        }));
        try {
            const response = await fetch(`${API_BASE_URL}/api/test-resume`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ candidate_slug: candidateSlug })
            });
            const data = await response.json();
            if (response.ok) {
                setCandidateStatuses(prev => ({ ...prev, [index]: { ...prev[index], resume: { status: data.success ? 'success' : 'error', message: data.message, data } } }));
            } else {
                setCandidateStatuses(prev => ({ ...prev, [index]: { ...prev[index], resume: { status: 'error', message: data.error || 'Check failed', data: null } } }));
            }
        } catch (error) {
            setCandidateStatuses(prev => ({ ...prev, [index]: { ...prev[index], resume: { status: 'error', message: 'Network error', data: null } } }));
        }
    };

    const validateInterview = async (index, interviewId, alpharunJobId) => {
        setCandidateStatuses(prev => ({
            ...prev,
            [index]: { ...prev[index], interview: { status: 'loading', message: 'Checking interview...', data: null } }
        }));
        try {
            const response = await fetch(`${API_BASE_URL}/api/test-interview`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ interview_id: interviewId, alpharun_job_id: alpharunJobId })
            });
            const data = await response.json();
            if (response.ok) {
                setCandidateStatuses(prev => ({ ...prev, [index]: { ...prev[index], interview: { status: 'success', message: 'Interview found', data } } }));
            } else {
                setCandidateStatuses(prev => ({ ...prev, [index]: { ...prev[index], interview: { status: 'error', message: 'No interview found', data: null } } }));
            }
        } catch (error) {
            setCandidateStatuses(prev => ({ ...prev, [index]: { ...prev[index], interview: { status: 'error', message: 'Network error', data: null } } }));
        }
    };

    const handleProcessCandidates = async () => {
        const validUrls = candidateUrls.filter(url => url.trim());
        if (validUrls.length === 0) {
            showAlert('error', 'Please provide at least one candidate URL');
            return;
        }

        const jobSlug = jobStatus.data?.slug;
        if (!jobSlug) {
            showAlert('error', 'Job has not been successfully validated.');
            return;
        }

        setLoading(true);
        setAlert({ show: false });
        setGeneratedContent('');
        setGeneratedSummaries(null);
        setPushStatuses({});

        const candidateSlugs = validUrls.map(url => url.split('/').pop());

        try {
            const response = await fetch(`${API_BASE_URL}/api/process-curated-candidates`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    job_slug: jobSlug,
                    candidate_slugs: candidateSlugs,
                    client_name: formData.client_name,
                    job_url: formData.outstaffer_platform_url,
                    preferred_candidate: formData.preferred_candidate,
                    additional_context: formData.additional_context,
                    multi_prompt_type: formData.prompt_type,
                    single_prompt_type: selectedSinglePrompt,
                    generate_email: generateEmail,
                    generate_summaries: generateSummaries,
                    auto_push: autoPush,
                })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.email_html) setGeneratedContent(data.email_html);
                if (data.summaries) setGeneratedSummaries(data.summaries);
                showAlert('success', 'Processing complete!');
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

    const handlePushToCrm = async (candidateSlug, summaryHtml) => {
        setPushStatuses(prev => ({ ...prev, [candidateSlug]: { status: 'loading' } }));
        try {
            const response = await fetch(`${API_BASE_URL}/api/push-to-recruitcrm`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ candidate_slug: candidateSlug, html_summary: summaryHtml }),
            });
            if (response.ok) {
                setPushStatuses(prev => ({ ...prev, [candidateSlug]: { status: 'success' } }));
            } else {
                const errorData = await response.json();
                setPushStatuses(prev => ({ ...prev, [candidateSlug]: { status: 'error', message: errorData.error } }));
            }
        } catch (error) {
            setPushStatuses(prev => ({ ...prev, [candidateSlug]: { status: 'error', message: 'Network error' } }));
        }
    };

    const handlePushAllToCrm = async () => {
        if (!generatedSummaries) return;
        for (const summary of generatedSummaries) {
            if (pushStatuses[summary.slug]?.status !== 'success') {
                await handlePushToCrm(summary.slug, summary.html);
            }
        }
    };

    const renderPushStatusIcon = (slug) => {
        const status = pushStatuses[slug];
        if (!status) return null;
        switch (status.status) {
            case 'loading': return <CircularProgress size={24} sx={{ ml: 1 }} />;
            case 'success': return <Tooltip title="Pushed successfully"><CheckCircle color="success" sx={{ ml: 1 }} /></Tooltip>;
            case 'error': return <Tooltip title={status.message || 'An error occurred'}><ErrorIcon color="error" sx={{ ml: 1 }} /></Tooltip>;
            default: return null;
        }
    };

    const showAlert = (type, message) => {
        setAlert({ show: true, type, message });
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
        return Object.values(candidateStatuses)
            .filter(status => status?.candidate?.status === 'success')
            .map(status => status.candidate.data.candidate_name);
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

    const isGenerateDisabled = loading ||
        Object.values(candidateStatuses).filter(s => s.candidate?.status === 'success').length === 0 ||
        (!generateEmail && !generateSummaries) ||
        jobStatus.status !== 'success';

    return (
        <Box>
            {alert.show && <Alert severity={alert.type} sx={{ mb: Spacing.Medium }}>{alert.message}</Alert>}
            <Grid container spacing={Spacing.Large}>
                <Grid item xs={12} md={5}>
                    <Card>
                        <CardContent>
                            <Typography variant="h4" sx={{ mb: Spacing.Medium }}>Input Data</Typography>

                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: Spacing.Medium, p: 2, border: '1px solid #eee', borderRadius: 1 }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                    <Typography variant="body1" sx={{ fontWeight: FontWeight.Medium }}>Job Description:</Typography>
                                    <Typography variant="body2" sx={{ color: getStatusColor(jobStatus.status) }}>
                                        {jobStatus.message || 'Pending first candidate URL'}
                                    </Typography>
                                </Box>
                            </Box>

                            <Typography variant="h6" sx={{ mb: 2 }}>Candidates</Typography>
                            {candidateUrls.map((_, index) => renderCandidateUrlField(index))}
                            <Divider sx={{ my: Spacing.Medium }} />

                            <Typography variant="h6" sx={{ mb: 2 }}>Processing Options</Typography>
                            <FormGroup>
                                <FormControlLabel
                                    control={<Switch checked={generateSummaries} onChange={(e) => setGenerateSummaries(e.target.checked)} />}
                                    label="Generate Individual Summaries"
                                />

                            </FormGroup>

                            {generateSummaries && (
                                <>
                                    <FormControl fullWidth sx={{ mt: 2, mb: 1 }}>
                                        <InputLabel>Summary Prompt</InputLabel>
                                        <Select value={selectedSinglePrompt} onChange={(e) => setSelectedSinglePrompt(e.target.value)} label="Summary Prompt">
                                            {singlePrompts.map((p) => <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}
                                        </Select>
                                    </FormControl>
                                    <FormGroup>
                                        <FormControlLabel
                                            control={<Switch checked={autoPush} onChange={(e) => setAutoPush(e.target.checked)} />}
                                            label="Auto-push summaries to RecruitCRM"
                                        />
                                    </FormGroup>
                                </>
                            )}
                            <FormGroup>
                                <FormControlLabel
                                    control={<Switch checked={generateEmail} onChange={(e) => setGenerateEmail(e.target.checked)} />}
                                    label="Generate Multi-Candidate Email"
                                />
                            </FormGroup>
                            {generateEmail && (
                                <>
                                    <Typography variant="h6" sx={{ mt: 2, mb: 2 }}>Email Details</Typography>
                                    <TextField
                                        label="Client Name"
                                        value={formData.client_name}
                                        onChange={(e) => handleInputChange('client_name', e.target.value)}
                                        fullWidth sx={{ mb: 2 }}
                                    />
                                    <FormControl fullWidth sx={{ mb: 2 }}>
                                        <InputLabel>Preferred Candidate</InputLabel>
                                        <Select
                                            value={formData.preferred_candidate}
                                            onChange={(e) => handleInputChange('preferred_candidate', e.target.value)}
                                            label="Preferred Candidate"
                                        >
                                            <MenuItem value=""><em>None</em></MenuItem>
                                            {getValidatedCandidateNames().map((name) => (
                                                <MenuItem key={name} value={name}>{name}</MenuItem>
                                            ))}
                                        </Select>
                                    </FormControl>
                                    <TextField
                                        label="Additional Context (Optional)"
                                        value={formData.additional_context}
                                        onChange={(e) => handleInputChange('additional_context', e.target.value)}
                                        fullWidth multiline rows={4} sx={{ mb: 2 }}
                                    />
                                    <TextField
                                        label="Outstaffer Platform URL (Optional)"
                                        value={formData.outstaffer_platform_url}
                                        onChange={(e) => handleInputChange('outstaffer_platform_url', e.target.value)}
                                        fullWidth sx={{ mb: 2 }} placeholder="Link to embed in email..."
                                    />
                                    <FormControl fullWidth sx={{ mb: 2 }}>
                                        <InputLabel>Email Template</InputLabel>
                                        <Select
                                            value={formData.prompt_type}
                                            onChange={(e) => handleInputChange('prompt_type', e.target.value)}
                                            label="Email Template"
                                        >
                                            {availablePrompts.map((prompt) => (
                                                <MenuItem key={prompt.id} value={prompt.id}>{prompt.name}</MenuItem>
                                            ))}
                                        </Select>
                                    </FormControl>
                                </>
                            )}
                            <Button
                                variant="contained"
                                color="primary"
                                onClick={handleProcessCandidates}
                                disabled={isGenerateDisabled}
                                fullWidth
                                sx={{ mt: 2, mb: 1 }}
                            >
                                {loading ? <CircularProgress size={24} /> : 'Process Candidates'}
                            </Button>
                        </CardContent>
                    </Card>
                </Grid>

                <Grid item xs={12} md={7}>
                    {generatedSummaries && (
                        <Card sx={{ mb: 3 }}>
                            <CardContent>
                                <Typography variant="h5" gutterBottom>Individual Summaries</Typography>
                                {!autoPush && (
                                    <Button variant="outlined" onClick={handlePushAllToCrm} startIcon={<CloudUploadIcon />} sx={{ my: 2 }}>
                                        Send All to RecruitCRM
                                    </Button>
                                )}
                                {generatedSummaries.map((summary, index) => (
                                    <Accordion key={index}>
                                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                                            <Box sx={{ display: 'flex', alignItems: 'center', width: '100%', justifyContent: 'space-between' }}>
                                                <Typography>{summary.name}</Typography>
                                                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                                    {renderPushStatusIcon(summary.slug)}
                                                    {!autoPush && pushStatuses[summary.slug]?.status !== 'success' && (
                                                        <Button
                                                            variant="contained" color="success" size="small" sx={{ ml: 3 }}
                                                            onClick={(e) => { e.stopPropagation(); handlePushToCrm(summary.slug, summary.html); }}
                                                            disabled={pushStatuses[summary.slug]?.status === 'loading'}
                                                        >
                                                            Push
                                                        </Button>
                                                    )}
                                                </Box>
                                            </Box>
                                        </AccordionSummary>
                                        <AccordionDetails>
                                            <Paper variant="outlined" sx={{ p: 2, backgroundColor: CustomColors.UIGrey100 }}>
                                                <Box dangerouslySetInnerHTML={{ __html: summary.html }} />
                                            </Paper>
                                        </AccordionDetails>
                                    </Accordion>
                                ))}
                            </CardContent>
                        </Card>
                    )}

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
                                    <Paper sx={{ p: Spacing.Medium, backgroundColor: CustomColors.UIGrey100, border: `1px solid ${CustomColors.UIGrey300}`, borderRadius: 2, maxHeight: '600px', overflow: 'auto' }}>
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
                                        InputProps={{ readOnly: true, sx: { fontFamily: 'monospace', fontSize: '12px' } }}
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