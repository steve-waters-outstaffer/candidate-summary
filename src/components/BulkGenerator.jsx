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
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    FormGroup,
    FormControlLabel,
    Accordion,
    AccordionSummary,
    AccordionDetails,
    Grid,
    Tooltip,
    Switch
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';

const BulkGenerator = () => {
    const [jobUrl, setJobUrl] = useState('');
    const [jobStages, setJobStages] = useState([]);
    const [selectedStage, setSelectedStage] = useState('');
    const [singleCandidatePrompt, setSingleCandidatePrompt] = useState('');
    const [multiCandidatePrompt, setMultiCandidatePrompt] = useState('');
    const [availableSinglePrompts, setAvailableSinglePrompts] = useState([]);
    const [availableMultiPrompts, setAvailableMultiPrompts] = useState([]);
    const [generateEmail, setGenerateEmail] = useState(true);
    const [autoPush, setAutoPush] = useState(false);
    const [loading, setLoading] = useState(false);
    const [jobLoading, setJobLoading] = useState(false);
    const [alert, setAlert] = useState({ show: false, type: 'info', message: '' });
    const [results, setResults] = useState(null);
    const [pushStatuses, setPushStatuses] = useState({});

    // --- NEW: State for email detail inputs ---
    const [emailDetails, setEmailDetails] = useState({
        client_name: '',
        preferred_candidate: '',
        additional_context: '',
        outstaffer_platform_url: ''
    });

    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

    useEffect(() => {
        fetchAvailablePrompts('single', setAvailableSinglePrompts, setSingleCandidatePrompt);
        fetchAvailablePrompts('multiple', setAvailableMultiPrompts, setMultiCandidatePrompt);
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

    const handleJobUrlChange = (e) => {
        const url = e.target.value;
        setJobUrl(url);
        const match = url.match(/\/job\/([a-zA-Z0-9]+)/);
        if (match && match[1]) {
            const slug = match[1];
            fetchJobStages(slug);
        } else {
            setJobStages([]);
            setSelectedStage('');
        }
    };

    // --- NEW: Handler for email detail inputs ---
    const handleEmailDetailsChange = (e) => {
        const { name, value } = e.target;
        setEmailDetails(prev => ({ ...prev, [name]: value }));
    };

    const fetchJobStages = async (jobSlug) => {
        setJobLoading(true);
        try {
            const url = `${API_BASE_URL}/api/job-stages-with-counts/${jobSlug}`;
            const response = await fetch(url);
            if (response.ok) {
                const stages = await response.json();
                setJobStages(stages);
                if (stages.length > 0) {
                    setSelectedStage(stages[0].status_id);
                }
            } else {
                showAlert('error', 'Could not fetch job stages. Please check the URL.');
                setJobStages([]);
            }
        } catch (error) {
            console.error('Error in fetchJobStages:', error);
            showAlert('error', 'Network error fetching job stages.');
        } finally {
            setJobLoading(false);
        }
    };

    const handleBulkProcess = async () => {
        setLoading(true);
        setResults(null);
        setPushStatuses({});
        setAlert({ show: false });

        try {
            const response = await fetch(`${API_BASE_URL}/api/bulk-process-job`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    job_url: jobUrl,
                    status_id: selectedStage,
                    single_candidate_prompt: singleCandidatePrompt,
                    multi_candidate_prompt: multiCandidatePrompt,
                    generate_email: generateEmail,
                    auto_push: autoPush,
                    // --- NEW: Pass email details to backend ---
                    client_name: emailDetails.client_name,
                    preferred_candidate: emailDetails.preferred_candidate,
                    additional_context: emailDetails.additional_context,
                    outstaffer_platform_url: emailDetails.outstaffer_platform_url
                }),
            });

            const data = await response.json();
            if (response.ok) {
                setResults(data);
                showAlert('success', `Processing complete. Found ${data.candidates_found} candidates.`);
            } else {
                showAlert('error', data.error || 'An unknown error occurred.');
            }
        } catch (error) {
            showAlert('error', 'A network error occurred during bulk processing.');
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
                body: JSON.stringify({
                    candidate_slug: candidateSlug,
                    html_summary: summaryHtml,
                }),
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
        if (!results || !results.summaries) return;
        for (const summary of results.summaries) {
            if (pushStatuses[summary.slug]?.status !== 'success') {
                await handlePushToCrm(summary.slug, summary.html);
            }
        }
    };

    const showAlert = (type, message) => {
        setAlert({ show: true, type, message });
    };

    const renderPushStatusIcon = (slug) => {
        const status = pushStatuses[slug];
        if (!status) return null;
        switch (status.status) {
            case 'loading':
                return <CircularProgress size={24} sx={{ ml: 1 }} />;
            case 'success':
                return (
                    <Tooltip title="Pushed successfully">
                        <CheckCircleIcon color="success" sx={{ ml: 1 }} />
                    </Tooltip>
                );
            case 'error':
                return (
                    <Tooltip title={status.message || 'An error occurred'}>
                        <ErrorIcon color="error" sx={{ ml: 1 }} />
                    </Tooltip>
                );
            default:
                return null;
        }
    };

    return (
        <Box>
            {alert.show && <Alert severity={alert.type} sx={{ mb: 2 }} onClose={() => setAlert({ show: false })}>{alert.message}</Alert>}
            <Grid container spacing={3}>
                <Grid item xs={12} md={5}>
                    <Card>
                        <CardContent>
                            <Typography variant="h4" gutterBottom>Bulk Process Job</Typography>
                            <TextField
                                label="RecruitCRM Job URL"
                                value={jobUrl}
                                onChange={handleJobUrlChange}
                                onPaste={handleJobUrlChange}
                                fullWidth
                                sx={{ mb: 2 }}
                                placeholder="Paste job URL to load stages..."
                            />
                            {jobLoading ? <CircularProgress sx={{ mb: 2 }} /> : (
                                <FormControl fullWidth sx={{ mb: 2 }} disabled={jobStages.length === 0}>
                                    <InputLabel>Candidate Stage</InputLabel>
                                    <Select value={selectedStage} onChange={(e) => setSelectedStage(e.target.value)} label="Candidate Stage">
                                        {jobStages.map((stage) => (
                                            <MenuItem key={stage.status_id} value={stage.status_id}>
                                                {stage.label} ({stage.candidate_count} candidates)
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                            )}
                            <FormControl fullWidth sx={{ mb: 2 }}>
                                <InputLabel>Summary Generation Prompt</InputLabel>
                                <Select value={singleCandidatePrompt} onChange={(e) => setSingleCandidatePrompt(e.target.value)} label="Summary Generation Prompt">
                                    {availableSinglePrompts.map((p) => <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}
                                </Select>
                            </FormControl>
                            <FormGroup>
                                <FormControlLabel
                                    control={<Switch checked={generateEmail} onChange={(e) => setGenerateEmail(e.target.checked)} />}
                                    label="Generate Multi-Candidate Email"
                                />
                            </FormGroup>

                            {/* --- MODIFIED: Added email detail form --- */}
                            {generateEmail && (
                                <>
                                    <Typography variant="h6" sx={{ mt: 2, mb: 2 }}>Email Details</Typography>
                                    <TextField
                                        label="Client Name"
                                        name="client_name"
                                        value={emailDetails.client_name}
                                        onChange={handleEmailDetailsChange}
                                        fullWidth sx={{ mb: 2 }}
                                    />
                                    <TextField
                                        label="Preferred Candidate (Optional)"
                                        name="preferred_candidate"
                                        value={emailDetails.preferred_candidate}
                                        onChange={handleEmailDetailsChange}
                                        fullWidth sx={{ mb: 2 }}
                                    />
                                    <TextField
                                        label="Additional Context (Optional)"
                                        name="additional_context"
                                        value={emailDetails.additional_context}
                                        onChange={handleEmailDetailsChange}
                                        fullWidth multiline rows={4} sx={{ mb: 2 }}
                                    />
                                    <TextField
                                        label="Outstaffer Platform URL (Optional)"
                                        name="outstaffer_platform_url"
                                        value={emailDetails.outstaffer_platform_url}
                                        onChange={handleEmailDetailsChange}
                                        fullWidth sx={{ mb: 2 }} placeholder="Link to embed in email..."
                                    />
                                    <FormControl fullWidth sx={{ mb: 2, mt: 1 }}>
                                        <InputLabel>Email Generation Prompt</InputLabel>
                                        <Select value={multiCandidatePrompt} onChange={(e) => setMultiCandidatePrompt(e.target.value)} label="Email Generation Prompt">
                                            {availableMultiPrompts.map((p) => <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}
                                        </Select>
                                    </FormControl>
                                </>
                            )}
                            <FormGroup>
                                <FormControlLabel
                                    control={<Switch checked={autoPush} onChange={(e) => setAutoPush(e.target.checked)} />}
                                    label="Automatically push summaries to RecruitCRM"
                                />
                            </FormGroup>
                            <Button
                                variant="contained"
                                onClick={handleBulkProcess}
                                disabled={loading || !selectedStage}
                                fullWidth
                                sx={{ mt: 2 }}
                                startIcon={loading ? <CircularProgress size={20} color="inherit" /> : null}
                            >
                                {loading ? 'Processing...' : 'Start Bulk Process'}
                            </Button>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} md={7}>
                    {results && (
                        <Card>
                            <CardContent>
                                <Typography variant="h5" gutterBottom>
                                    Results for: {results.job_title}
                                </Typography>
                                <Typography variant="body2" color="textSecondary" gutterBottom>
                                    {results.summaries_generated} summaries generated, {results.failures} failed.
                                </Typography>

                                {results.summaries_generated > 0 && !autoPush && (
                                    <Button
                                        variant="outlined"
                                        onClick={handlePushAllToCrm}
                                        startIcon={<CloudUploadIcon />}
                                        sx={{ my: 2 }}
                                    >
                                        Send All to RecruitCRM
                                    </Button>
                                )}

                                {results.summaries && results.summaries.map((summary, index) => (
                                    <Accordion key={index}>
                                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                                            <Box sx={{ display: 'flex', alignItems: 'center', width: '100%', justifyContent: 'space-between' }}>
                                                <Typography>{summary.name}</Typography>
                                                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                                    {renderPushStatusIcon(summary.slug)}
                                                    {!autoPush && pushStatuses[summary.slug]?.status !== 'success' && (
                                                        <Button
                                                            variant="outlined"
                                                            color="success"
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                handlePushToCrm(summary.slug, summary.html);
                                                            }}
                                                            disabled={pushStatuses[summary.slug]?.status === 'loading'}
                                                            size="small"
                                                            sx={{ ml: 3 }}
                                                        >
                                                            Push to RecruitCRM
                                                        </Button>
                                                    )}
                                                </Box>
                                            </Box>
                                        </AccordionSummary>
                                        <AccordionDetails>
                                            <Paper variant="outlined" sx={{ p: 2, backgroundColor: '#f9f9f9' }}>
                                                <Box dangerouslySetInnerHTML={{ __html: summary.html }} />
                                            </Paper>
                                        </AccordionDetails>
                                    </Accordion>
                                ))}
                                {results.email_html && (
                                    <Accordion sx={{ mt: 3 }}>
                                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                                            <Typography sx={{ fontWeight: 'bold' }}>Generated Email</Typography>
                                        </AccordionSummary>
                                        <AccordionDetails>
                                            <Paper variant="outlined" sx={{ p: 2 }}>
                                                <Box dangerouslySetInnerHTML={{ __html: results.email_html }} />
                                            </Paper>
                                        </AccordionDetails>
                                    </Accordion>
                                )}
                            </CardContent>
                        </Card>
                    )}
                </Grid>
            </Grid>
        </Box>
    );
};

export default BulkGenerator;