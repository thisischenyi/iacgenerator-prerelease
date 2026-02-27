import { useEffect } from 'react';
import { Alert, Box, CircularProgress, Container, Paper, Typography } from '@mui/material';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

export default function AuthCallbackPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const setTokenFromOAuth = useAuthStore((s) => s.setTokenFromOAuth);
  const error = useAuthStore((s) => s.error);

  useEffect(() => {
    const token = params.get('token');
    if (!token) {
      navigate('/login', { replace: true });
      return;
    }
    setTokenFromOAuth(token)
      .then(() => navigate('/', { replace: true }))
      .catch(() => undefined);
  }, [navigate, params, setTokenFromOAuth]);

  return (
    <Container maxWidth="sm" sx={{ py: 8 }}>
      <Paper sx={{ p: 4 }}>
        <Box display="flex" flexDirection="column" alignItems="center" gap={2}>
          <CircularProgress size={28} />
          <Typography variant="h6">Completing sign-in...</Typography>
          {error && <Alert severity="error">{error}</Alert>}
        </Box>
      </Paper>
    </Container>
  );
}
