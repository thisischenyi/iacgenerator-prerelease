import { useEffect, useRef, useState } from 'react';
import { 
  Box, 
  Container, 
  Paper, 
  TextField, 
  IconButton, 
  Typography,
} from '@mui/material';
import { Send as SendIcon } from '@mui/icons-material';
import { useChatStore, useCurrentMessages, useAgentProgress } from '../store/chatStore';
import MessageBubble from '../components/chat/MessageBubble';
import SessionList from '../components/chat/SessionList';
import AgentProgressIndicator from '../components/chat/AgentProgressIndicator';

export default function ChatPage() {
  const { 
    isLoading, 
    error, 
    sendMessageWithProgress, 
    createNewSession, 
    currentSessionId 
  } = useChatStore();
  const messages = useCurrentMessages();
  const agentProgress = useAgentProgress();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Auto-create first session if none exists
    if (!currentSessionId) {
      createNewSession();
    }
  }, [currentSessionId, createNewSession]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    
    const content = input;
    setInput('');
    // Use streaming version with progress tracking
    await sendMessageWithProgress(content);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Box sx={{ display: 'flex', height: 'calc(100vh - 80px)' }}>
      {/* Session List Sidebar */}
      <SessionList />

      {/* Main Chat Area */}
      <Container 
        maxWidth="lg" 
        sx={{ 
          height: '100%', 
          display: 'flex', 
          flexDirection: 'column',
          py: 2,
        }}
      >
        <Paper 
          sx={{ 
            flexGrow: 1, 
            mb: 2, 
            p: 3, 
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            bgcolor: '#f8f9fa'
          }}
        >
          {messages.length === 0 ? (
            <Box sx={{ flexGrow: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', opacity: 0.5 }}>
              <Typography variant="h4" color="text.secondary" gutterBottom fontWeight="bold">
                IaC Generator AI
              </Typography>
              <Typography variant="body1" color="text.secondary">
                描述您想要创建的基础设施 (AWS/Azure)
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                或者上传 Excel 模板文件
              </Typography>
            </Box>
          ) : (
            messages.map((msg, index) => (
              <MessageBubble key={index} message={msg} />
            ))
          )}
          
          {/* Agent Progress Indicator - shown during loading */}
          {isLoading && (
            <AgentProgressIndicator
              currentAgent={agentProgress.currentAgent}
              completedAgents={agentProgress.completedAgents}
              failedAgent={agentProgress.failedAgent}
              currentMessage={agentProgress.currentMessage}
              isLoading={isLoading}
            />
          )}
          
          {error && (
            <Typography color="error" align="center" sx={{ mt: 2 }}>
              {error}
            </Typography>
          )}
          
          <div ref={messagesEndRef} />
        </Paper>

        <Paper sx={{ p: 1, display: 'flex', alignItems: 'center', borderRadius: 3 }}>
          <TextField
            fullWidth
            variant="standard"
            placeholder="输入您的基础设施需求..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            disabled={isLoading}
            InputProps={{ disableUnderline: true }}
            multiline
            maxRows={4}
            sx={{ px: 2 }}
          />
          
          <IconButton 
            color="primary" 
            onClick={handleSend} 
            disabled={!input.trim() || isLoading}
            sx={{ 
              bgcolor: input.trim() ? 'primary.main' : 'action.disabledBackground',
              color: input.trim() ? 'white' : 'action.disabled',
              '&:hover': { bgcolor: 'primary.dark' },
              width: 48,
              height: 48,
            }}
          >
            <SendIcon />
          </IconButton>
        </Paper>
      </Container>
    </Box>
  );
}
