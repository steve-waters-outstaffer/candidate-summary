import React, { useState, useEffect, useCallback } from 'react';
import {
    Box, Card, CardContent, TextField, Button, Typography, Alert, CircularProgress,
    FormControl, InputLabel, Select, MenuItem, FormGroup, FormControlLabel, Switch,
    Stepper, Step, StepLabel, Grid, Paper, Accordion, AccordionSummary, AccordionDetails,
    Divider, List, ListItem, ListItemIcon, ListItemText, Collapse
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import DescriptionIcon from '@mui/icons-material/Description';
import MicIcon from '@mui/icons-material/Mic';
import { debounce } from 'lodash';
import { useAuth } from '../contexts/AuthContext';

// Updated component signature to accept props from Dashboard
const BulkGenerator = ({ jobId, setJobId, jobStatus, setJobStatus }) => {
    const { loginWithGoogle } = useAuth();
    const [jobUrl, setJobUrl] = useState('');
    const [clientName, setClientName] = useState('');
    const [outstafferJobUrl, setOutstafferJobUrl] = useState('');
    const [jobStages, setJobStages] = useState([]);
    const [selectedStage, setSelectedStage] = useState('');
    const [singleCandidatePrompt, setSingleCandidatePrompt] = useState('');
    const [multiCandidatePrompt, setMultiCandidatePrompt] = useState('');
    const [availablePrompts, setAvailablePrompts] = useState({ single: [], multiple: [] });
    const [alert, setAlert] = useState({ show: false, type: 'info', message: '' });
    
    // Email generation state
    const [generateEmail, setGenerateEmail] = useState(false);
    const [creatingDraft, setCreatingDraft] = useState(false);
    const [draftUrl, setDraftUrl] = useState('');

    // Loading States
    const [stagesLoading, setStagesLoading] = useState(false);
    const [candidatesLoading, setCandidatesLoading] = useState(false);
    const [processingLoading, setProcessingLoading] = useState(false);
    const [emailLoading, setEmailLoading] = useState(false);

    // Data & State
    const [candidateList, setCandidateList] = useState([]);
    const [selectedCandidates, setSelectedCandidates] = useState({});
    // Removed local jobId and results state - now using props from Dashboard
    const [jobName, setJobName] = useState('');

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
        setJobId(null); // Using prop function
        setJobName('');
        setJobStatus(null); // Using prop function
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
                const data = await response.json();
                setJobName(data.job_name || '');
                setJobStages(data.stages || []);
                if (!data.stages || data.stages.length === 0) {
                    showAlert('info', 'No candidates found in any active stage for this job.');
                }
            } else {
                const errorData = await response.json();
                showAlert('error', errorData.error || 'Could not fetch candidate stages for this job.');
                setJobName('');
            }
        } catch (error) {
            console.error('Error fetching job stages:', error);
            showAlert('error', 'A network error occurred while fetching job stages.');
            setJobName('');
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
        setJobStatus(null); // Using prop function
        setJobId(null); // Using prop function

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
                setJobId(data.job_id); // Using prop function
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
                    setJobStatus(data); // Using prop function
                    if (data.job_name && !jobName) {
                        setJobName(data.job_name);
                    }
                    if (data.status === 'complete' || data.status === 'failed') {
                        clearInterval(interval);
                        setProcessingLoading(false);
                        if (data.status === 'complete') {
                            showAlert('success', 'All summaries have been processed!');
                        } else {
                            showAlert('error', data.error || 'The bulk processing job failed.');
                        }
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
                    multi_candidate_prompt: multiCandidatePrompt,
                    client_name: clientName,
                    outstaffer_job_url: outstafferJobUrl
                })
            });

            const data = await response.json();
            if (response.ok) {
                setJobStatus(prev => ({ ...prev, email_html: data.email_html })); // Using prop function
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

    // --- Create Gmail Draft ---
    const createGmailDraft = async () => {
        if (!jobStatus?.email_html) {
            showAlert('error', 'No email content available to create draft.');
            return;
        }

        // Check if we have a valid access token
        let accessToken = sessionStorage.getItem('google_access_token');
        
        if (!accessToken) {
            // Need to authenticate with Google first
            try {
                showAlert('info', 'Requesting Gmail permissions...');
                const result = await loginWithGoogle();
                accessToken = result.accessToken;
                
                if (!accessToken) {
                    showAlert('error', 'Failed to get Gmail permissions. Please try again.');
                    return;
                }
            } catch (error) {
                showAlert('error', 'Failed to authenticate with Google: ' + error.message);
                return;
            }
        }

        // Extract job title for subject
        const jobTitle = jobName || 'Position';
        const subject = `Candidate Submissions - ${jobTitle}`;

        setCreatingDraft(true);
        try {
            const response = await fetch(`${API_BASE_URL}/api/create-bulk-gmail-draft`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    access_token: accessToken,
                    subject: subject,
                    html_body: jobStatus.email_html,
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

    // --- Step 5: Send to RecruitCRM ---
    const handleSendToRecruitCRM = async (candidateSlug) => {
        showAlert('info', `Sending ${getCandidateName(candidateSlug)} to RecruitCRM...`);
    };

    const handleSendAllToRecruitCRM = async () => {
        showAlert('info', 'Sending all successful summaries to RecruitCRM...');
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

                        {jobName && (
                            <Typography variant="h6" sx={{ color: 'success.main', mb: 2, fontWeight: 'medium' }}>
                                Job: {jobName}
                            </Typography>
                        )}

                        <FormControl fullWidth sx={{ mb: 2 }}>
                            <InputLabel id="stage-label">Hiring Stage</InputLabel>
                            <Select labelId="stage-label" value={selectedStage} onChange={(e) => handleStageChange(e.target.value)} label="Hiring Stage" disabled={stagesLoading || processingLoading}
                                    startAdornment={stagesLoading && <CircularProgress size={20} sx={{ mr: 1 }} />}>
                                {jobStages.map((stage) => (
                                    <MenuItem key={stage.status_id} value={stage.status_id}>
                                        {`${stage.label} `}
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>

                        {candidatesLoading && <CircularProgress />}

                        {candidateList.length > 0 && (
                            <>
                                <Typography variant="subtitle1" sx={{mb: 1}}>Candidates to process</Typography>
                                <Paper variant="outlined" sx={{ maxHeight: 300, overflow: 'auto', mb: 2 }}>
                                    <List dense>
                                        {candidateList.map((cand) => (
                                            <ListItem key={cand.slug} secondaryAction={<Switch edge="end" checked={selectedCandidates[cand.slug] || false} onChange={() => handleCandidateToggle(cand.slug)} disabled={processingLoading}/>} disablePadding>
                                                <ListItemText primary={cand.name} sx={{ pl: 2 }}/>
                                            </ListItem>
                                        ))}
                                    </List>
                                </Paper>
                            </>
                        )}

                        <Divider sx={{ my: 2 }} />
                        <Typography variant="subtitle1" sx={{mb: 1, fontWeight: 'bold'}}>Individual Summary Prompt</Typography>
                        <FormControl fullWidth sx={{ mb: 2 }}>
                            <InputLabel>Summary Prompt</InputLabel>
                            <Select value={singleCandidatePrompt} onChange={(e) => setSingleCandidatePrompt(e.target.value)} label="Summary Prompt" disabled={processingLoading}>
                                {availablePrompts.single.map((p) => <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}
                            </Select>
                        </FormControl>

                        <Divider sx={{ my: 2 }} />
                        
                        <FormControlLabel 
                            control={<Switch checked={generateEmail} onChange={(e) => setGenerateEmail(e.target.checked)} name="generateEmail" />} 
                            label="Generate Email" 
                            sx={{ mb: 1 }} 
                        />
                        
                        <Collapse in={generateEmail}>
                            <Box sx={{ mt: 2 }}>
                                <Typography variant="subtitle1" sx={{mb: 1, fontWeight: 'bold'}}>Email Customization</Typography>
                                <TextField label="Client Name" value={clientName} onChange={(e) => setClientName(e.target.value)} fullWidth sx={{ mb: 2 }} disabled={processingLoading} />
                                <TextField label="Outstaffer Platform Job URL" value={outstafferJobUrl} onChange={(e) => setOutstafferJobUrl(e.target.value)} fullWidth sx={{ mb: 2 }} disabled={processingLoading} />
                                
                                <FormControl fullWidth sx={{ mb: 2 }}>
                                    <InputLabel>Multi-Candidate Email Prompt</InputLabel>
                                    <Select value={multiCandidatePrompt} onChange={(e) => setMultiCandidatePrompt(e.target.value)} label="Multi-Candidate Email Prompt" disabled={processingLoading}>
                                        {availablePrompts.multiple.map((p) => <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}
                                    </Select>
                                </FormControl>
                            </Box>
                        </Collapse>

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

                        {!jobStatus && !processingLoading && <Typography color="text.secondary">Results will appear here once processing starts.</Typography>}

                        {processingLoading && !jobStatus && <CircularProgress />}

                        {jobStatus && (
                            <Box>
                                {jobName && <Typography variant="h6" gutterBottom>Job: <span style={{ color: 'green' }}>{jobName}</span></Typography>}
                                <Typography variant="h6" gutterBottom>Status: {jobStatus.status} ({jobStatus.processed_count + jobStatus.failed_count} / {jobStatus.total_candidates} complete)</Typography>
                                <Divider sx={{ my: 2 }} />

                                {jobStatus.status === 'complete' && (
                                    <Box sx={{display: 'flex', gap: 2, mb: 2}}>
                                        {generateEmail && !jobStatus.email_html && (
                                            <Button variant="contained" color="secondary" onClick={handleGenerateEmail} disabled={emailLoading} fullWidth>
                                                {emailLoading ? <CircularProgress size={24} /> : 'Generate Final Email'}
                                            </Button>
                                        )}
                                        <Button variant="outlined" color="success" onClick={handleSendAllToRecruitCRM} fullWidth>
                                            Send All to RecruitCRM
                                        </Button>
                                    </Box>
                                )}

                                {jobStatus.email_html && (
                                    <>
                                        <Accordion defaultExpanded>
                                            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                                                <Typography variant="h6">Generated Email</Typography>
                                            </AccordionSummary>
                                            <AccordionDetails>
                                                <Paper elevation={0} variant="outlined" sx={{ p: 2, maxHeight: 400, overflow: 'auto', mb: 2 }}>
                                                    <Box dangerouslySetInnerHTML={{ __html: jobStatus.email_html }} />
                                                </Paper>
                                                <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
                                                    <Button 
                                                        variant="contained" 
                                                        color="primary" 
                                                        onClick={createGmailDraft} 
                                                        disabled={creatingDraft}
                                                        fullWidth
                                                    >
                                                        {creatingDraft ? <CircularProgress size={24} /> : 'Create Draft in Gmail'}
                                                    </Button>
                                                    {draftUrl && (
                                                        <Button 
                                                            variant="outlined" 
                                                            color="primary" 
                                                            href={draftUrl} 
                                                            target="_blank"
                                                            fullWidth
                                                        >
                                                            Open Draft
                                                        </Button>
                                                    )}
                                                </Box>
                                            </AccordionDetails>
                                        </Accordion>
                                    </>
                                )}

                                <Divider sx={{ my: 2 }} />
                                <Typography variant="h6" sx={{ mt: 2, mb: 1 }}>Individual Summaries</Typography>
                                {Object.entries(jobStatus.results || {}).map(([slug, result]) => (
                                    <Accordion key={slug}>
                                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                                            <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                                                {result.status === 'success' && <CheckCircleIcon color="success" sx={{ mr: 1 }}/>}
                                                {result.status === 'failed' && <ErrorIcon color="error" sx={{ mr: 1 }}/>}
                                                {result.status === 'pending' && <CircularProgress size={20} sx={{ mr: 1 }}/>}
                                                <Typography sx={{ fontWeight: 'bold', flexShrink: 0 }}>{getCandidateName(slug)}</Typography>
                                                <Typography sx={{ ml: 1, color: 'text.secondary' }}>- {result.status}</Typography>
                                                <Box sx={{ flexGrow: 1 }} />
                                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mr: 2, flexShrink: 0 }}>
                                                    {result.has_cv && <DescriptionIcon color="action" titleAccess="CV Found"/>}
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