import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
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
  Edit as EditIcon,
  Add as AddIcon,
  Cloud as CloudIcon,
} from '@mui/icons-material';
import { useDeploymentStore } from '../../store/deploymentStore';
import type {
  CloudPlatform,
  DeploymentEnvironmentCreate,
} from '../../services/api';
import { deploymentService } from '../../services/api';
import {
  buildEnvironmentFormStateForEdit,
  buildEnvironmentUpdatePayload,
  initialEnvironmentFormState,
} from './environmentDialogHelpers';

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
    updateEnvironment,
    deleteEnvironment,
  } = useDeploymentStore();

  const [tabValue, setTabValue] = useState(0);
  const [formData, setFormData] = useState<DeploymentEnvironmentCreate>(
    initialEnvironmentFormState
  );
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingEdit, setIsLoadingEdit] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);
  const [editingEnvironment, setEditingEnvironment] =
    useState<Awaited<
      ReturnType<typeof deploymentService.getEnvironment>
    > | null>(null);

  const isEditing = editingEnvironment !== null;

  useEffect(() => {
    if (open) {
      void fetchEnvironments();
    } else {
      setTabValue(0);
      setFormData(initialEnvironmentFormState);
      setFormError(null);
      setIsSubmitting(false);
      setIsLoadingEdit(false);
      setDeleteConfirmId(null);
      setEditingEnvironment(null);
    }
  }, [open, fetchEnvironments]);

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    setFormError(null);
    if (newValue === 1 && !editingEnvironment) {
      setFormData(initialEnvironmentFormState);
    }
  };

  const handleFormChange = (field: keyof DeploymentEnvironmentCreate, value: string | boolean) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleStartCreate = () => {
    setEditingEnvironment(null);
    setFormData(initialEnvironmentFormState);
    setFormError(null);
    setTabValue(1);
  };

  const handleStartEdit = async (environmentId: number) => {
    setIsLoadingEdit(true);
    setFormError(null);
    try {
      const environment = await deploymentService.getEnvironment(environmentId);
      setEditingEnvironment(environment);
      setFormData(buildEnvironmentFormStateForEdit(environment));
      setTabValue(1);
    } catch (error: unknown) {
      const errorObj = error as { response?: { data?: { detail?: string } } };
      setFormError(errorObj.response?.data?.detail || '加载环境详情失败');
    } finally {
      setIsLoadingEdit(false);
    }
  };

  const handleSaveEnvironment = async () => {
    if (!formData.name.trim()) {
      setFormError('环境名称不能为空');
      return;
    }

    if (!isEditing && formData.cloud_platform === 'aws') {
      if (!formData.aws_access_key_id || !formData.aws_secret_access_key) {
        setFormError('请填写 AWS Access Key 和 Secret Key');
        return;
      }
    } else if (!isEditing && formData.cloud_platform === 'azure') {
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
      if (editingEnvironment) {
        await updateEnvironment(
          editingEnvironment.id,
          buildEnvironmentUpdatePayload(formData, editingEnvironment)
        );
      } else {
        await createEnvironment({
          ...formData,
          name: formData.name.trim(),
          description: formData.description?.trim() ?? '',
        });
      }
      setEditingEnvironment(null);
      setFormData(initialEnvironmentFormState);
      setTabValue(0); // Switch back to list
    } catch (error: unknown) {
      const errorObj = error as { response?: { data?: { detail?: string } } };
      setFormError(
        errorObj.response?.data?.detail ||
          (editingEnvironment ? '更新环境失败' : '创建环境失败')
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteEnvironment = async (id: number) => {
    setDeleteConfirmId(id);
  };

  const handleConfirmDelete = async () => {
    if (deleteConfirmId !== null) {
      try {
        await deleteEnvironment(deleteConfirmId);
      } catch {
        // Error handled in store
      }
      setDeleteConfirmId(null);
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
          <Tab
            label={isEditing ? '编辑环境' : '新建环境'}
            icon={<AddIcon />}
            iconPosition="start"
          />
        </Tabs>
      </Box>

      <DialogContent>
        {environmentsError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {environmentsError}
          </Alert>
        )}

        {tabValue === 0 && formError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {formError}
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
                onClick={handleStartCreate}
              >
                创建新环境
              </Button>
            </Box>
          ) : (
            <List>
              {environments.map((env) => (
                <ListItemButton
                  key={env.id}
                  disabled={isLoadingEdit}
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
                      disabled={isLoadingEdit}
                      aria-label={`编辑环境 ${env.name}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        void handleStartEdit(env.id);
                      }}
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      edge="end"
                      size="small"
                      disabled={isLoadingEdit}
                      aria-label={`删除环境 ${env.name}`}
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
          {isLoadingEdit ? (
            <Box display="flex" justifyContent="center" p={3}>
              <CircularProgress />
            </Box>
          ) : (
            <>
          {formError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {formError}
            </Alert>
          )}

          {isEditing && (
            <Alert severity="info" sx={{ mb: 2 }}>
              凭证字段留空将保留现有密钥；如需替换，请输入新的凭证值。
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
                disabled={isEditing}
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
                  required={!isEditing}
                  fullWidth
                />
                <TextField
                  label="Secret Access Key"
                  type="password"
                  value={formData.aws_secret_access_key}
                  onChange={(e) =>
                    handleFormChange('aws_secret_access_key', e.target.value)
                  }
                  required={!isEditing}
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
                  required={!isEditing}
                  fullWidth
                />
                <TextField
                  label="Tenant ID"
                  value={formData.azure_tenant_id}
                  onChange={(e) => handleFormChange('azure_tenant_id', e.target.value)}
                  required={!isEditing}
                  fullWidth
                />
                <TextField
                  label="Client ID"
                  value={formData.azure_client_id}
                  onChange={(e) => handleFormChange('azure_client_id', e.target.value)}
                  required={!isEditing}
                  fullWidth
                />
                <TextField
                  label="Client Secret"
                  type="password"
                  value={formData.azure_client_secret}
                  onChange={(e) =>
                    handleFormChange('azure_client_secret', e.target.value)
                  }
                  required={!isEditing}
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
            </>
          )}
        </TabPanel>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>取消</Button>
        {tabValue === 1 && (
          <Button
            variant="contained"
            onClick={handleSaveEnvironment}
            disabled={isSubmitting || isLoadingEdit}
          >
            {isSubmitting ? (
              <CircularProgress size={20} />
            ) : isEditing ? (
              '保存修改'
            ) : (
              '创建环境'
            )}
          </Button>
        )}
      </DialogActions>

      {/* Delete confirmation dialog */}
      <Dialog
        open={deleteConfirmId !== null}
        onClose={() => setDeleteConfirmId(null)}
      >
        <DialogTitle>确认删除</DialogTitle>
        <DialogContent>
          <DialogContentText>确定要删除此环境吗？此操作无法撤销。</DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirmId(null)}>取消</Button>
          <Button onClick={handleConfirmDelete} color="error" variant="contained">
            删除
          </Button>
        </DialogActions>
      </Dialog>
    </Dialog>
  );
}
