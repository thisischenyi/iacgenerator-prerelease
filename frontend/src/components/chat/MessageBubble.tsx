import { Box, Paper, Typography, Avatar, useTheme, IconButton, Tooltip } from '@mui/material';
import { Person as PersonIcon, SmartToy as BotIcon, Download as DownloadIcon, ContentCopy as CopyIcon, Check as CheckIcon } from '@mui/icons-material';
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { DeployButton } from '../deployment';

interface MessageBubbleProps {
  message: {
    role: string;
    content: string;
    code_blocks?: Array<{
      filename: string;
      content: string;
      language: string;
    }>;
  };
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const theme = useTheme();
  const isUser = message.role === 'user';
  const [copiedFile, setCopiedFile] = useState<string | null>(null);

  const handleDownload = (filename: string, content: string) => {
    const element = document.createElement('a');
    const file = new Blob([content], {type: 'text/plain'});
    element.href = URL.createObjectURL(file);
    element.download = filename;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const handleCopy = (filename: string, content: string) => {
    navigator.clipboard.writeText(content);
    setCopiedFile(filename);
    setTimeout(() => setCopiedFile(null), 2000);
  };

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        mb: 2,
        gap: 1,
      }}
    >
      {!isUser && (
        <Avatar sx={{ bgcolor: theme.palette.primary.main }}>
          <BotIcon />
        </Avatar>
      )}
      
      <Box sx={{ maxWidth: '80%' }}>
        <Paper
          elevation={isUser ? 0 : 1}
          sx={{
            p: 2,
            bgcolor: isUser ? theme.palette.primary.main : '#ffffff',
            color: isUser ? '#ffffff' : 'text.primary',
            borderRadius: 2,
            borderTopLeftRadius: !isUser ? 0 : 2,
            borderTopRightRadius: isUser ? 0 : 2,
          }}
        >
          {isUser ? (
            <Typography variant="body1">{message.content}</Typography>
          ) : (
            <Box className="markdown-content">
              <ReactMarkdown
                components={{
                  code({ node, inline, className, children, ...props }: any) {
                    const match = /language-(\w+)/.exec(className || '');
                    return !inline && match ? (
                      <SyntaxHighlighter
                        style={vscDarkPlus}
                        language={match[1]}
                        PreTag="div"
                        {...props}
                      >
                        {String(children).replace(/\n$/, '')}
                      </SyntaxHighlighter>
                    ) : (
                      <code className={className} {...props}>
                        {children}
                      </code>
                    );
                  },
                }}
              >
                {message.content}
              </ReactMarkdown>
            </Box>
          )}
        </Paper>
        
        {message.code_blocks && message.code_blocks.length > 0 && (
          <Box sx={{ mt: 1 }}>
            {message.code_blocks.map((block, index) => (
              <Paper key={index} variant="outlined" sx={{ mt: 1, overflow: 'hidden' }}>
                <Box sx={{ bgcolor: '#f5f5f5', px: 2, py: 1, borderBottom: '1px solid #e0e0e0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="caption" sx={{ fontFamily: 'monospace', fontWeight: 600 }}>
                    {block.filename}
                  </Typography>
                  <Box>
                    <Tooltip title={copiedFile === block.filename ? "Copied!" : "Copy content"}>
                      <IconButton 
                        size="small" 
                        onClick={() => handleCopy(block.filename, block.content)}
                        sx={{ padding: 0.5, mr: 0.5 }}
                      >
                        {copiedFile === block.filename ? <CheckIcon fontSize="small" color="success" /> : <CopyIcon fontSize="small" />}
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Download file">
                      <IconButton 
                        size="small" 
                        onClick={() => handleDownload(block.filename, block.content)}
                        sx={{ padding: 0.5 }}
                      >
                        <DownloadIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </Box>
                <SyntaxHighlighter
                  language={block.language}
                  style={vscDarkPlus}
                  customStyle={{ margin: 0, borderRadius: 0 }}
                >
                  {block.content}
                </SyntaxHighlighter>
              </Paper>
            ))}
            
            {/* Deploy Button - shows when there are .tf files */}
            <DeployButton codeBlocks={message.code_blocks} />
          </Box>
        )}
      </Box>

      {isUser && (
        <Avatar sx={{ bgcolor: theme.palette.secondary.main }}>
          <PersonIcon />
        </Avatar>
      )}
    </Box>
  );
}
