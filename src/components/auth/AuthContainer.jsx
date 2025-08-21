// src/components/auth/AuthContainer.jsx
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { useNavigate, useLocation } from 'react-router-dom';
import {
    Box,
    Paper,
    Typography,
    TextField,
    Button,
    Alert,
    Divider,
    Grid
} from '@mui/material';
import { useAuth } from '../../contexts/AuthContext';
import { CustomColors } from '../../theme';
import GoogleIcon from '@mui/icons-material/Google';

const AuthContainer = () => {
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const { login, register, loginWithGoogle } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();

    // Redirect user after successful login
    const redirectPath = location.state?.from?.pathname || '/dashboard';

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            if (isLogin) {
                await login(email, password);
            } else {
                await register(email, password);
            }
            navigate(redirectPath);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleGoogleSignIn = async () => {
        setError('');
        setLoading(true);

        try {
            await loginWithGoogle();
            navigate(redirectPath);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Box
            sx={{
                minHeight: '100vh',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                bgcolor: CustomColors.UIGrey100
            }}
        >
            <Paper
                elevation={1}
                sx={{
                    p: 4,
                    width: '100%',
                    maxWidth: 450
                }}
            >
                <Typography variant="h3" align="center" gutterBottom mb={3}>
                    {isLogin ? 'Login to Your Account' : 'Create an Account'}
                </Typography>

                {error && (
                    <Alert severity="error" sx={{ mb: 3 }}>
                        {error}
                    </Alert>
                )}

                <Box component="form" onSubmit={handleSubmit}>
                    <TextField
                        fullWidth
                        label="Email"
                        variant="outlined"
                        type="email"
                        margin="normal"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                    />

                    <TextField
                        fullWidth
                        label="Password"
                        variant="outlined"
                        type="password"
                        margin="normal"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                    />

                    <Grid container spacing={2} alignItems="center" sx={{ mt: 2, mb: 3 }}>
                        <Grid item xs>
                            <Button
                                type="submit"
                                variant="contained"
                                color="primary"
                                disabled={loading}
                                fullWidth
                            >
                                {loading ? 'Processing...' : isLogin ? 'Sign In' : 'Sign Up'}
                            </Button>
                        </Grid>
                        <Grid item>
                            <Button
                                type="button"
                                variant="text"
                                color="primary"
                                onClick={() => setIsLogin(!isLogin)}
                            >
                                {isLogin ? 'Create account' : 'Already have an account?'}
                            </Button>
                        </Grid>
                    </Grid>
                </Box>

                <Box position="relative" my={3}>
                    <Divider>
                        <Typography variant="body2" color="text.secondary" sx={{ px: 1 }}>
                            Or continue with
                        </Typography>
                    </Divider>
                </Box>

                <Button
                    fullWidth
                    variant="outlined"
                    startIcon={<GoogleIcon />}
                    onClick={handleGoogleSignIn}
                    disabled={loading}
                    sx={{
                        borderColor: CustomColors.UIGrey400,
                        color: CustomColors.UIGrey800,
                        backgroundColor: CustomColors.White,
                        '&:hover': {
                            borderColor: CustomColors.UIGrey600,
                            backgroundColor: CustomColors.UIGrey100,
                        }
                    }}
                >
                    Sign in with Google
                </Button>
            </Paper>
        </Box>
    );
};

AuthContainer.propTypes = {
    location: PropTypes.object
};

export default AuthContainer;