import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Alert,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  ExpandMore as ExpandMoreIcon,
} from '@mui/icons-material';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { DeploymentStatusType } from '../../services/api';

interface DeploymentResultDialogProps {
  open: boolean;
  onClose: () => void;
  applyOutput: string;
  terraformOutputs: Record<string, unknown> | null;
  status: DeploymentStatusType;
  errorMessage: string | null;
}

export default function DeploymentResultDialog({
  open,
  onClose,
  applyOutput,
  terraformOutputs,
  status,
  errorMessage,
}: DeploymentResultDialogProps) {
  const isSuccess = status === 'apply_success';
  const isFailed = status === 'apply_failed';

  // Format terraform output value for display
  const formatOutputValue = (value: unknown): string => {
    if (value === null || value === undefined) {
      return 'null';
    }
    if (typeof value === 'object') {
      const obj = value as Record<string, unknown>;
      if (obj.value !== undefined) {
        return formatOutputValue(obj.value);
      }
      return JSON.stringify(value, null, 2);
    }
    return String(value);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          {isSuccess ? (
            <SuccessIcon color="success" />
          ) : isFailed ? (
            <ErrorIcon color="error" />
          ) : null}
          <Typography variant="h6">
            {isSuccess ? '部署成功' : isFailed ? '部署失败' : '部署结果'}
          </Typography>
        </Box>
      </DialogTitle>

      <DialogContent>
        {isSuccess && (
          <Alert severity="success" sx={{ mb: 2 }}>
            所有资源已成功创建！以下是部署输出信息。
          </Alert>
        )}

        {isFailed && (
          <Alert severity="error" sx={{ mb: 2 }}>
            部署过程中发生错误。请查看下方日志获取详细信息。
            {errorMessage && (
              <Typography variant="body2" sx={{ mt: 1 }}>
                {errorMessage}
              </Typography>
            )}
          </Alert>
        )}

        {/* Terraform Outputs */}
        {terraformOutputs && Object.keys(terraformOutputs).length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle1" gutterBottom fontWeight={600}>
              Terraform Outputs
            </Typography>
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>输出名称</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>值</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {Object.entries(terraformOutputs).map(([key, value]) => (
                    <TableRow key={key}>
                      <TableCell
                        sx={{ fontFamily: 'monospace', whiteSpace: 'nowrap' }}
                      >
                        {key}
                      </TableCell>
                      <TableCell>
                        <Typography
                          variant="body2"
                          sx={{
                            fontFamily: 'monospace',
                            wordBreak: 'break-all',
                          }}
                        >
                          {formatOutputValue(value)}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}

        {/* Apply Output Log */}
        <Accordion defaultExpanded={isFailed}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography>执行日志</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Paper
              variant="outlined"
              sx={{
                maxHeight: '40vh',
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
                {applyOutput || '无输出内容'}
              </SyntaxHighlighter>
            </Paper>
          </AccordionDetails>
        </Accordion>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} variant="contained">
          关闭
        </Button>
      </DialogActions>
    </Dialog>
  );
}
