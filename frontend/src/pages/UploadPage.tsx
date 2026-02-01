import { useState } from 'react';
import { 
  Box, 
  Button, 
  Container, 
  Grid, 
  Paper, 
  Typography, 
  Card, 
  CardContent, 
  CardActions,
  CircularProgress,
  Alert
} from '@mui/material';
import { 
  CloudUpload as UploadIcon, 
  Download as DownloadIcon
} from '@mui/icons-material';
import { excelService } from '../services/api';
import { useChatStore } from '../store/chatStore';
import { useNavigate } from 'react-router-dom';

export default function UploadPage() {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const { createNewSession } = useChatStore();
  const navigate = useNavigate();

  const handleDownloadTemplate = async (type: 'aws' | 'azure' | 'full') => {
    try {
      const blob = await excelService.downloadTemplate(type);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `iac_template_${type}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      setError('Failed to download template');
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!event.target.files || event.target.files.length === 0) return;
    
    const file = event.target.files[0];
    await processFileUpload(file);
  };

  const processFileUpload = async (file: File) => {
    // Validate file type
    const validExtensions = ['.xlsx', '.xls'];
    const fileExtension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    
    if (!validExtensions.includes(fileExtension)) {
      setError('Invalid file format. Only .xlsx and .xls files are supported.');
      return;
    }
    
    setIsUploading(true);
    setError(null);
    
    try {
      // Create new session for Excel upload
      await createNewSession();
      
      // Upload file
      const result = await excelService.uploadFile(file);
      
      if (result.success) {
        // Prepare a summary message for the chat
        const resourceTypes = result.resource_types?.join(', ') || 'unknown';
        const resourceCount = result.resource_count || 0;
        
        // Navigate to chat first
        navigate('/');
        
        // Then send an automatic message with Excel data context
        // Give navigation time to complete
        setTimeout(async () => {
          const { sendMessageWithProgress } = useChatStore.getState();
          await sendMessageWithProgress(
            `我已上传了一个 Excel 文件，包含 ${resourceCount} 个资源，类型包括：${resourceTypes}。请验证资源、检查合规性并生成 Terraform 代码。`,
            result.resources
          );
        }, 100);
      } else {
        setError(result.errors ? result.errors.join(', ') : 'Upload failed');
      }
    } catch {
      setError('Failed to upload file');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDragEnter = (e: React.DragEvent<HTMLElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLElement>) => {
    e.preventDefault();
    e.stopPropagation();
    // Only set dragging to false if leaving the drop zone itself
    if (e.currentTarget === e.target) {
      setIsDragging(false);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLElement>) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = async (e: React.DragEvent<HTMLElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (isUploading) return;

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const file = files[0];
      await processFileUpload(file);
    }
  };

  return (
    <Container maxWidth="lg">
      <Typography variant="h4" gutterBottom fontWeight="bold" color="primary">
        Excel Upload
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Upload your infrastructure requirements using our Excel templates.
        The AI will parse your file and generate the corresponding Terraform code.
      </Typography>
      
      <Grid container spacing={3} sx={{ mt: 2 }}>
        {/* Templates Section */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              1. Download Template
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Start by downloading one of our standardized Excel templates.
              Each template contains sheets for different resource types.
            </Typography>
            
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 3 }}>
              <Card variant="outlined">
                <CardContent sx={{ pb: 1 }}>
                  <Typography variant="subtitle1" fontWeight="bold">Full Template (AWS & Azure)</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Contains all supported resources for both cloud platforms.
                  </Typography>
                </CardContent>
                <CardActions>
                  <Button 
                    startIcon={<DownloadIcon />} 
                    onClick={() => handleDownloadTemplate('full')}
                  >
                    Download
                  </Button>
                </CardActions>
              </Card>
              
              <Box sx={{ display: 'flex', gap: 2 }}>
                <Button 
                  variant="outlined" 
                  startIcon={<DownloadIcon />}
                  onClick={() => handleDownloadTemplate('aws')}
                  fullWidth
                >
                  AWS Only
                </Button>
                <Button 
                  variant="outlined" 
                  startIcon={<DownloadIcon />}
                  onClick={() => handleDownloadTemplate('azure')}
                  fullWidth
                >
                  Azure Only
                </Button>
              </Box>
            </Box>
          </Paper>
        </Grid>
        
        {/* Upload Section */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              2. Upload Completed File
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Once filled, upload your Excel file here. The AI will validate your
              resources and check for compliance issues.
            </Typography>
            
            <Box<"label">
              component="label"
              sx={{ 
                border: '2px dashed #e0e0e0', 
                borderRadius: 2, 
                p: 5, 
                mt: 3,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                bgcolor: isDragging ? '#e3f2fd' : '#fafafa',
                borderColor: isDragging ? 'primary.main' : '#e0e0e0',
                cursor: 'pointer',
                transition: 'all 0.2s',
                '&:hover': {
                  borderColor: 'primary.main',
                  bgcolor: '#f0f7ff'
                }
              }}
              onDragEnter={handleDragEnter}
              onDragLeave={handleDragLeave}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
            >
              <input
                type="file"
                hidden
                accept=".xlsx,.xls"
                onChange={handleFileUpload}
                disabled={isUploading}
              />
              
              {isUploading ? (
                <CircularProgress size={40} />
              ) : (
                <>
                  <UploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                  <Typography variant="h6" color="text.primary">
                    Click to Upload
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    or drag and drop Excel file here
                  </Typography>
                </>
              )}
            </Box>
            
            {error && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {error}
              </Alert>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
}
