import React, { useState, useEffect } from 'react';
import {
    Box,
    Paper,
    Typography,
    Button,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    IconButton,
    Chip,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    TextField,
    Switch,
    FormControlLabel,
    MenuItem,
    Select,
    FormControl,
    InputLabel,
    Alert,
    Snackbar
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { authFetch } from '../services/apiService';

// Variable groups — each group declares which category/type combos it appears in.
// category: 'single' | 'multiple'   type: 'summary' | 'email'
const VARIABLE_GROUPS = [
    {
        label: 'Candidate Data',
        categories: ['single'],
        types: ['summary', 'email'],
        vars: [
            { tag: '{{candidate_name}}',     desc: 'Full name' },
            { tag: '{{candidate_email}}',    desc: 'Email address' },
            { tag: '{{candidate_phone}}',    desc: 'Phone number' },
            { tag: '{{candidate_location}}', desc: 'Location / city' },
            { tag: '{{candidate_summary}}',  desc: 'Bio / profile summary' },
        ],
    },
    {
        label: 'Job Data',
        categories: ['single', 'multiple'],
        types: ['summary', 'email'],
        vars: [
            { tag: '{{job_title}}',        desc: 'Job title' },
            { tag: '{{job_description}}',  desc: 'Full job description' },
            { tag: '{{job_requirements}}', desc: 'Key requirements' },
        ],
    },
    {
        label: 'Interview Data',
        categories: ['single'],
        types: ['summary', 'email'],
        vars: [
            { tag: '{{quil_interview}}',        desc: 'CoRecruit interview notes' },
            { tag: '{{ai_interview}}',           desc: 'AlphaRun AI interview' },
            { tag: '{{fireflies_transcript}}',   desc: 'Fireflies call transcript' },
        ],
    },
    {
        label: 'Multiple Candidates',
        categories: ['multiple'],
        types: ['summary', 'email'],
        vars: [
            { tag: '{{candidate_list}}',  desc: 'Formatted list of all candidates' },
            { tag: '{{candidate_count}}', desc: 'Number of candidates' },
        ],
    },
    {
        label: 'Context',
        categories: ['single', 'multiple'],
        types: ['summary', 'email'],
        vars: [
            { tag: '{{additional_context}}', desc: 'Extra notes / user-supplied context' },
        ],
    },
];

const codeStyle = { bgcolor: 'grey.200', px: 0.5, py: 0.25, borderRadius: 0.5, fontFamily: 'monospace', fontSize: '0.8rem' };

const VariablesPanel = ({ category = 'single', type = 'summary' }) => {
    const visibleGroups = VARIABLE_GROUPS.filter(
        g => g.categories.includes(category) && g.types.includes(type)
    );

    return (
        <Paper sx={{ flex: 1, p: 2, bgcolor: 'grey.50', maxHeight: '80vh', overflowY: 'auto', position: 'sticky', top: 16 }}>
            <Typography variant="h6" gutterBottom>Available Variables</Typography>
            <Alert severity="info" sx={{ mb: 2, fontSize: '0.75rem' }}>
                Showing variables for <strong>{category}</strong> / <strong>{type}</strong>.
                Change Category or Type above to update this list.
            </Alert>
            {visibleGroups.map(group => (
                <Box key={group.label} sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" sx={{ mb: 0.5, fontWeight: 'bold' }}>
                        {group.label}
                    </Typography>
                    {group.vars.map(({ tag, desc }) => (
                        <Box key={tag} sx={{ display: 'flex', alignItems: 'baseline', gap: 1, mb: 0.5 }}>
                            <Box component="code" sx={codeStyle}>{tag}</Box>
                            <Typography variant="caption" color="text.secondary">{desc}</Typography>
                        </Box>
                    ))}
                </Box>
            ))}
        </Paper>
    );
};

const PromptAdmin = () => {
    const [prompts, setPrompts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [editDialogOpen, setEditDialogOpen] = useState(false);
    const [currentPrompt, setCurrentPrompt] = useState(null);
    const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });

    useEffect(() => {
        loadPrompts();
    }, []);

    const loadPrompts = async () => {
        try {
            setLoading(true);
            const response = await authFetch('/api/admin/prompts');
            const data = await response.json();
            if (data.success) {
                setPrompts(data.prompts);
            }
        } catch (error) {
            console.error('Error loading prompts:', error);
            showSnackbar('Error loading prompts', 'error');
        } finally {
            setLoading(false);
        }
    };

    const showSnackbar = (message, severity = 'success') => {
        setSnackbar({ open: true, message, severity });
    };

    const handleEdit = (prompt) => {
        setCurrentPrompt(prompt);
        setEditDialogOpen(true);
    };

    const handleCreate = () => {
        setCurrentPrompt({
            name: '',
            slug: '',
            category: 'single',
            type: 'summary',
            enabled: true,
            is_default: false,
            sort_order: 100,
            system_prompt: '',
            template: '',
            user_prompt: ''
        });
        setEditDialogOpen(true);
    };

    const handleDuplicate = (prompt) => {
        setCurrentPrompt({
            ...prompt,
            name: `${prompt.name} (Copy)`,
            slug: `${prompt.slug}-copy`,
            is_default: false
        });
        setEditDialogOpen(true);
    };

    const handleSave = async () => {
        try {
            const path = currentPrompt.id
                ? `/api/admin/prompts/${currentPrompt.id}`
                : '/api/admin/prompts';
            const method = currentPrompt.id ? 'PUT' : 'POST';
            const response = await authFetch(path, {
                method,
                body: JSON.stringify(currentPrompt),
            });

            const data = await response.json();
            
            if (data.success) {
                showSnackbar(currentPrompt.id ? 'Prompt updated' : 'Prompt created');
                setEditDialogOpen(false);
                loadPrompts();
            } else {
                showSnackbar(data.error || 'Error saving prompt', 'error');
            }
        } catch (error) {
            console.error('Error saving prompt:', error);
            showSnackbar('Error saving prompt', 'error');
        }
    };

    const handleDelete = async (promptId) => {
        if (!confirm('Are you sure you want to delete this prompt?')) return;
        try {
            const response = await authFetch(`/api/admin/prompts/${promptId}`, { method: 'DELETE' });

            const data = await response.json();
            
            if (data.success) {
                showSnackbar('Prompt deleted');
                loadPrompts();
            } else {
                showSnackbar(data.error || 'Error deleting prompt', 'error');
            }
        } catch (error) {
            console.error('Error deleting prompt:', error);
            showSnackbar('Error deleting prompt', 'error');
        }
    };

    const handleToggleEnabled = async (prompt) => {
        try {
            const response = await authFetch(`/api/admin/prompts/${prompt.id}`, {
                method: 'PUT',
                body: JSON.stringify({ ...prompt, enabled: !prompt.enabled }),
            });

            const data = await response.json();
            
            if (data.success) {
                showSnackbar(`Prompt ${prompt.enabled ? 'disabled' : 'enabled'}`);
                loadPrompts();
            }
        } catch (error) {
            console.error('Error toggling prompt:', error);
            showSnackbar('Error updating prompt', 'error');
        }
    };

    const handleSetDefault = async (prompt) => {
        try {
            const response = await authFetch(`/api/admin/prompts/${prompt.id}/set-default`, { method: 'POST' });

            const data = await response.json();
            
            if (data.success) {
                showSnackbar('Default prompt updated');
                loadPrompts();
            }
        } catch (error) {
            console.error('Error setting default:', error);
            showSnackbar('Error setting default', 'error');
        }
    };

    return (
        <Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
                <Typography variant="h5">Prompt Management</Typography>
                <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={handleCreate}
                >
                    New Prompt
                </Button>
            </Box>

            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>Name</TableCell>
                            <TableCell>Category</TableCell>
                            <TableCell>Type</TableCell>
                            <TableCell>Sort</TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell>Default</TableCell>
                            <TableCell align="right">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {prompts.map((prompt) => (
                            <TableRow key={prompt.id}>
                                <TableCell>{prompt.name}</TableCell>
                                <TableCell>
                                    <Chip 
                                        label={prompt.category} 
                                        size="small" 
                                        color={prompt.category === 'single' ? 'primary' : 'secondary'}
                                    />
                                </TableCell>
                                <TableCell>
                                    <Chip label={prompt.type} size="small" variant="outlined" />
                                </TableCell>
                                <TableCell>{prompt.sort_order}</TableCell>
                                <TableCell>
                                    <Switch
                                        checked={prompt.enabled}
                                        onChange={() => handleToggleEnabled(prompt)}
                                        size="small"
                                    />
                                </TableCell>
                                <TableCell>
                                    {prompt.is_default ? (
                                        <Chip label="Default" color="success" size="small" />
                                    ) : (
                                        <Button
                                            size="small"
                                            onClick={() => handleSetDefault(prompt)}
                                        >
                                            Set Default
                                        </Button>
                                    )}
                                </TableCell>
                                <TableCell align="right">
                                    <IconButton size="small" onClick={() => handleEdit(prompt)}>
                                        <EditIcon fontSize="small" />
                                    </IconButton>
                                    <IconButton size="small" onClick={() => handleDuplicate(prompt)}>
                                        <ContentCopyIcon fontSize="small" />
                                    </IconButton>
                                    <IconButton size="small" onClick={() => handleDelete(prompt.id)}>
                                        <DeleteIcon fontSize="small" />
                                    </IconButton>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            {/* Edit/Create Dialog */}
            <Dialog 
                open={editDialogOpen} 
                onClose={() => setEditDialogOpen(false)}
                maxWidth="lg"
                fullWidth
            >
                <DialogTitle>
                    {currentPrompt?.id ? 'Edit Prompt' : 'Create New Prompt'}
                </DialogTitle>
                <DialogContent sx={{ minHeight: '70vh' }}>
                    <Box sx={{ display: 'flex', gap: 3, pt: 2 }}>
                        {/* Main Form */}
                        <Box sx={{ flex: 3, display: 'flex', flexDirection: 'column', gap: 2 }}>
                        <TextField
                            label="Name"
                            value={currentPrompt?.name || ''}
                            onChange={(e) => setCurrentPrompt({ ...currentPrompt, name: e.target.value })}
                            fullWidth
                        />
                        
                        <TextField
                            label="Slug (Document ID)"
                            value={currentPrompt?.slug || ''}
                            onChange={(e) => setCurrentPrompt({ ...currentPrompt, slug: e.target.value })}
                            fullWidth
                            helperText="Lowercase, hyphenated (e.g., 'summary-for-platform-v2')"
                        />

                        <Box sx={{ display: 'flex', gap: 2 }}>
                            <FormControl fullWidth>
                                <InputLabel>Category</InputLabel>
                                <Select
                                    value={currentPrompt?.category || 'single'}
                                    onChange={(e) => setCurrentPrompt({ ...currentPrompt, category: e.target.value })}
                                    label="Category"
                                >
                                    <MenuItem value="single">Single</MenuItem>
                                    <MenuItem value="multiple">Multiple</MenuItem>
                                </Select>
                            </FormControl>

                            <FormControl fullWidth>
                                <InputLabel>Type</InputLabel>
                                <Select
                                    value={currentPrompt?.type || 'summary'}
                                    onChange={(e) => setCurrentPrompt({ ...currentPrompt, type: e.target.value })}
                                    label="Type"
                                >
                                    <MenuItem value="summary">Summary</MenuItem>
                                    <MenuItem value="email">Email</MenuItem>
                                </Select>
                            </FormControl>

                            <TextField
                                label="Sort Order"
                                type="number"
                                value={currentPrompt?.sort_order || 100}
                                onChange={(e) => setCurrentPrompt({ ...currentPrompt, sort_order: parseInt(e.target.value) })}
                                sx={{ width: 150 }}
                            />
                        </Box>

                        <FormControlLabel
                            control={
                                <Switch
                                    checked={currentPrompt?.enabled || false}
                                    onChange={(e) => setCurrentPrompt({ ...currentPrompt, enabled: e.target.checked })}
                                />
                            }
                            label="Enabled"
                        />

                        <FormControlLabel
                            control={
                                <Switch
                                    checked={currentPrompt?.is_default || false}
                                    onChange={(e) => setCurrentPrompt({ ...currentPrompt, is_default: e.target.checked })}
                                />
                            }
                            label="Set as Default"
                        />

                        <TextField
                            label="System Prompt"
                            value={currentPrompt?.system_prompt || ''}
                            onChange={(e) => setCurrentPrompt({ ...currentPrompt, system_prompt: e.target.value })}
                            multiline
                            rows={12}
                            fullWidth
                        />

                        <TextField
                            label="Template (HTML)"
                            value={currentPrompt?.template || ''}
                            onChange={(e) => setCurrentPrompt({ ...currentPrompt, template: e.target.value })}
                            multiline
                            rows={16}
                            fullWidth
                        />

                        <TextField
                            label="User Prompt"
                            value={currentPrompt?.user_prompt || ''}
                            onChange={(e) => setCurrentPrompt({ ...currentPrompt, user_prompt: e.target.value })}
                            multiline
                            rows={8}
                            fullWidth
                        />
                    </Box>

                    {/* Context-Aware Variables Reference */}
                    <VariablesPanel category={currentPrompt?.category} type={currentPrompt?.type} />
                    </Box>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
                    <Button onClick={handleSave} variant="contained">Save</Button>
                </DialogActions>
            </Dialog>

            {/* Snackbar for notifications */}
            <Snackbar
                open={snackbar.open}
                autoHideDuration={4000}
                onClose={() => setSnackbar({ ...snackbar, open: false })}
            >
                <Alert severity={snackbar.severity} onClose={() => setSnackbar({ ...snackbar, open: false })}>
                    {snackbar.message}
                </Alert>
            </Snackbar>
        </Box>
    );
};

export default PromptAdmin;
