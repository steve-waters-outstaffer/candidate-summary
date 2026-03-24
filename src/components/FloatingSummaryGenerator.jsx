import React, { useState } from 'react';
import {
    Box,
    Card,
    CardContent,
    TextField,
    Button,
    Typography,
    Alert,
    CircularProgress,
    Divider,
    Paper,
    Grid,
    Collapse
} from '@mui/material';
import {
    CheckCircle,
    Cancel,
    HelpOutline,
    ThumbUp,
    ThumbDown,
    PictureAsPdf,
    InfoOutlined
} from '@mui/icons-material';

const CustomColors = {
    SecretGarden: '#5a9a5a',
    DarkRed: '#b71c1c',
    UIGrey500: '#9e9e9e',
    UIGrey300: '#e0e0e0',
    UIGrey100: '#f5f5f5',
    MidnightBlue: '#191970',
};
const FontWeight = { Medium: 500 };
const Spacing = { Large: 3, Medium: 2, Small: 1 };

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

const StatusIcon = ({ status }) => {
    if (status === 'success') return <CheckCircle sx={{ color: CustomColors.SecretGarden, fontSize: 20 }} />;
    if (status === 'error') return <Cancel sx={{ color: CustomColors.DarkRed, fontSize: 20 }} />;
    if (status === 'warning') return <InfoOutlined sx={{ color: '#ED8936', fontSize: 20 }} />;
    if (status === 'loading') return <CircularProgress size={18} />;
    return <HelpOutline sx={{ color: CustomColors.UIGrey500, fontSize: 20 }} />;
};

