import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    AppBar,
    Toolbar,
    Typography,
    Button,
    Box,
    Container,
    Tabs,
    Tab,
    IconButton,
    Tooltip
} from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';
import { useAuth } from '../contexts/AuthContext';
import { logoutUser } from '../services/AuthService.js';
import CandidateSummaryGenerator from './CandidateSummaryGenerator';
import BulkGenerator from './BulkGenerator';
import PromptAdmin from './PromptAdmin';
import { CustomColors } from '../theme';

const Dashboard = () => {
    const { currentUser } = useAuth();
    const navigate = useNavigate();
    const [currentTab, setCurrentTab] = useState(0);

    // State for the bulk generation job, lifted up from BulkGenerator
    const [bulkJobId, setBulkJobId] = useState(null);
    const [bulkJobStatus, setBulkJobStatus] = useState(null);

    // Admin access control - add your email here
    const isAdmin = currentUser?.email === 'steve.waters@outstaffer.com';

    const handleTabChange = (event, newValue) => {
        setCurrentTab(newValue);
    };

    const handleLogout = async () => {
        try {
            await logoutUser();
            navigate('/login');
        } catch (error) {
            console.error("Logout error:", error);
        }
    };

    const handleSettingsClick = () => {
        setCurrentTab(2); // Switch to Admin tab
    };

    return (
        <Box sx={{ display: 'flex' }}>
            <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1, backgroundColor: CustomColors.MidnightBlue }}>
                <Toolbar>
                    <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
                        AI Candidate Summary
                    </Typography>
                    <Typography variant="body2" sx={{ mr: 2 }}>
                        {currentUser?.email}
                    </Typography>
                    {isAdmin && (
                        <Tooltip title="Admin Settings">
                            <IconButton
                                color="inherit"
                                onClick={handleSettingsClick}
                                size="small"
                                sx={{ mr: 1 }}
                            >
                                <SettingsIcon />
                            </IconButton>
                        </Tooltip>
                    )}
                    <Button
                        variant="outlined"
                        color="default"
                        onClick={handleLogout}
                        size="small"
                    >
                        Logout
                    </Button>
                </Toolbar>
            </AppBar>

            <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
                {/* This Toolbar component adds the necessary spacing below the fixed AppBar */}
                <Toolbar />
                <Box sx={{ borderBottom: 1, borderColor: 'divider', bgcolor: 'background.paper' }}>
                    <Tabs
                        value={currentTab}
                        onChange={handleTabChange}
                    >
                        <Tab label="Single Candidate Summary" />
                        <Tab label="Bulk Job Processor" />
                        {isAdmin && <Tab label="Admin" />}
                    </Tabs>
                </Box>

                <Box sx={{ pt: 3 }}>
                    {currentTab === 0 && <CandidateSummaryGenerator />}
                    {currentTab === 1 && (
                        <BulkGenerator
                            jobId={bulkJobId}
                            setJobId={setBulkJobId}
                            jobStatus={bulkJobStatus}
                            setJobStatus={setBulkJobStatus}
                        />
                    )}
                    {currentTab === 2 && isAdmin && <PromptAdmin />}
                </Box>
            </Container>
        </Box>
    );
};

export default Dashboard;
