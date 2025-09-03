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
import { debounce } from 'lodash';

const BulkGenerator = () => {
    const [jobUrl, setJobUrl] = useState('');
    const [jobStages, setJobStages] = useState([]);
    const [selectedStage, setSelectedStage] = useState('');
    const [singleCandidatePrompt, setSingleCandidatePrompt] = useState('');
    const [multiCandidatePrompt, setMultiCandidatePrompt] = useState('');
    const [availablePrompts, setAvailablePrompts] = useState({ single: [], multiple: [] });
    const [alert, setAlert] = useState({ show: false, type: 'info', message: '' });

    // Loading States
    const [stagesLoading, setStagesLoading] = useState(false);
    const [candidatesLoading, setCandidatesLoading] = useState(false);
    const [processingLoading, setProcessingLoading] = useState(false);
    const [emailLoading, setEmailLoading] = useState(false);

    // Data & State
    const [candidateList, setCandidateList] = useState([]);
    const [selectedCandidates, setSelectedCandidates] = useState({});
    const [jobId, setJobId] = useState(null);
    const [results, setResults] = useState(null);


    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

    // Fetch available prompts on component mount
    useEffect(() => {
        const fetchPrompts = async (category) => {
            if (!API_BASE_URL) return;
            try {
                const response = await fetch(`${API_BASE_URL}/api/prompts?category=${category}`);
                if (response.ok) {
                    const prompts = await response.json();
                    setAvailablePrompts(prev => ({ ...prev, [category]: prompts }));
                    if (prompts.length > 0) {
                        if (category === 'single') setSingleCandidatePrompt(prompts[0].id);
                        if (category === 'multiple') setMultiCandidatePrompt(prompts[0].id);
                    }
                }
            } catch (error) {
                console.error(`Error fetching ${category} prompts:`, error);
            }
        };
        fetchPrompts('single');
        fetchPrompts('multiple');
    }, []);

    const showAlert = (type, message) => {
        setAlert({ show: true, type, message });
    };

    const resetState = () => {
        setJobStages([]);
        setSelectedStage('');
        setCandidateList([]);
        setSelectedCandidates({});
        setJobId(null);
        setResults(null);
    };

    // --- Step 1: Fetch Job Stages ---
    const fetchJobStages = async (url) => {
        const slugMatch = url.match(/\/job(?:s)?\/([a-zA-Z0-9]+)/);
        if (!slugMatch || !slugMatch[1]) {
            resetState();
            return;
        }
        const jobSlug = slugMatch[1];
        setStagesLoading(true);
        try {
            const response = await fetch(`${API_BASE_URL}/api/job-stages-with-counts/${jobSlug}`);
            if (response.ok) {
                const stages = await response.json();
                setJobStages(stages);
                if (stages.length === 0) {
                    showAlert('info', 'No candidates found in any active stage for this job.');
                }
            } else {
                showAlert('error', 'Could not fetch candidate stages for this job.');
            }
        } catch (error) {
            console.error('Error fetching job stages:', error);
        } finally {
            setStagesLoading(false);
        }
    };

    const debouncedFetchJobStages = useCallback(debounce(fetchJobStages, 500), []);

    const handleJobUrlChange = (e) => {
        const url = e.target.value;
        setJobUrl(url);
        resetState();
        debouncedFetchJobStages(url);
    };


    // --- Step 2: Fetch Candidates in Selected Stage ---
    const handleStageChange = async (stageId) => {
        setSelectedStage(stageId);
        if (!stageId) {
            setCandidateList([]);
            return;
        }
        setCandidatesLoading(true);
        const jobSlug = jobUrl.match(/\/job(?:s)?\/([a-zA-Z0-9]+)/)[1];
        try {
            const response = await fetch(`${API_BASE_URL}/api/candidates-in-stage/${jobSlug}/${stageId}`);
            if (response.ok) {
                const candidates = await response.json();
                setCandidateList(candidates);
                const initialSelection = candidates.reduce((acc, cand) => {
                    acc[cand.slug] = true; // Select all by default
                    return acc;
                }, {});
                setSelectedCandidates(initialSelection);
            }
        } catch (error) {
            console.error('Error fetching candidates:', error);
            showAlert('error', 'Could not fetch the list of candidates.');
        } finally {
            setCandidatesLoading(false);
        }
    };

    const handleCandidateToggle = (slug) => {
        setSelectedCandidates(prev => ({ ...prev, [slug]: !prev[slug] }));
    };


    // --- Step 3: Start Bulk Processing ---
    const handleBulkProcess = async () => {
        const slugsToProcess = Object.keys(selectedCandidates).filter(slug => selectedCandidates[slug]);
        if (slugsToProcess.length === 0) {
            showAlert('error', 'Please select at least one candidate.');
            return;
        }

        setProcessingLoading(true);
        setAlert({ show: false });
        setResults(null);
        setJobId(null);

        try {
            const response = await fetch(`${API_BASE_URL}/api/bulk-process-job`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    job_url: jobUrl,
                    single_candidate_prompt: singleCandidatePrompt,
                    candidate_slugs: slugsToProcess
                })
            });
            const data = await response.json();
            if (response.status === 202) {
                setJobId(data.job_id);
                pollJobStatus(data.job_id);
            } else {
                showAlert('error', data.error || 'Failed to start bulk process.');
                setProcessingLoading(false);
            }
        } catch (error) {
            showAlert('error', 'A network error occurred while starting the process.');
            setProcessingLoading(false);
        }
    };

    const pollJobStatus = (id) => {
        const interval = setInterval(async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/api/bulk-job-status/${id}`);
                const data = await response.json();

                if (response.ok) {
                    setResults(data);
                    if (data.status === 'complete') {
                        clearInterval(interval);
                        setProcessingLoading(false);
                        showAlert('success', 'All summaries have been processed!');
                    }
                } else {
                    clearInterval(interval);
                    setProcessingLoading(false);
                    showAlert('error', 'Error fetching job status.');
                }
            } catch (error) {
                clearInterval(interval);
                setProcessingLoading(false);
                showAlert('error', 'A network error occurred while polling for status.');
            }
        }, 5000); // Poll every 5 seconds
    };

    // --- Step 4: Generate Final Email ---
    const handleGenerateEmail = async () => {
        if (!jobId || !multiCandidatePrompt) {
            showAlert('error', 'Job ID or email prompt is missing.');
            return;
        }

        setEmailLoading(true);
        try {
            const response = await fetch(`${API_BASE_URL}/api/generate-bulk-email`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    job_id: jobId,
                    multi_candidate_prompt: multiCandidatePrompt
                })
            });

            const data = await response.json();
            if (response.ok) {
                setResults(prev => ({ ...prev, email_html: data.email_html }));
                showAlert('success', 'Email generated successfully!');
            } else {
                showAlert('error', data.error || 'Failed to generate email.');
            }
        } catch (error) {
            showAlert('error', 'A network error occurred while generating the email.');
        } finally {
            setEmailLoading(false);
        }
    };


    const getCandidateName = (slug) => {
        const candidate = candidateList.find(c => c.slug === slug);
        return candidate ? candidate.name : slug;
    }

    const totalSelected = Object.values(selectedCandidates).filter(Boolean).length;


    return (
        <Grid container spacing={3}>
            {/* --- Left Column: Setup --- */}
            <Grid item xs={12} md={5}>
                <Card>
                    <CardContent>
                        <Typography variant="h4" sx={{ mb: 2 }}>Bulk Process Job</Typography>

                        <TextField label="RecruitCRM Job URL" value={jobUrl} onChange={handleJobUrlChange} fullWidth sx={{ mb: 2 }} placeholder="Paste a job URL to begin..." disabled={processingLoading} />

                        <FormControl fullWidth sx={{ mb: 2 }}>
                            <InputLabel id="stage-label">Hiring Stage</InputLabel>
                            <Select labelId="stage-label" value={selectedStage} onChange={(e) => handleStageChange(e.target.value)} label="Hiring Stage" disabled={stagesLoading || jobStages.length === 0 || processingLoading}
                                    startAdornment={stagesLoading && <CircularProgress size={20} sx={{ mr: 1 }} />}>
                                {jobStages.map((stage) => (
                                    <MenuItem key={stage.status_id} value={stage.status_id}>
                                        {`${stage.label} (${stage.candidate_count})`}
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                        {candidatesLoading && <CircularProgress />}
                        {candidateList.length > 0 && (
                            <Paper variant="outlined" sx={{ maxHeight: 300, overflow: 'auto', mb: 2 }}>
                                <List dense>
                                    {candidateList.map((cand) => (
                                        <ListItem key={cand.slug} secondaryAction={<Switch edge="end" checked={selectedCandidates[cand.slug] || false} onChange={() => handleCandidateToggle(cand.slug)} disabled={processingLoading}/>} disablePadding>
                                            <ListItemText primary={cand.name} sx={{ pl: 2 }}/>
                                        </ListItem>
                                    ))}
                                </List>
                            </Paper>
                        )}

                        <FormControl fullWidth sx={{ mb: 2 }}>
                            <InputLabel>Individual Summary Prompt</InputLabel>
                            <Select value={singleCandidatePrompt} onChange={(e) => setSingleCandidatePrompt(e.target.value)} label="Individual Summary Prompt" disabled={processingLoading}>
                                {availablePrompts.single.map((p) => <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}
                            </Select>
                        </FormControl>

                        <FormControl fullWidth sx={{ mb: 2 }}>
                            <InputLabel>Multi-Candidate Email Prompt</InputLabel>
                            <Select value={multiCandidatePrompt} onChange={(e) => setMultiCandidatePrompt(e.target.value)} label="Multi-Candidate Email Prompt" disabled={processingLoading}>
                                {availablePrompts.multiple.map((p) => <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}
                            </Select>
                        </FormControl>

                        <Button variant="contained" color="primary" onClick={handleBulkProcess} disabled={processingLoading || totalSelected === 0} fullWidth sx={{ mt: 2 }}>
                            {processingLoading ? <CircularProgress size={24} /> : `Process ${totalSelected} Candidates`}
                        </Button>
                    </CardContent>
                </Card>
            </Grid>

            {/* --- Right Column: Progress & Results --- */}
            <Grid item xs={12} md={7}>
                <Card>
                    <CardContent>
                        <Typography variant="h4" sx={{ mb: 2 }}>Progress & Results</Typography>
                        {alert.show && <Alert severity={alert.type} sx={{ mb: 2 }} onClose={() => setAlert({ show: false })}>{alert.message}</Alert>}

                        {!results && !processingLoading && <Typography color="text.secondary">Results will appear here once processing starts.</Typography>}

                        {results && (
                            <Box>
                                <Typography variant="h6" gutterBottom>
                                    Job Status: {results.status} ({results.processed_count + results.failed_count} / {results.total_candidates} complete)
                                </Typography>
                                <Divider sx={{ my: 2 }} />

                                {results.status === 'complete' && !results.email_html && (
                                    <Button variant="contained" color="secondary" onClick={handleGenerateEmail} disabled={emailLoading} fullWidth sx={{ mb: 2 }}>
                                        {emailLoading ? <CircularProgress size={24} /> : 'Generate Final Email'}
                                    </Button>
                                )}

                                {results.email_html && (
                                    <Accordion defaultExpanded>
                                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                                            <Typography variant="h6">Generated Email</Typography>
                                        </AccordionSummary>
                                        <AccordionDetails>
                                            <Paper elevation={0} variant="outlined" sx={{ p: 2, maxHeight: 400, overflow: 'auto' }}>
                                                <Box dangerouslySetInnerHTML={{ __html: results.email_html }} />
                                            </Paper>
                                        </AccordionDetails>
                                    </Accordion>
                                )}

                                <Typography variant="h6" sx={{ mt: 2, mb: 1 }}>Individual Summaries</Typography>
                                {Object.entries(results.results).map(([slug, result]) => (
                                    <Accordion key={slug}>
                                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                                            {result.status === 'success' && <CheckCircleIcon color="success" sx={{ mr: 1 }}/>}
                                            {result.status === 'failed' && <ErrorIcon color="error" sx={{ mr: 1 }}/>}
                                            {result.status === 'pending' && <CircularProgress size={20} sx={{ mr: 1 }}/>}
                                            <Typography sx={{ fontWeight: 'bold' }}>{getCandidateName(slug)}</Typography>
                                            <Typography sx={{ ml: 1, color: 'text.secondary' }}>- {result.status}</Typography>
                                        </AccordionSummary>
                                        <AccordionDetails>
                                            {result.status === 'success' && <Box dangerouslySetInnerHTML={{ __html: result.summary }} />}
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