// Regex targeting: https://app.recruitcrm.io/v2/candidate/{slug}
const parseCandidateSlug = (input) => {
    if (!input) return null;
    const urlMatch = input.match(/\/v2\/candidate\/([^/?#\s]+)/);
    if (urlMatch) return urlMatch[1];
    // Accept raw slug if no slashes
    if (!input.includes('/')) return input.trim();
    return null;
};

const FloatingSummaryGenerator = () => {
    const [recruitCrmUrl, setRecruitCrmUrl] = useState('');
    const [candidateSlug, setCandidateSlug] = useState('');
    const [additionalContext, setAdditionalContext] = useState('');

    const [apiStatus, setApiStatus] = useState({
        candidate: { status: 'pending', message: '', data: null },
        resume: { status: 'pending', message: '', data: null },
        interview: { status: 'pending', message: '', data: null }
    });

    const [generatedHtml, setGeneratedHtml] = useState('');
    const [loading, setLoading] = useState(false);
    const [downloading, setDownloading] = useState(false);
    const [alert, setAlert] = useState({ show: false, type: 'info', message: '' });

    // Feedback state
    const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
    const [showFeedbackComment, setShowFeedbackComment] = useState(false);
    const [feedbackComment, setFeedbackComment] = useState('');

    const showAlert = (type, message) => setAlert({ show: true, type, message });

    const handleParseUrl = async () => {
        const slug = parseCandidateSlug(recruitCrmUrl);
        if (!slug) {
            showAlert('error', 'Could not extract a candidate slug from that URL. Expected format: .../v2/candidate/{slug}');
            return;
        }

        setCandidateSlug(slug);
        setGeneratedHtml('');
        setFeedbackSubmitted(false);

        // Kick off all three checks in parallel
        setApiStatus({
            candidate: { status: 'loading', message: 'Checking...', data: null },
            resume: { status: 'loading', message: 'Checking...', data: null },
            interview: { status: 'loading', message: 'Checking...', data: null }
        });

        const [candidateRes, resumeRes, interviewRes] = await Promise.all([
            fetch(`${API_BASE_URL}/api/floating/test-candidate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ candidate_slug: slug })
            }).then(r => r.json()).catch(() => ({ error: 'Network error' })),

            fetch(`${API_BASE_URL}/api/floating/test-resume`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ candidate_slug: slug })
            }).then(r => r.json()).catch(() => ({ error: 'Network error' })),

            fetch(`${API_BASE_URL}/api/floating/test-interview`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ candidate_slug: slug })
            }).then(r => r.json()).catch(() => ({ error: 'Network error' }))
        ]);

        setApiStatus({
            candidate: {
                status: candidateRes.success ? 'success' : 'error',
                message: candidateRes.candidate_name || candidateRes.error || 'Not found',
                data: candidateRes
            },
            resume: {
                status: resumeRes.success ? 'success' : 'error',
                message: resumeRes.filename || resumeRes.message || resumeRes.error || 'No resume',
                data: resumeRes
            },
            interview: {
                status: interviewRes.success ? 'success' : 'warning',
                message: interviewRes.message || interviewRes.error || 'No interview found',
                data: interviewRes
            }
        });
    };

    const handleGenerate = async () => {
        if (!candidateSlug) return;
        setLoading(true);
        setGeneratedHtml('');
        setAlert({ show: false, type: 'info', message: '' });

        try {
            const res = await fetch(`${API_BASE_URL}/api/floating/generate-summary`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    candidate_slug: candidateSlug,
                    additional_context: additionalContext,
                    prompt_type: 'floating.candidate-v1'
                })
            });
            const data = await res.json();
            if (data.success && data.html_summary) {
                setGeneratedHtml(data.html_summary);
                setFeedbackSubmitted(false);
                setShowFeedbackComment(false);
                setFeedbackComment('');
            } else {
                showAlert('error', data.error || 'Generation failed. Please try again.');
            }
        } catch {
            showAlert('error', 'Network error during generation.');
        } finally {
            setLoading(false);
        }
    };

    const handleDownloadPdf = async () => {
        if (!generatedHtml) return;
        setDownloading(true);
        try {
            const res = await fetch(`${API_BASE_URL}/api/floating/generate-pdf`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    html_summary: generatedHtml,
                    candidate_name: apiStatus.candidate.data?.candidate_name || 'Candidate'
                })
            });
            if (!res.ok) {
                showAlert('error', 'PDF generation failed.');
                return;
            }
            const blob = await res.blob();
            const contentDisposition = res.headers.get('Content-Disposition') || '';
            const filenameMatch = contentDisposition.match(/filename="([^"]+)"/);
            const filename = filenameMatch ? filenameMatch[1] : 'Floating-Summary.pdf';
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            a.click();
            URL.revokeObjectURL(url);
        } catch {
            showAlert('error', 'Network error during PDF download.');
        } finally {
            setDownloading(false);
        }
    };

    const handleFeedbackSubmit = async (rating) => {
        setFeedbackSubmitted(true);
        // Fire-and-forget — same as CandidateSummaryGenerator
        fetch(`${API_BASE_URL}/api/feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                rating,
                comment: feedbackComment,
                prompt_type: 'floating.candidate-v1',
                candidate_slug: candidateSlug
            })
        }).catch(() => {});
    };

    const isGenerateDisabled = loading || apiStatus.candidate.status !== 'success';

    return (
        <Box>
            <Grid container spacing={Spacing.Large}>
                {/* Left column: input */}
                <Grid item xs={12} md={5}>
                    <Card>
                        <CardContent>
                            <Typography variant="h6" gutterBottom sx={{ color: CustomColors.MidnightBlue, fontWeight: FontWeight.Medium }}>
                                Floating Candidate Summary
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ mb: Spacing.Medium }}>
                                Generate an anonymous one-page candidate brief for sharing with clients. No job required.
                            </Typography>

                            <TextField
                                fullWidth
                                label="RecruitCRM Candidate URL"
                                placeholder="https://app.recruitcrm.io/v2/candidate/..."
                                value={recruitCrmUrl}
                                onChange={(e) => setRecruitCrmUrl(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && handleParseUrl()}
                                sx={{ mb: Spacing.Medium }}
                            />

                            <Button
                                variant="outlined"
                                fullWidth
                                onClick={handleParseUrl}
                                disabled={!recruitCrmUrl.trim()}
                                sx={{ mb: Spacing.Medium }}
                            >
                                Parse & Confirm URL
                            </Button>

                            {/* Status rows */}
                            {(apiStatus.candidate.status !== 'pending' || apiStatus.resume.status !== 'pending') && (
                                <Box sx={{ mb: Spacing.Medium, p: Spacing.Small, border: `1px solid ${CustomColors.UIGrey300}`, borderRadius: 1 }}>
                                    {[
                                        { label: 'Candidate Profile', key: 'candidate' },
                                        { label: 'Candidate Resume', key: 'resume' },
                                        { label: 'AI Interview Note', key: 'interview' }
                                    ].map(({ label, key }) => (
                                        <Box key={key} sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 0.75 }}>
                                            <StatusIcon status={apiStatus[key].status} />
                                            <Typography variant="body2" sx={{ fontWeight: FontWeight.Medium, minWidth: 140 }}>
                                                {label}:
                                            </Typography>
                                            <Typography variant="body2" color="text.secondary">
                                                {apiStatus[key].message}
                                            </Typography>
                                        </Box>
                                    ))}
                                </Box>
                            )}

                            <TextField
                                fullWidth
                                multiline
                                rows={3}
                                label="Additional Context (optional)"
                                placeholder="Any extra notes to guide the summary..."
                                value={additionalContext}
                                onChange={(e) => setAdditionalContext(e.target.value)}
                                sx={{ mb: Spacing.Medium }}
                            />

                            <Button
                                variant="contained"
                                fullWidth
                                onClick={handleGenerate}
                                disabled={isGenerateDisabled}
                                sx={{ backgroundColor: CustomColors.MidnightBlue }}
                            >
                                {loading ? <CircularProgress size={20} color="inherit" /> : 'Generate Summary'}
                            </Button>
                        </CardContent>
                    </Card>
                </Grid>

                {/* Right column: output */}
                <Grid item xs={12} md={7}>
                    {alert.show && (
                        <Alert severity={alert.type} sx={{ mb: Spacing.Medium }} onClose={() => setAlert({ show: false, type: 'info', message: '' })}>
                            {alert.message}
                        </Alert>
                    )}

                    {generatedHtml && (
                        <Card>
                            <CardContent>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: Spacing.Medium }}>
                                    <Typography variant="h6" sx={{ color: CustomColors.MidnightBlue, fontWeight: FontWeight.Medium }}>
                                        Generated Summary
                                    </Typography>
                                    <Button
                                        variant="contained"
                                        startIcon={downloading ? <CircularProgress size={16} color="inherit" /> : <PictureAsPdf />}
                                        onClick={handleDownloadPdf}
                                        disabled={downloading}
                                        sx={{ backgroundColor: CustomColors.MidnightBlue }}
                                    >
                                        {downloading ? 'Generating PDF...' : 'Download PDF'}
                                    </Button>
                                </Box>

                                <Divider sx={{ mb: Spacing.Medium }} />

                                <Paper sx={{ p: Spacing.Medium, backgroundColor: CustomColors.UIGrey100, border: `1px solid ${CustomColors.UIGrey300}`, borderRadius: 2, mb: Spacing.Medium }}>
                                    <Box dangerouslySetInnerHTML={{ __html: generatedHtml }} />
                                </Paper>

                                {/* Feedback widget */}
                                <Box sx={{ mt: Spacing.Medium, p: Spacing.Medium, border: `1px solid ${CustomColors.UIGrey300}`, borderRadius: 2, backgroundColor: '#fafafa' }}>
                                    {feedbackSubmitted ? (
                                        <Typography variant="body1" sx={{ color: CustomColors.SecretGarden, fontWeight: FontWeight.Medium, textAlign: 'center' }}>
                                            Thanks for your feedback!
                                        </Typography>
                                    ) : (
                                        <>
                                            <Typography variant="body2" sx={{ mb: 1, fontWeight: FontWeight.Medium, textAlign: 'center' }}>
                                                Was this summary helpful?
                                            </Typography>
                                            <Box sx={{ display: 'flex', justifyContent: 'center', gap: 1 }}>
                                                <Button variant="outlined" startIcon={<ThumbUp />} onClick={() => handleFeedbackSubmit('good')}>
                                                    Good
                                                </Button>
                                                <Button variant="outlined" color="error" startIcon={<ThumbDown />} onClick={() => setShowFeedbackComment(true)}>
                                                    Bad
                                                </Button>
                                            </Box>
                                            <Collapse in={showFeedbackComment}>
                                                <Box sx={{ mt: Spacing.Medium }}>
                                                    <TextField
                                                        fullWidth
                                                        multiline
                                                        rows={3}
                                                        label="What was wrong with the summary?"
                                                        value={feedbackComment}
                                                        onChange={(e) => setFeedbackComment(e.target.value)}
                                                    />
                                                    <Button
                                                        variant="contained"
                                                        color="error"
                                                        sx={{ mt: 1 }}
                                                        onClick={() => handleFeedbackSubmit('bad')}
                                                    >
                                                        Submit Feedback
                                                    </Button>
                                                </Box>
                                            </Collapse>
                                        </>
                                    )}
                                </Box>
                            </CardContent>
                        </Card>
                    )}
                </Grid>
            </Grid>
        </Box>
    );
};

export default FloatingSummaryGenerator;
