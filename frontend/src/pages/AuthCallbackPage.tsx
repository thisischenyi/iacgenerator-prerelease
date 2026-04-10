import { useEffect, useState } from 'react';
import { Alert, Box, CircularProgress, Container, Paper, Typography } from '@mui/material';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

export default function AuthCallbackPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const setTokenFromOAuth = useAuthStore((s) => s.setTokenFromOAuth);
  const error = useAuthStore((s) => s.error);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = params.get('token');
    if (!token) {
      navigate('/login', { replace: true });
      return;
    }
    setTokenFromOAuth(token)
      .then(() => navigate('/', { replace: true }))
      .catch(() => setLoading(false));
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
