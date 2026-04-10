import { useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Container,
  Divider,
  Paper,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { authService } from '../services/api';
import { useAuthStore } from '../store/authStore';

export default function LoginPage() {
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);
  const register = useAuthStore((s) => s.register);
  const loading = useAuthStore((s) => s.loading);
  const error = useAuthStore((s) => s.error);
  const clearError = useAuthStore((s) => s.clearError);

  const [tab, setTab] = useState(0);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');

  const submit = async () => {
    clearError();
    try {
      if (tab === 0) {
        await login(email, password);
      } else {
        await register(email, password, fullName);
      }
      navigate('/');
    } catch {
      // Error state is already set in store and rendered by Alert.
    }
  };

  return (
    <Container maxWidth="sm" sx={{ py: 8 }}>
      <Paper elevation={2} sx={{ p: 4 }}>
        <Typography variant="h5" fontWeight={700} mb={1}>
          IaC4 Sign In
        </Typography>
        <Typography variant="body2" color="text.secondary" mb={3}>
          Multi-user login with local account, Google, or Microsoft.
        </Typography>

        <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
          <Tab label="Login" />
          <Tab label="Register" />
        </Tabs>

        <Stack spacing={2}>
          {tab === 1 && (
            <TextField
              label="Full Name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          )}
          <TextField
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <TextField
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && <Alert severity="error">{error}</Alert>}
          <Button variant="contained" onClick={submit} disabled={loading}>
            {tab === 0 ? 'Login' : 'Create Account'}
          </Button>
        </Stack>

        <Divider sx={{ my: 3 }}>or</Divider>

        <Stack spacing={1.5}>
          <Button
            variant="outlined"
            onClick={() => {
              window.location.href = authService.getGoogleLoginUrl();
            }}
          >
            Continue with Google
          </Button>
          <Button
            variant="outlined"
            onClick={() => {
              window.location.href = authService.getMicrosoftLoginUrl();
            }}
          >
            Continue with Microsoft
          </Button>
        </Stack>

        <Box mt={3}>
          <Typography variant="caption" color="text.secondary">
            OAuth callback URL: `/auth/callback`
          </Typography>
        </Box>
      </Paper>
    </Container>
  );
}
