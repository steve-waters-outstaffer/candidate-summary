import React, { useState, useEffect, useCallback } from 'react';
import {
    Box,
    Card,
    CardContent,
    TextField,
    Button,
    Typography,
    Alert,
    CircularProgress,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    FormGroup,
    FormControlLabel,
    Switch,
    Stepper,
    Step,
    StepLabel,
    Grid,
    Paper,
    Accordion,
    AccordionSummary,
    AccordionDetails,
    Divider
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { debounce } from 'lodash';

const BulkGenerator = () => {
    const [jobUrl, setJobUrl] = useState('');
    const [jobStages, setJobStages] = useState([]);
    const [selectedStage, setSelectedStage] = useState('');
    const [singleCandidatePrompt, setSingleCandidatePrompt] = useState('');
    const [multiCandidatePrompt, setMultiCandidatePrompt] = useState('');
    const [generateEmail, setGenerateEmail] = useState(true);
    const [autoPush, setAutoPush] = useState(false);
    const [loading, setLoading] = useState(false);
    const [stagesLoading, setStagesLoading] = useState(false);
    const [alert, setAlert] = useState({ show: false, type: 'info', message: '' });
    const [availablePrompts, setAvailablePrompts] = useState({ single: [], multiple: [] });
    const [activeStep, setActiveStep] = useState(-1);
    const [results, setResults] = useState(null);

    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

    useEffect(() => {
        fetchAvailablePrompts('single');
        fetchAvailablePrompts('multiple');
    }, []);

    const fetchJobStagesWithCounts = async (url) => {
        // Regex to extract slug from various RecruitCRM job URL formats
        const slugMatch = url.match(/\/job(?:s)?\/([a-zA-Z0-9]+)/);
        if (!slugMatch || !slugMatch[1]) {
            setJobStages([]);
            setSelectedStage('');
            return;
        }
        const jobSlug = slugMatch[1];

        setStagesLoading(true);
        try {
            const response = await fetch(`${API_BASE_URL}/api/job-stages-with-counts/${jobSlug}`);
            if (response.ok) {
                const stages = await response.json();
                setJobStages(stages);
                if (stages.length > 0) {
                    setSelectedStage(stages[0].status_id);
                } else {
                    showAlert('info', 'No candidates found in any active stage for this job.');
                    setSelectedStage('');
                }
            } else {
                setJobStages([]);
                setSelectedStage('');
                showAlert('error', 'Could not fetch candidate stages for this job.');
            }
        } catch (error) {
            console.error('Error fetching job stages:', error);
            setJobStages([]);
            setSelectedStage('');
        } finally {
            setStagesLoading(false);
        }
    };

    // Debounce the fetch function to avoid excessive API calls while typing
    const debouncedFetchJobStages = useCallback(debounce(fetchJobStagesWithCounts, 500), []);

    const handleJobUrlChange = (e) => {
        const url = e.target.value;
        setJobUrl(url);
        debouncedFetchJobStages(url);
    };

    const fetchAvailablePrompts = async (category) => {
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

    const handleBulkProcess = async () => {
        if (!jobUrl.trim() || !selectedStage) {
            showAlert('error', 'Please provide a Job URL and select a stage.');
            return;
        }

        setLoading(true);
        setAlert({ show: false });
        setActiveStep(0);
        setResults(null);

        try {
            setActiveStep(1);
            const response = await fetch(`${API_BASE_URL}/api/bulk-process-job`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    job_url: jobUrl,
                    single_candidate_prompt: singleCandidatePrompt,
                    multi_candidate_prompt: multiCandidatePrompt,
                    generate_email: generateEmail,
                    auto_push: autoPush,
                    status_id: selectedStage
                })
            });

            const data = await response.json();
            setActiveStep(2);

            if (response.ok) {
                showAlert('success', data.message || 'Bulk processing completed!');
                setResults(data);
                setActiveStep(3);
            } else {
                showAlert('error', data.error || 'Failed to complete bulk process');
                setActiveStep(-1);
            }

        } catch (error) {
            console.error('Error in bulk process:', error);
            showAlert('error', 'A network error occurred during the bulk process.');
            setActiveStep(-1);
        } finally {
            setLoading(false);
        }
    };

    const showAlert = (type, message) => {
        setAlert({ show: true, type, message });
    };

    const steps = ['Fetching Candidates', 'Generating Summaries', 'Finalizing'];

    return (
        <Grid container spacing={3}>
            <Grid item xs={12} md={5}>
                <Card>
                    <CardContent>
                        <Typography variant="h4" sx={{ mb: 2 }}>Bulk Process Job</Typography>

                        <TextField
                            label="RecruitCRM Job URL"
                            value={jobUrl}
                            onChange={handleJobUrlChange}
                            fullWidth
                            sx={{ mb: 2 }}
                            placeholder="Paste a RecruitCRM job URL..."
                        />

                        <FormControl fullWidth sx={{ mb: 2 }}>
                            <InputLabel id="hiring-stage-label">Hiring Stage</InputLabel>
                            <Select
                                labelId="hiring-stage-label"
                                value={selectedStage}
                                onChange={(e) => setSelectedStage(e.target.value)}
                                label="Hiring Stage"
                                disabled={stagesLoading || jobStages.length === 0}
                                startAdornment={stagesLoading && <CircularProgress size={20} sx={{ mr: 1 }} />}
                            >
                                {jobStages.map((stage) => (
                                    <MenuItem key={stage.status_id} value={stage.status_id}>
                                        {`${stage.label} (${stage.candidate_count})`}
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>

                        <FormControl fullWidth sx={{ mb: 2 }}>
                            <InputLabel>Individual Summary Prompt</InputLabel>
                            <Select
                                value={singleCandidatePrompt}
                                onChange={(e) => setSingleCandidatePrompt(e.target.value)}
                                label="Individual Summary Prompt"
                            >
                                {availablePrompts.single.map((prompt) => (
                                    <MenuItem key={prompt.id} value={prompt.id}>
                                        {prompt.name}
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>

                        <FormControl fullWidth sx={{ mb: 2 }}>
                            <InputLabel>Multi-Candidate Email Prompt</InputLabel>
                            <Select
                                value={multiCandidatePrompt}
                                onChange={(e) => setMultiCandidatePrompt(e.target.value)}
                                label="Multi-Candidate Email Prompt"
                                disabled={!generateEmail}
                            >
                                {availablePrompts.multiple.map((prompt) => (
                                    <MenuItem key={prompt.id} value={prompt.id}>
                                        {prompt.name}
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>

                        <FormGroup>
                            <FormControlLabel
                                control={<Switch checked={generateEmail} onChange={(e) => setGenerateEmail(e.target.checked)} />}
                                label="Generate Email Summary"
                            />
                            <FormControlLabel
                                control={<Switch checked={autoPush} onChange={(e) => setAutoPush(e.target.checked)} />}
                                label="Auto-push summaries to RecruitCRM"
                            />
                        </FormGroup>

                        <Button
                            variant="contained"
                            color="primary"
                            onClick={handleBulkProcess}
                            disabled={loading || stagesLoading || !selectedStage}
                            fullWidth
                            sx={{ mt: 2 }}
                        >
                            {loading ? <CircularProgress size={24} /> : 'Go Mofo Go'}
                        </Button>
                    </CardContent>
                </Card>
            </Grid>
            <Grid item xs={12} md={7}>
                <Card>
                    <CardContent>
                        <Typography variant="h4" sx={{ mb: 2 }}>Progress & Results</Typography>
                        {alert.show && <Alert severity={alert.type} sx={{ mb: 2 }} onClose={() => setAlert({ show: false })}>{alert.message}</Alert>}

                        <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
                            {steps.map((label) => (
                                <Step key={label}>
                                    <StepLabel>{label}</StepLabel>
                                </Step>
                            ))}
                        </Stepper>

                        {results && (
                            <Box>
                                <Typography variant="h5" gutterBottom>
                                    Results for: {results.job_title}
                                </Typography>
                                <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
                                    Found {results.candidates_found} candidates |
                                    Processed: {results.summaries_generated} |
                                    Failed: {results.failures} |
                                    Pushed to CRM: {results.pushes_attempted}
                                </Typography>

                                {results.email_html && (
                                    <Card variant="outlined" sx={{ my: 2 }}>
                                        <CardContent>
                                            <Typography variant="h6" gutterBottom>Generated Email</Typography>
                                            <Paper elevation={0} variant="outlined" sx={{ p: 2, maxHeight: 400, overflow: 'auto' }}>
                                                <Box dangerouslySetInnerHTML={{ __html: results.email_html }} />
                                            </Paper>
                                        </CardContent>
                                    </Card>
                                )}
                                <Divider sx={{ my: 2 }} />
                                <Typography variant="h6" sx={{ mt: 2, mb: 1 }}>Individual Summaries</Typography>
                                {results.summaries && Object.entries(results.summaries).map(([name, summary]) => (
                                    <Accordion key={name}>
                                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                                            <Typography sx={{ color: 'success.main', fontWeight: 'bold' }}>Success: {name}</Typography>
                                        </AccordionSummary>
                                        <AccordionDetails>
                                            <Paper variant="outlined" sx={{ p: 2 }}>
                                                <Box dangerouslySetInnerHTML={{ __html: summary }} />
                                            </Paper>
                                        </AccordionDetails>
                                    </Accordion>
                                ))}
                                {results.failed_candidates && Object.entries(results.failed_candidates).map(([name, reason]) => (
                                    <Accordion key={name} disabled>
                                        <AccordionSummary>
                                            <Typography sx={{ color: 'error.main', fontWeight: 'bold' }}>Failed: {name}</Typography>
                                        </AccordionSummary>
                                        <AccordionDetails>
                                            <Typography variant="body2">{reason}</Typography>
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