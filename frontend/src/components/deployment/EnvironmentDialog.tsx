import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Box,
  Typography,
  List,
  ListItemButton,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Chip,
  Divider,
  Alert,
  FormControlLabel,
  Switch,
  Tabs,
  Tab,
  CircularProgress,
} from '@mui/material';
import {
  Delete as DeleteIcon,
  Add as AddIcon,
  Cloud as CloudIcon,
} from '@mui/icons-material';
import { useDeploymentStore } from '../../store/deploymentStore';
import type { CloudPlatform, DeploymentEnvironmentCreate } from '../../services/api';

interface EnvironmentDialogProps {
  open: boolean;
  onClose: () => void;
  onSelect: (environmentId: number) => void;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && <Box sx={{ pt: 2 }}>{children}</Box>}
    </div>
  );
}

const initialFormState: DeploymentEnvironmentCreate = {
  name: '',
  description: '',
  cloud_platform: 'aws',
  aws_access_key_id: '',
  aws_secret_access_key: '',
  aws_region: 'us-east-1',
  azure_subscription_id: '',
  azure_tenant_id: '',
  azure_client_id: '',
  azure_client_secret: '',
  is_default: false,
};

export default function EnvironmentDialog({
  open,
  onClose,
  onSelect,
}: EnvironmentDialogProps) {
  const {
    environments,
    environmentsLoading,
    environmentsError,
    fetchEnvironments,
    createEnvironment,
    deleteEnvironment,
  } = useDeploymentStore();

  const [tabValue, setTabValue] = useState(0);
  const [formData, setFormData] = useState<DeploymentEnvironmentCreate>(initialFormState);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      fetchEnvironments();
    }
  }, [open, fetchEnvironments]);

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    setFormError(null);
  };

  const handleFormChange = (field: keyof DeploymentEnvironmentCreate, value: string | boolean) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleCreateEnvironment = async () => {
    if (!formData.name.trim()) {
      setFormError('环境名称不能为空');
      return;
    }

    if (formData.cloud_platform === 'aws') {
      if (!formData.aws_access_key_id || !formData.aws_secret_access_key) {
        setFormError('请填写 AWS Access Key 和 Secret Key');
        return;
      }
    } else if (formData.cloud_platform === 'azure') {
      if (
        !formData.azure_subscription_id ||
        !formData.azure_tenant_id ||
        !formData.azure_client_id ||
        !formData.azure_client_secret
      ) {
        setFormError('请填写所有 Azure 凭证信息');
        return;
      }
    }

    setIsSubmitting(true);
    setFormError(null);

    try {
      await createEnvironment(formData);
      setFormData(initialFormState);
      setTabValue(0); // Switch back to list
    } catch (error: unknown) {
      const errorObj = error as { response?: { data?: { detail?: string } } };
      setFormError(errorObj.response?.data?.detail || '创建环境失败');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteEnvironment = async (id: number) => {
    if (window.confirm('确定要删除此环境吗？')) {
      try {
        await deleteEnvironment(id);
      } catch {
        // Error handled in store
      }
    }
  };

  const handleSelectEnvironment = (id: number) => {
    // Only call onSelect - it will handle closing the dialog and opening progress dialog
    onSelect(id);
    // Don't call onClose() here as it would reset all state
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <CloudIcon color="primary" />
          <Typography variant="h6">部署目标环境</Typography>
        </Box>
      </DialogTitle>

      <Box sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="选择环境" />
          <Tab label="新建环境" icon={<AddIcon />} iconPosition="start" />
        </Tabs>
      </Box>

      <DialogContent>
        {environmentsError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {environmentsError}
          </Alert>
        )}

        <TabPanel value={tabValue} index={0}>
          {environmentsLoading ? (
            <Box display="flex" justifyContent="center" p={3}>
              <CircularProgress />
            </Box>
          ) : environments.length === 0 ? (
            <Box textAlign="center" py={4}>
              <Typography color="text.secondary" gutterBottom>
                暂无配置的部署环境
              </Typography>
              <Button
                variant="outlined"
                startIcon={<AddIcon />}
                onClick={() => setTabValue(1)}
              >
                创建新环境
              </Button>
            </Box>
          ) : (
            <List>
              {environments.map((env) => (
                <ListItemButton
                  key={env.id}
                  onClick={() => handleSelectEnvironment(env.id)}
                  sx={{
                    border: 1,
                    borderColor: 'divider',
                    borderRadius: 1,
                    mb: 1,
                    '&:hover': {
                      bgcolor: 'action.hover',
                    },
                  }}
                >
                  <ListItemText
                    primary={
                      <Box display="flex" alignItems="center" gap={1}>
                        {env.name}
                        {env.is_default && (
                          <Chip label="默认" size="small" color="primary" />
                        )}
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Chip
                          label={env.cloud_platform.toUpperCase()}
                          size="small"
                          variant="outlined"
                          sx={{ mr: 1 }}
                        />
                        {env.aws_region && (
                          <Typography variant="caption" color="text.secondary">
                            Region: {env.aws_region}
                          </Typography>
                        )}
                        {env.description && (
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{ mt: 0.5 }}
                          >
                            {env.description}
                          </Typography>
                        )}
                      </Box>
                    }
                  />
                  <ListItemSecondaryAction>
                    <IconButton
                      edge="end"
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteEnvironment(env.id);
                      }}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </ListItemSecondaryAction>
                </ListItemButton>
              ))}
            </List>
          )}
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          {formError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {formError}
            </Alert>
          )}

          <Box display="flex" flexDirection="column" gap={2}>
            <TextField
              label="环境名称"
              value={formData.name}
              onChange={(e) => handleFormChange('name', e.target.value)}
              required
              fullWidth
            />

            <TextField
              label="描述"
              value={formData.description}
              onChange={(e) => handleFormChange('description', e.target.value)}
              multiline
              rows={2}
              fullWidth
            />

            <FormControl fullWidth>
              <InputLabel>云平台</InputLabel>
              <Select
                value={formData.cloud_platform}
                label="云平台"
                onChange={(e) =>
                  handleFormChange('cloud_platform', e.target.value as CloudPlatform)
                }
              >
                <MenuItem value="aws">AWS</MenuItem>
                <MenuItem value="azure">Azure</MenuItem>
              </Select>
            </FormControl>

            <Divider sx={{ my: 1 }} />

            {formData.cloud_platform === 'aws' && (
              <>
                <Typography variant="subtitle2" color="text.secondary">
                  AWS 凭证
                </Typography>
                <TextField
                  label="Access Key ID"
                  value={formData.aws_access_key_id}
                  onChange={(e) => handleFormChange('aws_access_key_id', e.target.value)}
                  required
                  fullWidth
                />
                <TextField
                  label="Secret Access Key"
                  type="password"
                  value={formData.aws_secret_access_key}
                  onChange={(e) =>
                    handleFormChange('aws_secret_access_key', e.target.value)
                  }
                  required
                  fullWidth
                />
                <FormControl fullWidth>
                  <InputLabel>Region</InputLabel>
                  <Select
                    value={formData.aws_region}
                    label="Region"
                    onChange={(e) => handleFormChange('aws_region', e.target.value)}
                  >
                    <MenuItem value="us-east-1">US East (N. Virginia)</MenuItem>
                    <MenuItem value="us-west-2">US West (Oregon)</MenuItem>
                    <MenuItem value="eu-west-1">EU (Ireland)</MenuItem>
                    <MenuItem value="ap-northeast-1">Asia Pacific (Tokyo)</MenuItem>
                    <MenuItem value="ap-southeast-1">Asia Pacific (Singapore)</MenuItem>
                  </Select>
                </FormControl>
              </>
            )}

            {formData.cloud_platform === 'azure' && (
              <>
                <Typography variant="subtitle2" color="text.secondary">
                  Azure 凭证
                </Typography>
                <TextField
                  label="Subscription ID"
                  value={formData.azure_subscription_id}
                  onChange={(e) =>
                    handleFormChange('azure_subscription_id', e.target.value)
                  }
                  required
                  fullWidth
                />
                <TextField
                  label="Tenant ID"
                  value={formData.azure_tenant_id}
                  onChange={(e) => handleFormChange('azure_tenant_id', e.target.value)}
                  required
                  fullWidth
                />
                <TextField
                  label="Client ID"
                  value={formData.azure_client_id}
                  onChange={(e) => handleFormChange('azure_client_id', e.target.value)}
                  required
                  fullWidth
                />
                <TextField
                  label="Client Secret"
                  type="password"
                  value={formData.azure_client_secret}
                  onChange={(e) =>
                    handleFormChange('azure_client_secret', e.target.value)
                  }
                  required
                  fullWidth
                />
              </>
            )}

            <FormControlLabel
              control={
                <Switch
                  checked={formData.is_default}
                  onChange={(e) => handleFormChange('is_default', e.target.checked)}
                />
              }
              label="设为默认环境"
            />
          </Box>
        </TabPanel>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>取消</Button>
        {tabValue === 1 && (
          <Button
            variant="contained"
            onClick={handleCreateEnvironment}
            disabled={isSubmitting}
          >
            {isSubmitting ? <CircularProgress size={20} /> : '创建环境'}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
