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
    Tab
} from '@mui/material';
import { useAuth } from '../contexts/AuthContext';
import { logoutUser } from '../services/AuthService.js';
import CandidateSummaryGenerator from './CandidateSummaryGenerator';
import MultipleCandidatesGenerator from './MultipleCandidatesGenerator';
import BulkGenerator from './BulkGenerator';
import { CustomColors } from '../theme';

const Dashboard = () => {
    const { currentUser } = useAuth();
    const navigate = useNavigate();
    const [currentTab, setCurrentTab] = useState(0);

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

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', bgcolor: CustomColors.UIGrey100 }}>
            <AppBar position="static" color="secondary">
                <Toolbar>
                    <Typography color="default" variant="h6" component="div" sx={{ flexGrow: 1 }}>
                        AI Candidate Summary
                    </Typography>
                    <Typography variant="body2" sx={{ mr: 2 }}>
                        {currentUser?.email}
                    </Typography>
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
                <Box sx={{ borderBottom: 1, borderColor: 'divider', bgcolor: 'background.paper' }}>
                    <Tabs
                        value={currentTab}
                        onChange={handleTabChange}
                        centered
                    >
                        <Tab label="Single Candidate Summary" />
                        <Tab label="Multi-Candidate Email" />
                        <Tab label="Bulk Job Processor" />
                    </Tabs>
                </Box>

                <Box sx={{ pt: 3 }}>
                    {currentTab === 0 && <CandidateSummaryGenerator />}
                    {currentTab === 1 && <MultipleCandidatesGenerator />}
                    {currentTab === 2 && <BulkGenerator />}
                </Box>
            </Container>
        </Box>
    );
};

export default Dashboard;