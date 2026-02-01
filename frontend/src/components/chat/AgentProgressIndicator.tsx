import { Box, Typography, Stepper, Step, StepLabel, CircularProgress } from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  RadioButtonUnchecked as PendingIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';

// Agent types matching backend
export type AgentType =
  | 'input_parser'
  | 'information_collector'
  | 'compliance_checker'
  | 'code_generator'
  | 'code_reviewer';

export interface AgentProgress {
  agent: AgentType;
  agent_name: string;
  agent_description: string;
  status: 'pending' | 'started' | 'completed' | 'failed';
  message?: string;
}

// Display names for agents
const AGENT_DISPLAY_CONFIG: Record<AgentType, { name: string; description: string }> = {
  input_parser: { name: '解析输入', description: '正在分析您的需求...' },
  information_collector: { name: '收集信息', description: '正在收集资源信息...' },
  compliance_checker: { name: '合规检查', description: '正在检查安全策略合规性...' },
  code_generator: { name: '生成代码', description: '正在生成 Terraform 代码...' },
  code_reviewer: { name: '代码审查', description: '正在审查生成的代码...' },
};

// Ordered list of agents in workflow
const AGENT_ORDER: AgentType[] = [
  'input_parser',
  'information_collector',
  'compliance_checker',
  'code_generator',
  'code_reviewer',
];

interface AgentProgressIndicatorProps {
  currentAgent?: AgentType | null;
  completedAgents: AgentType[];
  failedAgent?: AgentType | null;
  currentMessage?: string;
  isLoading: boolean;
}

export default function AgentProgressIndicator({
  currentAgent,
  completedAgents,
  failedAgent,
  currentMessage,
  isLoading,
}: AgentProgressIndicatorProps) {
  // Always show when loading - even if no progress events received yet
  if (!isLoading) {
    return null;
  }

  const getStepStatus = (agent: AgentType): 'completed' | 'active' | 'failed' | 'pending' => {
    if (failedAgent === agent) return 'failed';
    if (completedAgents.includes(agent)) return 'completed';
    if (currentAgent === agent) return 'active';
    return 'pending';
  };

  const getStepIcon = (agent: AgentType) => {
    const status = getStepStatus(agent);
    switch (status) {
      case 'completed':
        return <CheckCircleIcon color="success" />;
      case 'active':
        return <CircularProgress size={20} />;
      case 'failed':
        return <ErrorIcon color="error" />;
      default:
        return <PendingIcon color="disabled" />;
    }
  };

  // Find current step index
  const activeStep = currentAgent ? AGENT_ORDER.indexOf(currentAgent) : -1;

  return (
    <Box
      sx={{
        width: '100%',
        py: 2,
        px: 3,
        bgcolor: 'background.paper',
        borderRadius: 2,
        mb: 2,
        boxShadow: 1,
      }}
    >
      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
        AI 处理进度
      </Typography>
      
      <Stepper activeStep={activeStep} alternativeLabel>
        {AGENT_ORDER.map((agent) => {
          const config = AGENT_DISPLAY_CONFIG[agent];
          const status = getStepStatus(agent);
          
          return (
            <Step key={agent} completed={status === 'completed'}>
              <StepLabel
                icon={getStepIcon(agent)}
                error={status === 'failed'}
                sx={{
                  '& .MuiStepLabel-label': {
                    fontSize: '0.75rem',
                    mt: 0.5,
                  },
                }}
              >
                {config.name}
              </StepLabel>
            </Step>
          );
        })}
      </Stepper>

      {(currentAgent || currentMessage) && (
        <Typography
          variant="body2"
          color="text.secondary"
          align="center"
          sx={{ mt: 2, fontStyle: 'italic' }}
        >
          {currentMessage || (currentAgent ? AGENT_DISPLAY_CONFIG[currentAgent]?.description : '')}
        </Typography>
      )}
    </Box>
  );
}
