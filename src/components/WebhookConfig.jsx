import React, { useState, useEffect } from 'react';
import {
    Box,
    Card,
    CardContent,
    Typography,
    Alert,
    CircularProgress,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    FormControlLabel,
    Switch,
    TextField,
    Button,
    Divider,
    Paper
} from '@mui/material';
import { Save as SaveIcon, Refresh as RefreshIcon } from '@mui/icons-material';

const WebhookConfig = () => {
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [alert, setAlert] = useState({ show: false, type: 'info', message: '' });
    
    // Config state
    const [config, setConfig] = useState({
        enabled: true,
        default_prompt_id: '',
        prompt_category: 'single',
        use_quil: true,
        use_fireflies: false,
        proceed_without_interview: true,
        additional_context: '',
        auto_push: false,
        auto_push_delay_seconds: 0,
        create_tracking_note: false,
        max_concurrent_tasks: 5,
        rate_limit_per_minute: 10
    });

    // Available prompts from database
    const [prompts, setPrompts] = useState([]);

    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

    useEffect(() => {
        loadConfig();
        loadPrompts();
    }, []);

    const loadConfig = async () => {
        try {
            setLoading(true);
            const response = await fetch(`${API_BASE_URL}/api/webhook-config`);
            if (!response.ok) throw new Error('Failed to load config');
            const data = await response.json();
            setConfig(data);
            showAlert('success', 'Configuration loaded');
        } catch (error) {
            showAlert('error', `Failed to load config: ${error.message}`);
        } finally {
            setLoading(false);
        }
    };

    const loadPrompts = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/prompts?type=summary`);
            if (!response.ok) throw new Error('Failed to load prompts');
            const data = await response.json();
            setPrompts(data);
        } catch (error) {
            showAlert('error', `Failed to load prompts: ${error.message}`);
        }
    };

    const handleSave = async () => {
        try {
            setSaving(true);
            const response = await fetch(`${API_BASE_URL}/api/webhook-config`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            
            if (!response.ok) throw new Error('Failed to save config');
            
            showAlert('success', 'Configuration saved successfully');
        } catch (error) {
            showAlert('error', `Failed to save config: ${error.message}`);
        } finally {
            setSaving(false);
        }
    };

    const showAlert = (type, message) => {
        setAlert({ show: true, type, message });
        setTimeout(() => setAlert({ show: false, type: 'info', message: '' }), 5000);
    };

    const handleChange = (field, value) => {
        setConfig(prev => ({ ...prev, [field]: value }));
    };

    if (loading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress />
            </Box>
        );
    }

    return (
        <Box>
            {alert.show && (
                <Alert severity={alert.type} sx={{ mb: 2 }}>
                    {alert.message}
                </Alert>
            )}

            <Card>
                <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                        <Typography variant="h5">Webhook Configuration</Typography>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                            <Button
                                variant="outlined"
                                startIcon={<RefreshIcon />}
                                onClick={loadConfig}
                                disabled={loading || saving}
                            >
                                Refresh
                            </Button>
                            <Button
                                variant="contained"
                                startIcon={<SaveIcon />}
                                onClick={handleSave}
                                disabled={saving}
                            >
                                {saving ? 'Saving...' : 'Save Changes'}
                            </Button>
                        </Box>
                    </Box>

                    {/* Master Enable/Disable */}
                    <Paper sx={{ p: 2, mb: 3, bgcolor: 'background.default' }}>
                        <FormControlLabel
                            control={
                                <Switch
                                    checked={config.enabled}
                                    onChange={(e) => handleChange('enabled', e.target.checked)}
                                />
                            }
                            label={
                                <Box>
                                    <Typography variant="body1" fontWeight="medium">
                                        Enable Webhook Processing
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">
                                        When enabled, RecruitCRM webhooks will automatically trigger candidate summary generation
                                    </Typography>
                                </Box>
                            }
                        />
                    </Paper>

                    <Divider sx={{ my: 3 }} />

                    {/* Summary Generation Settings */}
                    <Typography variant="h6" gutterBottom>Summary Generation</Typography>

                    <FormControl fullWidth sx={{ mb: 3 }}>
                        <InputLabel>Default Summary Prompt</InputLabel>
                        <Select
                            value={prompts.some(p => p.id === config.default_prompt_id) ? config.default_prompt_id : ''}
                            onChange={(e) => handleChange('default_prompt_id', e.target.value)}
                            label="Default Summary Prompt"
                        >
                            {prompts.length === 0 ? (
                                <MenuItem value="" disabled>
                                    <em>Loading prompts...</em>
                                </MenuItem>
                            ) : (
                                prompts.map((prompt) => (
                                    <MenuItem key={prompt.id} value={prompt.id}>
                                        {prompt.name}
                                    </MenuItem>
                                ))
                            )}
                        </Select>
                        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, ml: 2 }}>
                            Which prompt template to use when generating candidate summaries automatically
                        </Typography>
                    </FormControl>

                    <FormControl fullWidth sx={{ mb: 3 }}>
                        <InputLabel>Prompt Category</InputLabel>
                        <Select
                            value={config.prompt_category}
                            onChange={(e) => handleChange('prompt_category', e.target.value)}
                            label="Prompt Category"
                        >
                            <MenuItem value="single">Single</MenuItem>
                            <MenuItem value="email">Email</MenuItem>
                        </Select>
                        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, ml: 2 }}>
                            Type of prompt to use for generation
                        </Typography>
                    </FormControl>

                    <TextField
                        fullWidth
                        multiline
                        rows={3}
                        label="Additional Context (Optional)"
                        value={config.additional_context}
                        onChange={(e) => handleChange('additional_context', e.target.value)}
                        sx={{ mb: 3 }}
                        helperText="Extra instructions or context to include in every summary generation"
                    />

                    <Divider sx={{ my: 3 }} />

                    {/* Data Source Settings */}
                    <Typography variant="h6" gutterBottom>Data Sources</Typography>

                    <Paper sx={{ p: 2, mb: 2, bgcolor: 'background.default' }}>
                        <FormControlLabel
                            control={
                                <Switch
                                    checked={config.use_quil}
                                    onChange={(e) => handleChange('use_quil', e.target.checked)}
                                />
                            }
                            label={
                                <Box>
                                    <Typography variant="body1" fontWeight="medium">
                                        Use Quil Interview Notes
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">
                                        Include Quil interview transcripts when generating summaries
                                    </Typography>
                                </Box>
                            }
                        />
                    </Paper>

                    <Paper sx={{ p: 2, mb: 2, bgcolor: 'background.default' }}>
                        <FormControlLabel
                            control={
                                <Switch
                                    checked={config.use_fireflies}
                                    onChange={(e) => handleChange('use_fireflies', e.target.checked)}
                                />
                            }
                            label={
                                <Box>
                                    <Typography variant="body1" fontWeight="medium">
                                        Use Fireflies Transcripts
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">
                                        Include Fireflies.ai meeting transcripts when generating summaries
                                    </Typography>
                                </Box>
                            }
                        />
                    </Paper>

                    <Paper sx={{ p: 2, mb: 3, bgcolor: 'background.default' }}>
                        <FormControlLabel
                            control={
                                <Switch
                                    checked={config.proceed_without_interview}
                                    onChange={(e) => handleChange('proceed_without_interview', e.target.checked)}
                                />
                            }
                            label={
                                <Box>
                                    <Typography variant="body1" fontWeight="medium">
                                        Generate Without Interview Data
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">
                                        Allow summary generation even when no Anna AI, Quil, or Fireflies interview data is available. Summary will be based on resume only.
                                    </Typography>
                                </Box>
                            }
                        />
                    </Paper>

                    <Divider sx={{ my: 3 }} />

                    {/* Post-Generation Actions */}
                    <Typography variant="h6" gutterBottom>Post-Generation Actions</Typography>

                    <Paper sx={{ p: 2, mb: 2, bgcolor: 'background.default' }}>
                        <FormControlLabel
                            control={
                                <Switch
                                    checked={config.create_tracking_note}
                                    onChange={(e) => handleChange('create_tracking_note', e.target.checked)}
                                />
                            }
                            label={
                                <Box>
                                    <Typography variant="body1" fontWeight="medium">
                                        Create Tracking Note
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">
                                        Automatically create a note in RecruitCRM with the generated summary after generation completes
                                    </Typography>
                                </Box>
                            }
                        />
                    </Paper>

                    <Paper sx={{ p: 2, mb: 2, bgcolor: 'background.default' }}>
                        <FormControlLabel
                            control={
                                <Switch
                                    checked={config.auto_push}
                                    onChange={(e) => handleChange('auto_push', e.target.checked)}
                                />
                            }
                            label={
                                <Box>
                                    <Typography variant="body1" fontWeight="medium">
                                        Auto-Push to Next Stage
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">
                                        Automatically move the candidate to the next stage in the pipeline after summary is generated
                                    </Typography>
                                </Box>
                            }
                        />
                    </Paper>

                    {config.auto_push && (
                        <TextField
                            fullWidth
                            type="number"
                            label="Auto-Push Delay (seconds)"
                            value={config.auto_push_delay_seconds}
                            onChange={(e) => handleChange('auto_push_delay_seconds', parseInt(e.target.value))}
                            sx={{ mb: 3 }}
                            helperText="How many seconds to wait before automatically pushing the candidate to the next stage"
                        />
                    )}

                    <Divider sx={{ my: 3 }} />

                    {/* Performance Settings */}
                    <Typography variant="h6" gutterBottom>Performance & Rate Limiting</Typography>

                    <TextField
                        fullWidth
                        type="number"
                        label="Max Concurrent Tasks"
                        value={config.max_concurrent_tasks}
                        onChange={(e) => handleChange('max_concurrent_tasks', parseInt(e.target.value))}
                        sx={{ mb: 3 }}
                        helperText="Maximum number of summary generation tasks that can run simultaneously"
                    />

                    <TextField
                        fullWidth
                        type="number"
                        label="Rate Limit (per minute)"
                        value={config.rate_limit_per_minute}
                        onChange={(e) => handleChange('rate_limit_per_minute', parseInt(e.target.value))}
                        sx={{ mb: 3 }}
                        helperText="Maximum number of webhook requests that can be processed per minute"
                    />
                </CardContent>
            </Card>
        </Box>
    );
};

export default WebhookConfig;
