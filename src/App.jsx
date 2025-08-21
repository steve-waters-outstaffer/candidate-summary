// src/App.jsx
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, StyledEngineProvider, CssBaseline } from '@mui/material';
import { AuthProvider } from '/src/contexts/AuthContext';
import Dashboard from './components/Dashboard';
import AuthContainer from './components/auth/AuthContainer';
import ProtectedRoute from './components/auth/ProtectedRoute';
import CandidateSummaryGenerator from './components/CandidateSummaryGenerator';
import { theme } from './theme';

function App() {
    return (
        <StyledEngineProvider injectFirst>
            <ThemeProvider theme={theme}>
                <CssBaseline />
                <BrowserRouter>
                    <AuthProvider>
                        <Routes>
                            <Route path="/login" element={<AuthContainer />} />
                            <Route path="/dashboard" element={
                                <ProtectedRoute>
                                    <Dashboard />
                                </ProtectedRoute>
                            } />
                            <Route path="/summary" element={
                                <ProtectedRoute>
                                    <CandidateSummaryGenerator />
                                </ProtectedRoute>
                            } />
                            <Route path="/" element={<Navigate replace to="/dashboard" />} />
                        </Routes>
                    </AuthProvider>
                </BrowserRouter>
            </ThemeProvider>
        </StyledEngineProvider>
    );
}

export default App;