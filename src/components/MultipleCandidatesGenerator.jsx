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
    Chip
} from '@mui/material';
import {
    CheckCircle,
    Cancel,
    Delete,
    Add
} from '@mui/icons-material';

const CustomColors = {
    SecretGarden: '#5a9a5a',
    DarkRed: '#b71c1c',
    DeepSkyBlue: '#00bfff',
    UIGrey500: '#9e9e9e',
    UIGrey300: '#e0e0e0',
    UIGrey100: '#f5f5f5',
    MidnightBlue: '#191970',
};
const Spacing = { Large: 3, Medium: 2, Small: 1 };

const MultipleCandidatesGenerator = () => {
    const [formData, setFormData] = useState({
        candidate_urls: ['', '', '', '', ''],
        client_name: '',
        job_url: '',
        preferred_candidate: '',
        additional_context: '',
        prompt_type: ''
    });
    
    const [candidateValidation, setCandidateValidation] = useState({});
    const [availablePrompts, setAvailablePrompts] = useState([]);
    const [generatedContent, setGeneratedContent] = useState('');
    const [loading, setLoading] = useState(false);
    const [alert, setAlert] = useState({ show: false, type: 'info', message: '' });
    const [view, setView] = useState('preview');

    // API Base URL from environment
    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

    // Load available prompts on component mount
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
            }
        } catch (error) {
            console.error('Error fetching prompts:', error);
        }
    };

    const handleInputChange = (field, value) => {
        setFormData(prev => ({
            ...prev,
            [field]: value
        }));
    };

    const handleCandidateUrlChange = (index, value) => {
        const newUrls = [...formData.candidate_urls];
        newUrls[index] = value;
        setFormData(prev => ({
            ...prev,
            candidate_urls: newUrls
        }));
        
        // Clear validation when URL changes
        if (candidateValidation[index]) {
            setCandidateValidation(prev => ({
                ...prev,
                [index]: undefined
            }));
        }
    };

    const validateCandidateUrl = async (index) => {
        const url = formData.candidate_urls[index];
        if (!url.trim()) return;

        setCandidateValidation(prev => ({
            ...prev,
            [index]: { status: 'validating', name: '' }
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
                setCandidateValidation(prev => ({
                    ...prev,
                    [index]: {
                        status: 'valid',
                        name: data.candidate_name
                    }
                }));
            } else {
                setCandidateValidation(prev => ({
                    ...prev,
                    [index]: { status: 'invalid', name: '' }
                }));
            }
        } catch (error) {
            setCandidateValidation(prev => ({
                ...prev,
                [index]: { status: 'invalid', name: '' }
            }));
        }
    };

    const generateContent = async () => {
        // Validate we have at least one candidate URL
        const validUrls = formData.candidate_urls.filter(url => url.trim());
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
                    ...formData,
                    candidate_urls: validUrls
                })
            });

            if (response.ok) {
                const data = await response.json();
                setGeneratedContent(data.generated_content);
                
                let message = `Generated content for ${data.candidates_processed} candidates`;
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
    };

    const handleViewChange = (event, newValue) => {
        setView(newValue);
    };

    const getValidatedCandidateNames = () => {
        return Object.entries(candidateValidation)
            .filter(([_, validation]) => validation?.status === 'valid')
            .map(([index, validation]) => ({
                index: parseInt(index),
                name: validation.name
            }));
    };

    const renderCandidateUrlField = (index) => {
        const validation = candidateValidation[index];
        const hasValue = formData.candidate_urls[index].trim();
        
        return (
            <Box key={index} sx={{ mb: 2 }}>
                <Grid container spacing={2} alignItems="center">
                    <Grid item xs={10}>
                        <TextField
                            label={`Candidate ${index + 1} URL`}
                            value={formData.candidate_urls[index]}
                            onChange={(e) => handleCandidateUrlChange(index, e.target.value)}
                            onBlur={() => hasValue && validateCandidateUrl(index)}
                            fullWidth
                            variant="outlined"
                            placeholder="https://outstaffer.recruitcrm.io/candidates/..."
                            InputProps={{
                                endAdornment: validation && (
                                    <Box sx={{ ml: 1 }}>
                                        {validation.status === 'validating' && <CircularProgress size={20} />}
                                        {validation.status === 'valid' && <CheckCircle sx={{ color: CustomColors.SecretGarden }} />}
                                        {validation.status === 'invalid' && <Cancel sx={{ color: CustomColors.DarkRed }} />}
                                    </Box>
                                )
                            }}
                        />
                        {validation?.status === 'valid' && (
                            <Typography variant="caption" sx={{ color: CustomColors.SecretGarden, mt: 1 }}>
                                ✓ {validation.name}
                            </Typography>
                        )}
                    </Grid>
                    <Grid item xs={2}>
                        <Button
                            variant="outlined"
                            size="small"
                            onClick={() => validateCandidateUrl(index)}
                            disabled={!hasValue || validation?.status === 'validating'}
                        >
                            Validate
                        </Button>
                    </Grid>
                </Grid>
            </Box>
        );
    };

    return (
        <Card>
            <CardContent>
                <Typography variant="h5" gutterBottom>
                    Multiple Candidates Generator
                </Typography>
                
                {alert.show && (
                    <Alert 
                        severity={alert.type} 
                        onClose={() => setAlert({ show: false })}
                        sx={{ mb: 2 }}
                    >
                        {alert.message}
                    </Alert>
                )}

                <Grid container spacing={3}>
                    {/* Left Column - Input Form */}
                    <Grid item xs={12} md={6}>
                        <Box sx={{ mb: 3 }}>
                            <Typography variant="h6" gutterBottom>
                                Candidate URLs
                            </Typography>
                            {formData.candidate_urls.map((_, index) => renderCandidateUrlField(index))}
                        </Box>

                        <Box sx={{ mb: 3 }}>
                            <Typography variant="h6" gutterBottom>
                                Email Details
                            </Typography>
                            
                            <TextField
                                label="Client Name"
                                value={formData.client_name}
                                onChange={(e) => handleInputChange('client_name', e.target.value)}
                                fullWidth
                                sx={{ mb: 2 }}
                            />
                            
                            <TextField
                                label="Job URL"
                                value={formData.job_url}
                                onChange={(e) => handleInputChange('job_url', e.target.value)}
                                fullWidth
                                sx={{ mb: 2 }}
                                placeholder="https://outstaffer.recruitcrm.io/jobs/..."
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
                                label="Additional Context"
                                value={formData.additional_context}
                                onChange={(e) => handleInputChange('additional_context', e.target.value)}
                                fullWidth
                                multiline
                                rows={3}
                                sx={{ mb: 2 }}
                                placeholder="Any additional context or instructions..."
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
                        </Box>

                        <Button
                            variant="contained"
                            color="primary"
                            onClick={generateContent}
                            disabled={loading}
                            fullWidth
                            sx={{ mb: 2 }}
                        >
                            {loading ? <CircularProgress size={24} /> : 'Generate Email'}
                        </Button>
                    </Grid>

                    {/* Right Column - Generated Content */}
                    <Grid item xs={12} md={6}>
                        {generatedContent && (
                            <>
                                <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
                                    <Tabs value={view} onChange={handleViewChange}>
                                        <Tab label="Preview" value="preview" />
                                        <Tab label="HTML" value="html" />
                                    </Tabs>
                                </Box>

                                {view === 'preview' && (
                                    <Paper 
                                        sx={{ 
                                            p: 2, 
                                            backgroundColor: CustomColors.UIGrey100, 
                                            border: `1px solid ${CustomColors.UIGrey300}`,
                                            maxHeight: '600px',
                                            overflow: 'auto'
                                        }}
                                    >
                                        <Box dangerouslySetInnerHTML={{ __html: generatedContent }} />
                                    </Paper>
                                )}

                                {view === 'html' && (
                                    <TextField
                                        multiline
                                        rows={20}
                                        value={generatedContent}
                                        fullWidth
                                        variant="outlined"
                                        InputProps={{ readOnly: true }}
                                        sx={{ fontFamily: 'monospace' }}
                                    />
                                )}
                            </>
                        )}
                    </Grid>
                </Grid>
            </CardContent>
        </Card>
    );
};

export default MultipleCandidatesGenerator;