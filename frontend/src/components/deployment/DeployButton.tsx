import { useState } from 'react';
import {
  Button,
  Box,
  CircularProgress,
  Alert,
  Typography,
} from '@mui/material';
import {
  RocketLaunch as DeployIcon,
  CheckCircle as SuccessIcon,
} from '@mui/icons-material';
import EnvironmentDialog from './EnvironmentDialog';
import PlanProgressDialog from './PlanProgressDialog';
import PlanPreviewDialog from './PlanPreviewDialog';
import DeploymentResultDialog from './DeploymentResultDialog';
import { useDeploymentStore } from '../../store/deploymentStore';
import { useChatStore } from '../../store/chatStore';
import type { DeploymentStatusType } from '../../services/api';

interface DeployButtonProps {
  codeBlocks: Array<{
    filename: string;
    content: string;
    language: string;
  }>;
}

type DeploymentPhase = 'idle' | 'selecting' | 'planning' | 'previewing' | 'applying' | 'complete';

export default function DeployButton({ codeBlocks }: DeployButtonProps) {
  const { currentSessionId } = useChatStore();
  const {
    planResponse,
    applyResponse,
    deploymentError,
    runPlan,
    runApply,
    clearDeployment,
  } = useDeploymentStore();

  const [phase, setPhase] = useState<DeploymentPhase>('idle');
  const [environmentDialogOpen, setEnvironmentDialogOpen] = useState(false);
  const [progressDialogOpen, setProgressDialogOpen] = useState(false);
  const [planDialogOpen, setPlanDialogOpen] = useState(false);
  const [resultDialogOpen, setResultDialogOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Convert code blocks to terraform code map
  const getTerraformCode = (): Record<string, string> => {
    const codeMap: Record<string, string> = {};
    codeBlocks.forEach((block) => {
      // Only include .tf files
      if (block.filename.endsWith('.tf')) {
        codeMap[block.filename] = block.content;
      }
    });
    return codeMap;
  };

  const handleDeployClick = () => {
    console.log(`[UI: Deploy] Deploy button clicked`);
    setError(null);
    clearDeployment();
    setEnvironmentDialogOpen(true);
    setPhase('selecting');
    console.log(`[UI: Deploy] Environment dialog opened`);
  };

  const handleEnvironmentSelect = async (environmentId: number) => {
    console.log(`[UI: Deploy] Environment selected: environmentId=${environmentId}, sessionId=${currentSessionId}`);
    if (!currentSessionId) {
      console.error(`[UI: Deploy] No current session ID`);
      setError('没有活动的会话');
      return;
    }

    setEnvironmentDialogOpen(false);
    setProgressDialogOpen(true);
    setPhase('planning');
    setError(null);

    try {
      const terraformCode = getTerraformCode();
      console.log(`[UI: Deploy] Terraform code collected: ${Object.keys(terraformCode).length} files`);
      console.log(`[UI: Deploy] Files: ${Object.keys(terraformCode).join(', ')}`);
      
      if (Object.keys(terraformCode).length === 0) {
        console.error(`[UI: Deploy] No valid Terraform files found`);
        setError('没有找到有效的 Terraform 文件');
        setProgressDialogOpen(false);
        setPhase('idle');
        return;
      }

      console.log(`[UI: Deploy] Calling runPlan...`);
      await runPlan(currentSessionId, environmentId, terraformCode);
      console.log(`[UI: Deploy] runPlan completed successfully`);
      setProgressDialogOpen(false);
      setPhase('previewing');
      setPlanDialogOpen(true);
      console.log(`[UI: Deploy] Plan dialog opened`);
    } catch (err: unknown) {
      console.error(`[UI: Deploy] runPlan failed:`, err);
      const errorObj = err as { response?: { data?: { detail?: string | { message?: string; error?: string } } } };
      const detail = errorObj.response?.data?.detail;
      let msg = '执行 Plan 失败';

      if (typeof detail === 'string') {
        msg = detail;
      } else if (detail && typeof detail === 'object') {
        msg = detail.message || msg;
        if (detail.error) {
          msg += `: ${detail.error}`;
        }
      }
      
      console.error(`[UI: Deploy] Error message: ${msg}`);
      setError(msg);
      setProgressDialogOpen(false);
      setPhase('idle');
    }
  };

  const handleConfirmApply = async () => {
    console.log(`[UI: Deploy] Confirm apply clicked`);
    if (!planResponse?.deployment_id) {
      console.error(`[UI: Deploy] No deployment_id in planResponse`);
      setError('没有有效的部署计划');
      return;
    }

    console.log(`[UI: Deploy] Starting apply for deployment_id: ${planResponse.deployment_id}`);
    setPhase('applying');
    setError(null);

    try {
      console.log(`[UI: Deploy] Calling runApply...`);
      await runApply(planResponse.deployment_id);
      console.log(`[UI: Deploy] runApply completed successfully`);
      setPhase('complete');
      setPlanDialogOpen(false);
      setResultDialogOpen(true);
      console.log(`[UI: Deploy] Dialog switched to result view`);
    } catch (err: unknown) {
      console.error(`[UI: Deploy] runApply failed:`, err);
      const errorObj = err as { response?: { data?: { detail?: string } } };
      const errorMsg = errorObj.response?.data?.detail || '部署失败';
      console.error(`[UI: Deploy] Error message: ${errorMsg}`);
      setError(errorMsg);
      setPhase('previewing'); // Stay on preview to show error
    }
  };

  const handleClose = () => {
    setEnvironmentDialogOpen(false);
    setProgressDialogOpen(false);
    setPlanDialogOpen(false);
    setResultDialogOpen(false);
    setPhase('idle');
    setError(null);
    clearDeployment();
  };

  const getButtonContent = () => {
    switch (phase) {
      case 'planning':
        return (
          <>
            <CircularProgress size={16} sx={{ mr: 1 }} />
            正在生成 Plan...
          </>
        );
      case 'applying':
        return (
          <>
            <CircularProgress size={16} sx={{ mr: 1 }} />
            正在部署...
          </>
        );
      case 'complete':
        return (
          <>
            <SuccessIcon sx={{ mr: 1 }} />
            部署完成
          </>
        );
      default:
        return (
          <>
            <DeployIcon sx={{ mr: 1 }} />
            部署到云环境
          </>
        );
    }
  };

  // Only show if there are .tf files
  const hasTerraformFiles = codeBlocks.some((block) =>
    block.filename.endsWith('.tf')
  );

  if (!hasTerraformFiles) {
    return null;
  }

  return (
    <Box sx={{ mt: 2 }}>
      {error && (
        <Alert severity="error" sx={{ mb: 1 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Button
        variant="contained"
        color="success"
        onClick={handleDeployClick}
        disabled={phase === 'planning' || phase === 'applying'}
        startIcon={getButtonContent()}
        sx={{
          textTransform: 'none',
          fontWeight: 500,
        }}
      >
        {phase === 'idle' && '部署到云环境'}
      </Button>

      {phase === 'complete' && (
        <Typography
          variant="caption"
          color="success.main"
          sx={{ display: 'block', mt: 0.5 }}
        >
          资源已成功创建
        </Typography>
      )}

      <EnvironmentDialog
        open={environmentDialogOpen}
        onClose={handleClose}
        onSelect={handleEnvironmentSelect}
      />

      <PlanProgressDialog
        open={progressDialogOpen}
        error={error}
      />

      <PlanPreviewDialog
        open={planDialogOpen}
        onClose={handleClose}
        onConfirmApply={handleConfirmApply}
        planOutput={planResponse?.plan_output || ''}
        planSummary={planResponse?.plan_summary || null}
        status={(planResponse?.status || 'pending') as DeploymentStatusType}
        isApplying={phase === 'applying'}
        applyError={deploymentError}
      />

      <DeploymentResultDialog
        open={resultDialogOpen}
        onClose={handleClose}
        applyOutput={applyResponse?.apply_output || ''}
        terraformOutputs={applyResponse?.terraform_outputs || null}
        status={(applyResponse?.status || 'pending') as DeploymentStatusType}
        errorMessage={applyResponse?.error_message || null}
      />
    </Box>
  );
}
