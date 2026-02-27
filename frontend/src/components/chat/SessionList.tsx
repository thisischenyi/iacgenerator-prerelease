import { useState } from 'react';
import {
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  IconButton,
  Typography,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Chat as ChatIcon,
} from '@mui/icons-material';
import { useChatStore } from '../../store/chatStore';

export default function SessionList() {
  const sessions = useChatStore((state) => state.sessions);
  const currentSessionId = useChatStore((state) => state.currentSessionId);
  const createNewSession = useChatStore((state) => state.createNewSession);
  const switchSession = useChatStore((state) => state.switchSession);
  const deleteSession = useChatStore((state) => state.deleteSession);
  const renameSession = useChatStore((state) => state.renameSession);

  const [renameDialogOpen, setRenameDialogOpen] = useState(false);
  const [renamingSessionId, setRenamingSessionId] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState('');

  const handleNewSession = async () => {
    await createNewSession();
  };

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this session?')) {
      await deleteSession(sessionId);
    }
  };

  const handleRenameClick = (sessionId: string, currentTitle: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setRenamingSessionId(sessionId);
    setNewTitle(currentTitle);
    setRenameDialogOpen(true);
  };

  const handleRenameSubmit = () => {
    if (renamingSessionId && newTitle.trim()) {
      renameSession(renamingSessionId, newTitle.trim());
    }
    setRenameDialogOpen(false);
    setRenamingSessionId(null);
    setNewTitle('');
  };

  const sortedSessions = Object.values(sessions).sort((a, b) => b.updatedAt - a.updatedAt);

  return (
    <Box
      sx={{
        width: 280,
        height: '100%',
        borderRight: 1,
        borderColor: 'divider',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: '#fafafa',
      }}
    >
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="h6" fontWeight="bold" color="primary" gutterBottom>
          会话列表
        </Typography>
        <Button
          variant="contained"
          fullWidth
          startIcon={<AddIcon />}
          onClick={handleNewSession}
          sx={{ mt: 1 }}
        >
          新建会话
        </Button>
      </Box>

      {/* Session List */}
      <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
        {sortedSessions.length === 0 ? (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <ChatIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
            <Typography variant="body2" color="text.secondary">
              暂无会话
            </Typography>
            <Typography variant="caption" color="text.secondary">
              点击上方按钮创建新会话
            </Typography>
          </Box>
        ) : (
          <List sx={{ py: 0 }}>
            {sortedSessions.map((session) => (
              <ListItem
                key={session.id}
                disablePadding
                secondaryAction={
                  <Box>
                    <IconButton
                      edge="end"
                      size="small"
                      onClick={(e) => handleRenameClick(session.id, session.title, e)}
                      sx={{ mr: 0.5 }}
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      edge="end"
                      size="small"
                      onClick={(e) => { void handleDeleteSession(session.id, e); }}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Box>
                }
              >
                <ListItemButton
                  selected={session.id === currentSessionId}
                  onClick={() => switchSession(session.id)}
                  sx={{
                    borderLeft: session.id === currentSessionId ? 3 : 0,
                    borderColor: 'primary.main',
                    bgcolor: session.id === currentSessionId ? 'action.selected' : 'transparent',
                    '&:hover': {
                      bgcolor: session.id === currentSessionId ? 'action.selected' : 'action.hover',
                    },
                  }}
                >
                  <ListItemText
                    primary={session.title}
                    secondary={`${session.messages.length} 条消息`}
                    primaryTypographyProps={{
                      fontWeight: session.id === currentSessionId ? 'bold' : 'normal',
                      noWrap: true,
                      sx: { pr: 8 },
                    }}
                    secondaryTypographyProps={{
                      variant: 'caption',
                    }}
                  />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        )}
      </Box>

      {/* Rename Dialog */}
      <Dialog open={renameDialogOpen} onClose={() => setRenameDialogOpen(false)}>
        <DialogTitle>重命名会话</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="会话名称"
            fullWidth
            variant="outlined"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                handleRenameSubmit();
              }
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRenameDialogOpen(false)}>取消</Button>
          <Button onClick={handleRenameSubmit} variant="contained">
            确定
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
