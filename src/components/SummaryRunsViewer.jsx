import React, { useState, useEffect } from 'react';
import {
    Box,
    Paper,
    Typography,
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
    Button,
    TextField,
    CircularProgress,
    Alert,
    Collapse,
    Grid
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import DescriptionIcon from '@mui/icons-material/Description';

const SummaryRunsViewer = () => {
    const [runs, setRuns] = useState([]);
    const [loading, setLoading] = useState(true);
    const [expandedRunId, setExpandedRunId] = useState(null);
    const [selectedRun, setSelectedRun] = useState(null);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [error, setError] = useState(null);
    
    // Filters
    const [nameFilter, setNameFilter] = useState('');
    const [jobFilter, setJobFilter] = useState('');
    
    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

    useEffect(() => {
        loadRuns();
    }, []);

    const loadRuns = async () => {
        try {
            setLoading(true);
            setError(null);
            
            const response = await fetch(`${API_BASE_URL}/api/summary-runs?limit=50`);
            if (!response.ok) throw new Error('Failed to load runs');
            
            const data = await response.json();
            setRuns(data.runs || []);
        } catch (err) {
            console.error('Error loading runs:', err);
            setError(`Failed to load runs: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    const handleExpandClick = (runId) => {
        setExpandedRunId(expandedRunId === runId ? null : runId);
    };

    const handleViewDetails = (run) => {
        setSelectedRun(run);
        setDialogOpen(true);
    };

    const handleCloseDialog = () => {
        setDialogOpen(false);
        setSelectedRun(null);
    };

    const filteredRuns = runs.filter(run => {
        const candidateMatch = !nameFilter || 
            (run.candidate_name && run.candidate_name.toLowerCase().includes(nameFilter.toLowerCase()));
        const jobMatch = !jobFilter || 
            (run.job_name && run.job_name.toLowerCase().includes(jobFilter.toLowerCase()));
        return candidateMatch && jobMatch;
    });

    if (loading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress />
            </Box>
        );
    }

    return (
        <Box>
            {error && (
                <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                    {error}
                </Alert>
            )}

            <Paper sx={{ p: 2, mb: 2 }}>
                <Typography variant="h5" gutterBottom>
                    Summary Generation Runs
                </Typography>
                
                <Grid container spacing={2} sx={{ mt: 1 }}>
                    <Grid item xs={12} md={4}>
                        <TextField
                            fullWidth
                            size="small"
                            label="Filter by Candidate"
                            value={nameFilter}
                            onChange={(e) => setNameFilter(e.target.value)}
                        />
                    </Grid>
                    <Grid item xs={12} md={4}>
                        <TextField
                            fullWidth
                            size="small"
                            label="Filter by Job"
                            value={jobFilter}
                            onChange={(e) => setJobFilter(e.target.value)}
                        />
                    </Grid>
                    <Grid item xs={12} md={4}>
                        <Button variant="outlined" onClick={loadRuns} fullWidth>
                            Refresh
                        </Button>
                    </Grid>
                </Grid>
            </Paper>

            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell width="50px"></TableCell>
                            <TableCell>Candidate</TableCell>
                            <TableCell>Job</TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell>Prompt</TableCell>
                            <TableCell>Sources</TableCell>
                            <TableCell>Date</TableCell>
                            <TableCell>Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {filteredRuns.map((run) => (
                            <React.Fragment key={run.id}>
                                <TableRow hover>
                                    <TableCell>
                                        <IconButton
                                            size="small"
                                            onClick={() => handleExpandClick(run.id)}
                                        >
                                            {expandedRunId === run.id ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                                        </IconButton>
                                    </TableCell>
                                    <TableCell>{run.candidate_name || 'N/A'}</TableCell>
                                    <TableCell>{run.job_name || 'N/A'}</TableCell>
                                    <TableCell>
                                        <Chip
                                            icon={run.success ? <CheckCircleIcon /> : <CancelIcon />}
                                            label={run.success ? 'Success' : 'Failed'}
                                            color={run.success ? 'success' : 'error'}
                                            size="small"
                                        />
                                    </TableCell>
                                    <TableCell>
                                        <Typography variant="caption">
                                            {run.prompt_id || 'N/A'}
                                        </Typography>
                                    </TableCell>
                                    <TableCell>
                                        <Box sx={{ display: 'flex', gap: 0.5 }}>
                                            {run.sources_used?.resume && (
                                                <Chip icon={<DescriptionIcon />} label="CV" size="small" />
                                            )}
                                            {run.sources_used?.anna_ai && (
                                                <Chip label="Anna" size="small" />
                                            )}
                                            {run.sources_used?.quil && (
                                                <Chip label="Quil" size="small" />
                                            )}
                                            {run.sources_used?.fireflies && (
                                                <Chip label="Fireflies" size="small" />
                                            )}
                                        </Box>
                                    </TableCell>
                                    <TableCell>
                                        <Typography variant="caption">
                                            {run.timestamp ? 
                                                new Date(run.timestamp).toLocaleString() : 
                                                'N/A'}
                                        </Typography>
                                    </TableCell>
                                    <TableCell>
                                        <Button
                                            size="small"
                                            variant="outlined"
                                            onClick={() => handleViewDetails(run)}
                                            disabled={!run.summary_html && !run.generation?.data?.html_summary}
                                        >
                                            View Summary
                                        </Button>
                                    </TableCell>
                                </TableRow>
                                <TableRow>
                                    <TableCell colSpan={8} sx={{ p: 0 }}>
                                        <Collapse in={expandedRunId === run.id} timeout="auto" unmountOnExit>
                                            <Box sx={{ p: 2, bgcolor: 'background.default' }}>
                                                <Typography variant="subtitle2" gutterBottom>
                                                    Test Results
                                                </Typography>
                                                {run.tests && Object.entries(run.tests).map(([key, test]) => (
                                                    <Box key={key} sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
                                                        {test.success ? 
                                                            <CheckCircleIcon fontSize="small" color="success" /> : 
                                                            <CancelIcon fontSize="small" color="error" />
                                                        }
                                                        <Typography variant="body2" sx={{ ml: 1 }}>
                                                            {key.replace(/_/g, ' ')}: {test.success ? 'Pass' : (test.error || 'Fail')}
                                                        </Typography>
                                                    </Box>
                                                ))}
                                                
                                                {run.generation?.error && (
                                                    <Box sx={{ mt: 2 }}>
                                                        <Typography variant="subtitle2" color="error" gutterBottom>
                                                            Error
                                                        </Typography>
                                                        <Typography variant="body2" color="error">
                                                            {run.generation.error}
                                                        </Typography>
                                                    </Box>
                                                )}
                                            </Box>
                                        </Collapse>
                                    </TableCell>
                                </TableRow>
                            </React.Fragment>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            {/* Details Dialog */}
            <Dialog
                open={dialogOpen}
                onClose={handleCloseDialog}
                maxWidth="lg"
                fullWidth
            >
                <DialogTitle>
                    Generated Summary
                </DialogTitle>
                <DialogContent dividers>
                    {selectedRun && (
                        <Box>
                            <Box sx={{ mb: 2, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
                                <Grid container spacing={2}>
                                    <Grid item xs={6}>
                                        <Typography variant="body2" color="text.secondary">
                                            Candidate
                                        </Typography>
                                        <Typography variant="body1" fontWeight="medium">
                                            {selectedRun.candidate_name || 'N/A'}
                                        </Typography>
                                    </Grid>
                                    <Grid item xs={6}>
                                        <Typography variant="body2" color="text.secondary">
                                            Job
                                        </Typography>
                                        <Typography variant="body1" fontWeight="medium">
                                            {selectedRun.job_name || 'N/A'}
                                        </Typography>
                                    </Grid>
                                </Grid>
                            </Box>

                            {selectedRun.summary_html || selectedRun.generation?.data?.html_summary ? (
                                <Box 
                                    sx={{ 
                                        p: 2, 
                                        border: '1px solid #ddd', 
                                        borderRadius: 1,
                                        bgcolor: 'white',
                                        maxHeight: '600px',
                                        overflow: 'auto'
                                    }}
                                    dangerouslySetInnerHTML={{ 
                                        __html: selectedRun.summary_html || selectedRun.generation?.data?.html_summary 
                                    }}
                                />
                            ) : (
                                <Alert severity="info">
                                    No summary generated for this run
                                </Alert>
                            )}
                        </Box>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleCloseDialog}>Close</Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
};

export default SummaryRunsViewer;
