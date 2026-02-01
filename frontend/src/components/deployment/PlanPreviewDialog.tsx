import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Chip,
  Alert,
  CircularProgress,
  Paper,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { PlanSummary, DeploymentStatusType } from '../../services/api';

interface PlanPreviewDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirmApply: () => void;
  planOutput: string;
  planSummary: PlanSummary | null;
  status: DeploymentStatusType;
  isApplying: boolean;
  applyError: string | null;
}

export default function PlanPreviewDialog({
  open,
  onClose,
  onConfirmApply,
  planOutput,
  planSummary,
  status,
  isApplying,
  applyError,
}: PlanPreviewDialogProps) {
  const isPlanReady = status === 'plan_ready';
  const isApplySuccess = status === 'apply_success';
  const isApplyFailed = status === 'apply_failed';

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Typography variant="h6">Terraform Plan 预览</Typography>
          {planSummary && (
            <Box display="flex" gap={1}>
              <Chip
                icon={<AddIcon />}
                label={`新增 ${planSummary.add}`}
                color="success"
                size="small"
                variant="outlined"
              />
              <Chip
                icon={<EditIcon />}
                label={`变更 ${planSummary.change}`}
                color="warning"
                size="small"
                variant="outlined"
              />
              <Chip
                icon={<DeleteIcon />}
                label={`删除 ${planSummary.destroy}`}
                color="error"
                size="small"
                variant="outlined"
              />
            </Box>
          )}
        </Box>
      </DialogTitle>

      <DialogContent>
        {applyError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {applyError}
          </Alert>
        )}

        {isApplySuccess && (
          <Alert
            severity="success"
            icon={<CheckCircleIcon />}
            sx={{ mb: 2 }}
          >
            部署成功！资源已创建完成。
          </Alert>
        )}

        {isApplyFailed && (
          <Alert severity="error" icon={<ErrorIcon />} sx={{ mb: 2 }}>
            部署失败，请查看输出日志获取详细信息。
          </Alert>
        )}

        <Paper
          variant="outlined"
          sx={{
            maxHeight: '60vh',
            overflow: 'auto',
          }}
        >
          <SyntaxHighlighter
            language="bash"
            style={vscDarkPlus}
            customStyle={{
              margin: 0,
              borderRadius: 0,
              fontSize: '12px',
            }}
            wrapLines
            wrapLongLines
          >
            {planOutput || '无输出内容'}
          </SyntaxHighlighter>
        </Paper>

        {isPlanReady && planSummary && (
          <Alert severity="info" sx={{ mt: 2 }}>
            确认后将创建 {planSummary.add} 个资源
            {planSummary.change > 0 && `，变更 ${planSummary.change} 个资源`}
            {planSummary.destroy > 0 && `，删除 ${planSummary.destroy} 个资源`}
            。此操作不可撤销！
          </Alert>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={isApplying}>
          {isApplySuccess ? '关闭' : '取消'}
        </Button>
        {isPlanReady && !isApplySuccess && (
          <Button
            variant="contained"
            color="primary"
            onClick={onConfirmApply}
            disabled={isApplying}
            startIcon={
              isApplying ? <CircularProgress size={16} color="inherit" /> : null
            }
          >
            {isApplying ? '部署中...' : '确认部署'}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
