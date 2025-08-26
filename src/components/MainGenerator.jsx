import React, { useState } from 'react';
import {
    Box,
    Tabs,
    Tab,
    Typography
} from '@mui/material';
import CandidateSummaryGenerator from './CandidateSummaryGenerator';
import MultipleCandidatesGenerator from './MultipleCandidatesGenerator';

const CustomColors = {
    MidnightBlue: '#191970',
    UIGrey100: '#f5f5f5',
};
const Spacing = { Large: 3 };

const MainGenerator = () => {
    const [currentTab, setCurrentTab] = useState(0);

    const handleTabChange = (event, newValue) => {
        setCurrentTab(newValue);
    };

    return (
        <Box sx={{ mx: 'auto', p: Spacing.Large }}>
            <Typography 
                variant="h2" 
                sx={{ 
                    mb: Spacing.Large, 
                    color: CustomColors.MidnightBlue,
                    textAlign: 'center'
                }}
            >
                Candidate Summary Generator
            </Typography>
            
            <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
                <Tabs 
                    value={currentTab} 
                    onChange={handleTabChange} 
                    centered
                    sx={{
                        '& .MuiTabs-indicator': {
                            backgroundColor: CustomColors.MidnightBlue,
                        },
                    }}
                >
                    <Tab 
                        label="Single Candidate" 
                        sx={{ 
                            fontWeight: 600,
                            '&.Mui-selected': {
                                color: CustomColors.MidnightBlue,
                            }
                        }} 
                    />
                    <Tab 
                        label="Multiple Candidates" 
                        sx={{ 
                            fontWeight: 600,
                            '&.Mui-selected': {
                                color: CustomColors.MidnightBlue,
                            }
                        }} 
                    />
                </Tabs>
            </Box>
            
            {currentTab === 0 && <CandidateSummaryGenerator />}
            {currentTab === 1 && <MultipleCandidatesGenerator />}
        </Box>
    );
};

export default MainGenerator;