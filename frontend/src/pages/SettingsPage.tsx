import { useState, useEffect } from 'react';
import { 
  Button, 
  Container, 
  Paper, 
  Typography, 
  TextField, 
  Grid,
  Switch,
  FormControlLabel,
  Alert,
  CircularProgress
} from '@mui/material';
import axios from 'axios';

// Since we haven't implemented full LLM config store, we'll do direct API calls here
// In a real app, this would be in a store

export default function SettingsPage() {
  const [config, setConfig] = useState({
    id: null as number | null,
    config_name: 'Default Config',
    api_endpoint: 'https://api.openai.com/v1',
    api_key: '',
    model_name: 'gpt-4',
    temperature: 0.7,
    max_tokens: 4000,
    is_active: true
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      setLoading(true);
      // Fetch active config first
      const response = await axios.get('/api/llm-config?active_only=true');
      if (response.data && response.data.length > 0) {
        const activeConfig = response.data[0];
        // Backend stores these as integers (x100), so we need to divide by 100
        // But checking schema, response model says float. 
        // If backend returns 70 for 0.7, we must divide.
        // Let's safe guard it: if > 2, assume it needs division.
        
        const normalize = (val: number) => (val > 2 ? val / 100 : val);

        setConfig({
          ...activeConfig,
          temperature: normalize(activeConfig.temperature),
          top_p: normalize(activeConfig.top_p),
          frequency_penalty: normalize(activeConfig.frequency_penalty),
          presence_penalty: normalize(activeConfig.presence_penalty),
          api_key: '' // Don't show encrypted API key
        });
      }
    } catch (error) {
      console.error('Error fetching config:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setLoading(true);
      setMessage(null);
      
      // Basic validation
      if (!config.api_key && !config.id) {
        throw new Error('API Key is required for new configuration');
      }
      if (!config.config_name) {
        throw new Error('Config Name is required');
      }

      let response;
      let configId = config.id;

      if (configId) {
        // Update existing config
        // If API key is empty, it will not be updated on backend (kept as is)
        response = await axios.put(`/api/llm-config/${configId}`, config);
      } else {
        // Create new config
        // Basic validation for new config
        if (!config.api_key) {
          throw new Error('API Key is required for new configuration');
        }
        response = await axios.post('/api/llm-config', config);
        configId = response.data.id;
      }

      // Handle activation
      if (config.is_active && configId) {
        await axios.patch(`/api/llm-config/${configId}/activate`);
      }

      setMessage({ type: 'success', text: 'Configuration saved successfully' });
      
      // Refresh config to get latest state (and encrypted key placeholder)
      if (config.is_active) {
          fetchConfig(); 
      } else {
          // If we just saved but didn't activate, we might want to just update local state ID
          setConfig(prev => ({ ...prev, id: configId }));
      }

    } catch (error: any) {
      console.error('Save configuration failed:', error);
      
      let errorMsg = 'Failed to save configuration';
      const detail = error.response?.data?.detail;
      
      if (typeof detail === 'string') {
        errorMsg = detail;
      } else if (Array.isArray(detail)) {
        // Pydantic validation error is an array
        errorMsg = detail.map((e: any) => `${e.loc.join('.')}: ${e.msg}`).join(', ');
      } else if (error.message) {
        errorMsg = error.message;
      }

      setMessage({ 
        type: 'error', 
        text: errorMsg
      });
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field: string, value: any) => {
    setConfig(prev => ({ ...prev, [field]: value }));
  };

  return (
    <Container maxWidth="md">
      <Typography variant="h4" gutterBottom fontWeight="bold" color="primary">
        LLM Settings
      </Typography>
      
      <Paper sx={{ p: 4, mt: 3 }}>
        <Typography variant="h6" gutterBottom>
          Model Configuration
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          Configure the LLM backend for the IaC Generator.
        </Typography>

        {message && (
          <Alert severity={message.type} sx={{ mb: 3 }}>
            {message.text}
          </Alert>
        )}

        <Grid container spacing={3}>
          <Grid size={12}>
            <TextField
              label="Configuration Name"
              fullWidth
              value={config.config_name}
              onChange={(e) => handleChange('config_name', e.target.value)}
            />
          </Grid>
          
          <Grid size={12}>
            <TextField
              label="API Endpoint"
              fullWidth
              value={config.api_endpoint}
              onChange={(e) => handleChange('api_endpoint', e.target.value)}
              placeholder="https://api.openai.com/v1"
            />
          </Grid>
          
          <Grid size={12}>
            <TextField
              label="API Key"
              fullWidth
              type="password"
              value={config.api_key}
              onChange={(e) => handleChange('api_key', e.target.value)}
              placeholder="sk-..."
              helperText="Leave empty to keep existing key"
            />
          </Grid>
          
          <Grid size={12}>
            <TextField
              label="Model Name"
              fullWidth
              value={config.model_name}
              onChange={(e) => handleChange('model_name', e.target.value)}
              placeholder="gpt-4"
            />
          </Grid>
          
          <Grid size={6}>
            <TextField
              label="Temperature"
              fullWidth
              type="number"
              inputProps={{ step: 0.1, min: 0, max: 2 }}
              value={config.temperature}
              onChange={(e) => handleChange('temperature', parseFloat(e.target.value))}
            />
          </Grid>
          
          <Grid size={6}>
            <TextField
              label="Max Tokens"
              fullWidth
              type="number"
              value={config.max_tokens}
              onChange={(e) => handleChange('max_tokens', parseInt(e.target.value))}
            />
          </Grid>
          
          <Grid size={12}>
            <FormControlLabel
              control={
                <Switch
                  checked={config.is_active}
                  onChange={(e) => handleChange('is_active', e.target.checked)}
                />
              }
              label="Set as Active Configuration"
            />
          </Grid>
          
          <Grid size={12}>
            <Button
              variant="contained"
              size="large"
              onClick={handleSave}
              disabled={loading}
              startIcon={loading ? <CircularProgress size={20} /> : null}
            >
              Save Configuration
            </Button>
          </Grid>
        </Grid>
      </Paper>
    </Container>
  );
}
