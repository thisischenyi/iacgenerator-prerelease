import { useEffect, useState } from 'react';
import { 
  Box, 
  Button, 
  Container, 
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton, 
  Paper, 
  Switch, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  TextField,
  Typography,
  Chip,
  MenuItem,
  CircularProgress
} from '@mui/material';
import { 
  Add as AddIcon, 
  Delete as DeleteIcon, 
  Edit as EditIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { usePolicyStore, type Policy } from '../store/policyStore';

export default function PolicyPage() {
  const { policies, isLoading, fetchPolicies, createPolicy, updatePolicy, togglePolicy, deletePolicy } = usePolicyStore();
  const [open, setOpen] = useState(false);
  const [editingPolicy, setEditingPolicy] = useState<Policy | null>(null);
  const [newPolicy, setNewPolicy] = useState<Partial<Policy>>({
    name: '',
    description: '',
    natural_language_rule: '',
    cloud_platform: 'all',
    severity: 'error',
    enabled: true
  });

  useEffect(() => {
    fetchPolicies();
  }, [fetchPolicies]);

  const handleOpen = () => setOpen(true);
  const handleClose = () => {
    setOpen(false);
    setEditingPolicy(null);
    setNewPolicy({
      name: '',
      description: '',
      natural_language_rule: '',
      cloud_platform: 'all',
      severity: 'error',
      enabled: true
    });
  };

  const handleEditOpen = (policy: Policy) => {
    setEditingPolicy(policy);
    setNewPolicy({
      name: policy.name,
      description: policy.description,
      natural_language_rule: policy.natural_language_rule,
      cloud_platform: policy.cloud_platform,
      severity: policy.severity,
      enabled: policy.enabled
    });
    setOpen(true);
  };

  const handleSubmit = async () => {
    if (editingPolicy) {
      await updatePolicy(editingPolicy.id, newPolicy);
    } else {
      await createPolicy(newPolicy);
    }
    handleClose();
  };

  const getSeverityColor = (severity: string) => {
    return severity === 'error' ? 'error' : 'warning';
  };

  const getPlatformLabel = (platform: string) => {
    switch (platform) {
      case 'aws': return 'AWS';
      case 'azure': return 'Azure';
      default: return 'All Platforms';
    }
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" fontWeight="bold" color="primary">
          Security Policies
        </Typography>
        <Box>
          <Button 
            startIcon={<RefreshIcon />} 
            onClick={() => fetchPolicies()} 
            sx={{ mr: 1 }}
          >
            Refresh
          </Button>
          <Button 
            variant="contained" 
            startIcon={<AddIcon />} 
            onClick={handleOpen}
          >
            Add Policy
          </Button>
        </Box>
      </Box>

      {isLoading && policies.length === 0 ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <TableContainer component={Paper} sx={{ borderRadius: 2 }}>
          <Table>
            <TableHead sx={{ bgcolor: '#f5f5f5' }}>
              <TableRow>
                <TableCell width="50">Status</TableCell>
                <TableCell>Policy Name</TableCell>
                <TableCell>Rule Description</TableCell>
                <TableCell width="120">Platform</TableCell>
                <TableCell width="100">Severity</TableCell>
                <TableCell width="100" align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {policies.map((policy) => (
                <TableRow key={policy.id} hover>
                  <TableCell>
                    <Switch 
                      checked={policy.enabled} 
                      onChange={(e) => togglePolicy(policy.id, e.target.checked)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="subtitle2" fontWeight="bold">
                      {policy.name}
                    </Typography>
                    {policy.description && (
                      <Typography variant="caption" color="text.secondary">
                        {policy.description}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ 
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden'
                    }}>
                      {policy.natural_language_rule}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={getPlatformLabel(policy.cloud_platform)} 
                      size="small" 
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={policy.severity} 
                      color={getSeverityColor(policy.severity)} 
                      size="small" 
                    />
                  </TableCell>
                  <TableCell align="center">
                    <IconButton size="small" onClick={() => handleEditOpen(policy)} sx={{ mr: 0.5 }}>
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton size="small" onClick={() => deletePolicy(policy.id)}>
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
              {policies.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                    <Typography color="text.secondary">No policies found. Create one to get started.</Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Create/Edit Policy Dialog */}
      <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
        <DialogTitle>{editingPolicy ? 'Edit Security Policy' : 'Add New Security Policy'}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              label="Policy Name"
              fullWidth
              value={newPolicy.name}
              onChange={(e) => setNewPolicy({ ...newPolicy, name: e.target.value })}
            />
            <TextField
              label="Description"
              fullWidth
              multiline
              rows={2}
              value={newPolicy.description}
              onChange={(e) => setNewPolicy({ ...newPolicy, description: e.target.value })}
            />
            <TextField
              label="Rule (Natural Language)"
              fullWidth
              multiline
              rows={3}
              placeholder="e.g., S3 buckets must not have public access enabled"
              value={newPolicy.natural_language_rule}
              onChange={(e) => setNewPolicy({ ...newPolicy, natural_language_rule: e.target.value })}
              helperText="The AI will interpret this rule to validate resources."
            />
            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                select
                label="Platform"
                fullWidth
                value={newPolicy.cloud_platform}
                onChange={(e) => setNewPolicy({ ...newPolicy, cloud_platform: e.target.value as any })}
              >
                <MenuItem value="all">All Platforms</MenuItem>
                <MenuItem value="aws">AWS</MenuItem>
                <MenuItem value="azure">Azure</MenuItem>
              </TextField>
              <TextField
                select
                label="Severity"
                fullWidth
                value={newPolicy.severity}
                onChange={(e) => setNewPolicy({ ...newPolicy, severity: e.target.value as any })}
              >
                <MenuItem value="error">Error</MenuItem>
                <MenuItem value="warning">Warning</MenuItem>
              </TextField>
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>Cancel</Button>
          <Button onClick={handleSubmit} variant="contained" disabled={!newPolicy.name || !newPolicy.natural_language_rule}>
            {editingPolicy ? 'Update Policy' : 'Create Policy'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}
