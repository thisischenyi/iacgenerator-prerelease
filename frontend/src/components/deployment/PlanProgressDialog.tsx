import { useState, useEffect, useRef } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  Box,
  Typography,
  LinearProgress,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  CircularProgress,
} from '@mui/material';
import {
  CloudUpload as CloudIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';

interface PlanProgressDialogProps {
  open: boolean;
  error?: string | null;
}

type StepStatus = 'pending' | 'active' | 'completed' | 'error';

interface PlanStep {
  label: string;
  description: string;
  status: StepStatus;
  duration?: number;
  startTime?: number;
}

const PLAN_STEPS: Omit<PlanStep, 'status' | 'duration' | 'startTime'>[] = [
  { label: '准备部署环境', description: '创建工作目录，写入 Terraform 配置文件' },
  { label: '初始化 Terraform', description: '下载 Provider 插件，初始化后端' },
  { label: '生成执行计划', description: '分析配置，计算资源变更' },
  { label: '解析计划结果', description: '提取变更摘要信息' },
];

export default function PlanProgressDialog({ open, error }: PlanProgressDialogProps) {
  const [activeStep, setActiveStep] = useState(0);
  const [steps, setSteps] = useState<PlanStep[]>(
    PLAN_STEPS.map((s) => ({ ...s, status: 'pending' as StepStatus }))
  );
  const [elapsedTime, setElapsedTime] = useState(0);
  // Track when each step started using a ref to persist across renders
  const stepStartTimesRef = useRef<number[]>([]);

  // Simulate step progression based on typical timing
  useEffect(() => {
    if (!open) {
      // Reset when dialog closes
      setActiveStep(0);
      setSteps(PLAN_STEPS.map((s) => ({ ...s, status: 'pending' as StepStatus })));
      setElapsedTime(0);
      stepStartTimesRef.current = [];
      return;
    }

    const startTime = Date.now();
    stepStartTimesRef.current = [];

    // Step timing simulation (approximate based on typical terraform operations)
    const stepTimings = [1500, 8000, 15000, 2000]; // ms for each step
    let currentStep = 0;

    const advanceStep = () => {
      if (currentStep < PLAN_STEPS.length) {
        const now = Date.now();
        
        setSteps((prev) => {
          const updated = [...prev];
          if (currentStep > 0) {
            // Calculate real duration from when step started to now
            const stepStartTime = stepStartTimesRef.current[currentStep - 1];
            const realDuration = stepStartTime ? (now - stepStartTime) / 1000 : 0;
            updated[currentStep - 1] = {
              ...updated[currentStep - 1],
              status: 'completed',
              duration: realDuration,
            };
          }
          // Record start time for current step
          stepStartTimesRef.current[currentStep] = now;
          updated[currentStep] = { 
            ...updated[currentStep], 
            status: 'active',
            startTime: now,
          };
          return updated;
        });
        setActiveStep(currentStep);

        currentStep++;

        if (currentStep < PLAN_STEPS.length) {
          setTimeout(advanceStep, stepTimings[currentStep - 1]);
        }
      }
    };

    // Start the first step immediately
    advanceStep();

    // Update elapsed time every second
    const timer = setInterval(() => {
      setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);

    return () => {
      clearInterval(timer);
    };
  }, [open]);

  // Handle error state
  useEffect(() => {
    if (error) {
      setSteps((prev) => {
        const updated = [...prev];
        const activeIdx = updated.findIndex((s) => s.status === 'active');
        if (activeIdx >= 0) {
          updated[activeIdx] = { ...updated[activeIdx], status: 'error' };
        }
        return updated;
      });
    }
  }, [error]);

  const formatTime = (seconds: number): string => {
    if (seconds < 60) {
      return `${seconds} 秒`;
    }
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins} 分 ${secs} 秒`;
  };

  const getStepIcon = (status: StepStatus, index: number) => {
    switch (status) {
      case 'completed':
        return <CheckIcon color="success" />;
      case 'active':
        return <CircularProgress size={24} />;
      case 'error':
        return <ErrorIcon color="error" />;
      default:
        return (
          <Box
            sx={{
              width: 24,
              height: 24,
              borderRadius: '50%',
              border: '2px solid',
              borderColor: 'grey.400',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 12,
              color: 'grey.500',
            }}
          >
            {index + 1}
          </Box>
        );
    }
  };

  return (
    <Dialog open={open} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <CloudIcon color="primary" />
          <Typography variant="h6">正在准备部署计划</Typography>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Box sx={{ mb: 3 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
            <Typography variant="body2" color="text.secondary">
              已用时间: {formatTime(elapsedTime)}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              步骤 {activeStep + 1} / {PLAN_STEPS.length}
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={((activeStep + 0.5) / PLAN_STEPS.length) * 100}
            sx={{ height: 8, borderRadius: 4 }}
          />
        </Box>

        <Stepper activeStep={activeStep} orientation="vertical">
          {steps.map((step, index) => (
            <Step key={step.label} completed={step.status === 'completed'}>
              <StepLabel
                error={step.status === 'error'}
                StepIconComponent={() => getStepIcon(step.status, index)}
              >
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography
                    fontWeight={step.status === 'active' ? 600 : 400}
                    color={step.status === 'error' ? 'error' : 'inherit'}
                  >
                    {step.label}
                  </Typography>
                  {step.status === 'completed' && step.duration && (
                    <Typography variant="caption" color="text.secondary">
                      ({step.duration.toFixed(1)}s)
                    </Typography>
                  )}
                </Box>
              </StepLabel>
              <StepContent>
                <Typography variant="body2" color="text.secondary">
                  {step.description}
                </Typography>
                {step.status === 'active' && (
                  <Box sx={{ mt: 1 }}>
                    <LinearProgress sx={{ borderRadius: 2 }} />
                  </Box>
                )}
                {step.status === 'error' && error && (
                  <Typography variant="body2" color="error" sx={{ mt: 1 }}>
                    {error}
                  </Typography>
                )}
              </StepContent>
            </Step>
          ))}
        </Stepper>

        <Box
          sx={{
            mt: 3,
            p: 2,
            bgcolor: 'grey.50',
            borderRadius: 1,
            border: '1px solid',
            borderColor: 'grey.200',
          }}
        >
          <Typography variant="body2" color="text.secondary" textAlign="center">
            Terraform 正在分析您的基础设施配置...
            <br />
            首次运行可能需要下载 Provider 插件，请耐心等待
          </Typography>
        </Box>
      </DialogContent>
    </Dialog>
  );
}
