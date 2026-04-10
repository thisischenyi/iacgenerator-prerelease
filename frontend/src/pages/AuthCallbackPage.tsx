import { useEffect, useState } from 'react';
import { Alert, Box, CircularProgress, Container, Paper, Typography } from '@mui/material';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

const exchangedOAuthCodes = new Set<string>();

export default function AuthCallbackPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const setTokenFromOAuth = useAuthStore((s) => s.setTokenFromOAuth);
  const error = useAuthStore((s) => s.error);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const code = params.get('code');
    if (!code) {
      navigate('/login', { replace: true });
      return;
    }
    if (exchangedOAuthCodes.has(code)) {
      return;
    }
    exchangedOAuthCodes.add(code);
    // Exchange the one-time code for a JWT via a protected POST endpoint
    setTokenFromOAuth(code)
      .then(() => navigate('/', { replace: true }))
      .catch(() => {
        exchangedOAuthCodes.delete(code);
        setLoading(false);
      });
  }, [navigate, params, setTokenFromOAuth]);

  return (
    <Container maxWidth="sm" sx={{ py: 8 }}>
      <Paper sx={{ p: 4 }}>
        <Box display="flex" flexDirection="column" alignItems="center" gap={2}>
          {loading && !error && <CircularProgress size={28} />}
          <Typography variant="h6">
            {error ? 'Sign-in failed' : 'Completing sign-in...'}
          </Typography>
          {error && <Alert severity="error">{error}</Alert>}
        </Box>
      </Paper>
    </Container>
  );
}
