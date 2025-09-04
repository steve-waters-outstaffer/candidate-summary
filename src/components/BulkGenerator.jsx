import React, { useState, useEffect, useCallback } from 'react';
import {
    Box, Card, CardContent, TextField, Button, Typography, Alert, CircularProgress,
    FormControl, InputLabel, Select, MenuItem, FormGroup, FormControlLabel, Switch,
    Stepper, Step, StepLabel, Grid, Paper, Accordion, AccordionSummary, AccordionDetails,
    Divider, List, ListItem, ListItemIcon, ListItemText
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import DescriptionIcon from '@mui/icons-material/Description';
import MicIcon from '@mui/icons-material/Mic';
import { debounce } from 'lodash';
import { CustomColors } from '../theme';

// --- UPDATE THE COMPONENT SIGNATURE to accept props ---
const BulkGenerator = ({ jobId, setJobId, jobStatus, setJobStatus }) => {
    // This local state is specific to this component's UI and remains here
    const [jobUrl, setJobUrl] = useState('');
    const [clientName, setClientName] = useState('');
    const [outstafferJobUrl, setOutstafferJobUrl] = useState('');
    const [jobStages, setJobStages] = useState([]);
    const [selectedStage, setSelectedStage] = useState('');
    const [singleCandidatePrompt, setSingleCandidatePrompt] = useState('');
    const [multiCandidatePrompt, setMultiCandidatePrompt] = useState('');
    const [availablePrompts, setAvailablePrompts] = useState({ single: [], multiple: [] });
    const [alert, setAlert] = useState({ show: false, type: 'info', message: '' });

    // Loading States
    const [isLoadingStages, setIsLoadingStages] = useState(false);
    const [isLoadingCandidates, setIsLoadingCandidates] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);
    const [isGeneratingEmail, setIsGeneratingEmail] = useState(false);
    const [candidates, setCandidates] = useState([]);
    const [selectedCandidates, setSelectedCandidates] = useState({});

    // --- REMOVE THE LOCAL STATE now managed by the Dashboard parent ---
    // const [jobId, setJobId] = useState(null);
    // const [jobStatus, setJobStatus] = useState(null);

    const resetAlert = () => setAlert({ show: false, type: 'info', message: '' });

    const debouncedFetchJobStages = useCallback(debounce(async (url) => {
        if (!url) return;
        resetAlert();
        setIsLoadingStages(true);
        const slug = url.split('/').pop();
        try {
            const response = await fetch(`${import.meta.env.VITE_API_URL}/api/job-stages-with-counts/${slug}`);
            const data = await response.json();
            if (response.ok) {
                setJobStages(data.stages);
            } else {
                setAlert({ show: true, type: 'error', message: data.error || 'Failed to fetch job stages.' });
                setJobStages([]);
            }
        } catch (error) {
            setAlert({ show: true, type: 'error', message: 'Error connecting to the server.' });
            setJobStages([]);
        }
        setIsLoadingStages(false);
    }, 500), []);

    const handleJobUrlChange = (event) => {
        const url = event.target.value;
        setJobUrl(url);
        debouncedFetchJobStages(url);
    };

    useEffect(() => {
        const fetchPrompts = async () => {
            try {
                const [singleRes, multiRes] = await Promise.all([
                    fetch(`${import.meta.env.VITE_API_URL}/api/prompts?category=single`),
                    fetch(`${import.meta.env.VITE_API_URL}/api/prompts?category=multiple`),
                ]);

                // --- NEW DEBUGGING STEP ---
                // Log the raw text from the responses to see what the server is actually sending.
                const singleText = await singleRes.text();
                const multiText = await multiRes.text();

                // Check if the response text looks like JSON before parsing
                if (!singleText.startsWith('{') && !singleText.startsWith('[')) {
                    console.error("The 'single' prompt response from the server was not JSON. It was:", singleText);
                    throw new Error("Server returned an invalid response for single prompts.");
                }
                if (!multiText.startsWith('{') && !multiText.startsWith('[')) {
                    console.error("The 'multiple' prompt response from the server was not JSON. It was:", multiText);
                    throw new Error("Server returned an invalid response for multiple prompts.");
                }
                // --- END DEBUGGING STEP ---

                // Now we parse the text we already fetched
                const singleData = JSON.parse(singleText);
                const multiData = JSON.parse(multiText);

                setAvailablePrompts({ single: singleData, multiple: multiData });

            } catch (error) {
                console.error("Failed to fetch prompts:", error);
                setAlert({ show: true, type: 'error', message: 'Could not load AI prompts from the server. Check the console for details.' });
            }
        };
        fetchPrompts();
    }, []);

    const handleStageChange = async (event) => {
        const stageId = event.target.value;
        setSelectedStage(stageId);
        if (stageId) {
            setIsLoadingCandidates(true);
            const jobSlug = jobUrl.split('/').pop();
            try {
                const response = await fetch(`${import.meta.env.VITE_API_URL}/api/candidates-in-stage/${jobSlug}/${stageId}`);
                const data = await response.json();
                if (response.ok) {
                    setCandidates(data);
                    const initialSelection = data.reduce((acc, cand) => ({ ...acc, [cand.slug]: true }), {});
                    setSelectedCandidates(initialSelection);
                } else {
                    setAlert({ show: true, type: 'error', message: data.error || 'Failed to fetch candidates.' });
                }
            } catch (error) {
                setAlert({ show: true, type: 'error', message: 'Error fetching candidates.' });
            }
            setIsLoadingCandidates(false);
        } else {
            setCandidates([]);
        }
    };

    useEffect(() => {
        let interval;
        if (jobId && jobStatus?.status === 'processing') {
            const fetchJobStatus = async (id) => {
                try {
                    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/bulk-job-status/${id}`);
                    if (!response.ok) throw new Error('Network response was not ok');
                    const data = await response.json();
                    setJobStatus(data);
                    if (data.status === 'complete' || data.status === 'failed') {
                        setIsProcessing(false);
                    }
                } catch (error) {
                    console.error("Error fetching job status:", error);
                    setAlert({ show: true, type: 'error', message: 'Polling failed. Check connection.' });
                    setIsProcessing(false);
                }
            };
            interval = setInterval(() => fetchJobStatus(jobId), 5000);
        }
        return () => clearInterval(interval);
    }, [jobId, jobStatus?.status, setJobStatus]);

    const handleCandidateSelectionChange = (event) => {
        setSelectedCandidates({
            ...selectedCandidates,
            [event.target.name]: event.target.checked,
        });
    };

    const handleStartProcessing = async () => {
        resetAlert();
        setIsProcessing(true);
        const selectedSlugs = Object.keys(selectedCandidates).filter(slug => selectedCandidates[slug]);

        try {
            const response = await fetch(`${import.meta.env.VITE_API_URL}/api/bulk-process-job`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    job_url: jobUrl,
                    single_candidate_prompt: singleCandidatePrompt,
                    candidate_slugs: selectedSlugs,
                }),
            });
            const data = await response.json();
            if (response.ok) {
                setJobId(data.job_id); // This now calls the function from Dashboard
                setJobStatus({ status: 'processing', results: {} }); // Initial status
                setAlert({ show: true, type: 'success', message: 'Bulk processing job started.' });
            } else {
                setAlert({ show: true, type: 'error', message: data.error || 'Failed to start job.' });
                setIsProcessing(false);
            }
        } catch (error) {
            setAlert({ show: true, type: 'error', message: 'Failed to connect to the server.' });
            setIsProcessing(false);
        }
    };

    const handleGenerateEmail = async () => {
        setIsGeneratingEmail(true);
        try {
            const response = await fetch(`${import.meta.env.VITE_API_URL}/api/generate-bulk-email`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    job_id: jobId,
                    multi_candidate_prompt: multiCandidatePrompt,
                    client_name: clientName,
                    outstaffer_job_url: outstafferJobUrl,
                }),
            });
            const data = await response.json();
            if (response.ok) {
                setJobStatus(prev => ({ ...prev, email_html: data.email_html }));
                setAlert({ show: true, type: 'success', message: 'Email content generated.' });
            } else {
                setAlert({ show: true, type: 'error', message: data.error || 'Failed to generate email.' });
            }
        } catch (error) {
            setAlert({ show: true, type: 'error', message: 'Error generating email.' });
        }
        setIsGeneratingEmail(false);
    };

    const handleSendToRecruitCRM = async (slug) => {
        const summary = jobStatus?.results?.[slug]?.summary;
        if (!summary) {
            setAlert({ show: true, type: 'error', message: 'Could not find summary for this candidate.' });
            return;
        }
        try {
            const response = await fetch(`${import.meta.env.VITE_API_URL}/api/push-to-recruitcrm`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    candidate_slug: slug,
                    html_summary: summary,
                }),
            });
            const data = await response.json();
            if (response.ok) {
                setAlert({ show: true, type: 'success', message: 'Summary successfully pushed to RecruitCRM.' });
            } else {
                setAlert({ show: true, type: 'error', message: data.error || 'Failed to push summary.' });
            }
        } catch (error) {
            setAlert({ show: true, type: 'error', message: 'Server error while pushing summary.' });
        }
    };

    const activeStep = jobId ? (jobStatus?.status === 'complete' ? 2 : 1) : 0;
    const allCandidatesCount = candidates.length;
    const selectedCandidatesCount = Object.values(selectedCandidates).filter(Boolean).length;

    return (
        <Grid container spacing={3}>
            <Grid item xs={12}>
                <Stepper activeStep={activeStep}>
                    <Step><StepLabel>Setup</StepLabel></Step>
                    <Step><StepLabel>Process Candidates</StepLabel></Step>
                    <Step><StepLabel>Generate Email</StepLabel></Step>
                </Stepper>
            </Grid>

            {alert.show && (
                <Grid item xs={12}>
                    <Alert severity={alert.type} onClose={() => setAlert({ show: false })}>{alert.message}</Alert>
                </Grid>
            )}

            <Grid item xs={12} md={4}>
                <Card>
                    <CardContent>
                        <Typography variant="h6" gutterBottom>1. Job & Stage Selection</Typography>
                        <TextField
                            label="RecruitCRM Job URL"
                            fullWidth
                            margin="normal"
                            onChange={handleJobUrlChange}
                            disabled={isProcessing}
                            InputProps={{
                                endAdornment: isLoadingStages && <CircularProgress size={20} />,
                            }}
                        />
                        {jobStages.length > 0 && (
                            <FormControl fullWidth margin="normal" disabled={isProcessing}>
                                <InputLabel>Hiring Stage</InputLabel>
                                <Select value={selectedStage} label="Hiring Stage" onChange={handleStageChange}>
                                    {jobStages.map(stage => (
                                        <MenuItem key={stage.status_id} value={stage.status_id}>
                                            {stage.name} ({stage.candidate_count})
                                        </MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                        )}
                    </CardContent>
                </Card>
                <Card sx={{ mt: 3 }}>
                    <CardContent>
                        <Typography variant="h6" gutterBottom>2. AI Configuration</Typography>
                        <FormControl fullWidth margin="normal" disabled={isProcessing}>
                            <InputLabel>Summary Prompt</InputLabel>
                            <Select value={singleCandidatePrompt} label="Summary Prompt" onChange={(e) => setSingleCandidatePrompt(e.target.value)}>
                                {availablePrompts.single.map(p => <MenuItem key={p.key} value={p.key}>{p.name}</MenuItem>)}
                            </Select>
                        </FormControl>
                        <FormControl fullWidth margin="normal" disabled={jobStatus?.status !== 'complete'}>
                            <InputLabel>Client Email Prompt</InputLabel>
                            <Select value={multiCandidatePrompt} label="Client Email Prompt" onChange={(e) => setMultiCandidatePrompt(e.target.value)}>
                                {availablePrompts.multiple.map(p => <MenuItem key={p.key} value={p.key}>{p.name}</MenuItem>)}
                            </Select>
                        </FormControl>
                        <TextField
                            label="Client Name"
                            fullWidth
                            margin="normal"
                            value={clientName}
                            onChange={(e) => setClientName(e.target.value)}
                            disabled={jobStatus?.status !== 'complete'}
                        />
                        <TextField
                            label="Outstaffer Job URL (for email)"
                            fullWidth
                            margin="normal"
                            value={outstafferJobUrl}
                            onChange={(e) => setOutstafferJobUrl(e.target.value)}
                            disabled={jobStatus?.status !== 'complete'}
                        />
                    </CardContent>
                </Card>
            </Grid>

            <Grid item xs={12} md={8}>
                <Card>
                    <CardContent>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <Typography variant="h6">3. Candidate Processing</Typography>
                            {candidates.length > 0 && (
                                <Button
                                    variant="contained"
                                    onClick={handleStartProcessing}
                                    disabled={!selectedStage || selectedCandidatesCount === 0 || isProcessing || jobId}
                                >
                                    {isProcessing ? <CircularProgress size={24} /> : `Process ${selectedCandidatesCount} Candidates`}
                                </Button>
                            )}
                        </Box>

                        {isLoadingCandidates && <CircularProgress sx={{ mt: 2 }}/>}

                        {!jobId && candidates.length > 0 && (
                            <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
                                <Typography variant="subtitle2" gutterBottom>
                                    {selectedCandidatesCount} of {allCandidatesCount} candidates selected
                                </Typography>
                                <FormGroup>
                                    {candidates.map(candidate => (
                                        <FormControlLabel
                                            key={candidate.slug}
                                            control={<Switch checked={!!selectedCandidates[candidate.slug]} onChange={handleCandidateSelectionChange} name={candidate.slug} />}
                                            label={candidate.name}
                                        />
                                    ))}
                                </FormGroup>
                            </Paper>
                        )}

                        {jobStatus && (
                            <Box sx={{ mt: 2 }}>
                                <Typography>
                                    Status: {jobStatus.status} ({jobStatus.processed_count || 0} / {jobStatus.total_candidates || 0})
                                </Typography>
                                {isProcessing && <CircularProgress sx={{ my: 2 }} />}

                                {jobStatus.status === 'complete' && !jobStatus.email_html && (
                                    <Button
                                        variant="contained"
                                        color="secondary"
                                        onClick={handleGenerateEmail}
                                        disabled={isGeneratingEmail}
                                        sx={{ mt: 2 }}
                                    >
                                        {isGeneratingEmail ? <CircularProgress size={24} /> : "Generate Client Email"}
                                    </Button>
                                )}

                                {jobStatus.email_html && (
                                    <Card variant="outlined" sx={{ mt: 2 }}>
                                        <CardContent>
                                            <Typography variant="h6" gutterBottom>Generated Email</Typography>
                                            <Box sx={{ border: 1, borderColor: 'grey.300', p: 2, maxHeight: 400, overflow: 'auto' }}
                                                 dangerouslySetInnerHTML={{ __html: jobStatus.email_html }} />
                                        </CardContent>
                                    </Card>
                                )}

                                <Divider sx={{ my: 2 }}>Results</Divider>

                                {Object.entries(jobStatus.results || {}).map(([slug, result]) => (
                                    <Accordion key={slug}>
                                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                                            <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                                                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                                    {result.status === 'success' ? <CheckCircleIcon color="success" sx={{ mr: 1 }} /> : <ErrorIcon color="error" sx={{ mr: 1 }} />}
                                                    <Typography>{candidates.find(c => c.slug === slug)?.name || slug}</Typography>
                                                </Box>
                                                <Box>
                                                    {result.has_cv && <DescriptionIcon color="action" titleAccess="CV Found" />}
                                                    {result.has_ai_interview && <MicIcon color="action" titleAccess="AI Interview Found" />}
                                                </Box>
                                            </Box>
                                        </AccordionSummary>
                                        <AccordionDetails>
                                            {result.status === 'success' && (
                                                <Box>
                                                    <Box dangerouslySetInnerHTML={{ __html: result.summary }} />
                                                    <Button variant="outlined" color="primary" size="small" onClick={() => handleSendToRecruitCRM(slug)} sx={{ mt: 2 }}>
                                                        Send to RecruitCRM
                                                    </Button>
                                                </Box>
                                            )}
                                            {result.status === 'failed' && <Alert severity="error">{result.error}</Alert>}
                                        </AccordionDetails>
                                    </Accordion>
                                ))}
                            </Box>
                        )}
                    </CardContent>
                </Card>
            </Grid>
        </Grid>
    );
};

export default BulkGenerator;