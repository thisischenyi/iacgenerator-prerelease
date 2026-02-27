import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { chatService, getApiToken } from '../services/api';
import type { AgentType } from '../components/chat/AgentProgressIndicator';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  code_blocks?: Array<{
    filename: string;
    content: string;
    language: string;
  }>;
}

interface Session {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  updatedAt: number;
}

interface AgentProgressState {
  currentAgent: AgentType | null;
  completedAgents: AgentType[];
  failedAgent: AgentType | null;
  currentMessage?: string;
}

interface ChatState {
  authUserId: number | null;
  // Multi-session support
  sessions: Record<string, Session>;  // sessionId -> Session
  currentSessionId: string | null;
  
  // Current session state (for easy access)
  isLoading: boolean;
  error: string | null;
  
  // Agent progress tracking
  agentProgress: AgentProgressState;
  
  // Session management
  createNewSession: () => Promise<void>;
  switchSession: (sessionId: string) => void;
  deleteSession: (sessionId: string) => Promise<void>;
  renameSession: (sessionId: string, newTitle: string) => void;
  
  // Message operations
  sendMessage: (content: string, resources?: any[]) => Promise<void>;
  sendMessageWithProgress: (content: string, resources?: any[]) => Promise<void>;
  
  // Progress management
  resetProgress: () => void;
  
  // Legacy compatibility
  clearSession: () => void;
  setAuthUser: (userId: number | null) => void;
  syncSessionsFromServer: () => Promise<void>;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      authUserId: null,
      sessions: {},
      currentSessionId: null,
      isLoading: false,
      error: null,
      agentProgress: {
        currentAgent: null,
        completedAgents: [],
        failedAgent: null,
      },
      
      resetProgress: () => {
        set({
          agentProgress: {
            currentAgent: null,
            completedAgents: [],
            failedAgent: null,
            currentMessage: undefined,
          },
        });
      },
      
      createNewSession: async () => {
        try {
          set({ isLoading: true, error: null });
          const response = await chatService.createSession();
          const sessionId = response.session_id;
          
          const newSession: Session = {
            id: sessionId,
            title: `会话 ${Object.keys(get().sessions).length + 1}`,
            messages: [],
            createdAt: Date.now(),
            updatedAt: Date.now(),
          };
          
          set((state) => ({
            sessions: { ...state.sessions, [sessionId]: newSession },
            currentSessionId: sessionId,
            isLoading: false,
          }));

          // Re-sync with backend to ensure local state matches persisted state.
          await get().syncSessionsFromServer();
          set({ currentSessionId: sessionId });
        } catch (error) {
          console.error('Failed to create session:', error);
          set({ error: 'Failed to create session', isLoading: false });
        }
      },
      
      switchSession: (sessionId: string) => {
        const { sessions } = get();
        if (sessions[sessionId]) {
          set({ currentSessionId: sessionId, error: null });
        }
      },
      
      deleteSession: async (sessionId: string) => {
        try {
          await chatService.deleteSession(sessionId);
        } catch (error) {
          console.error('Failed to delete session:', error);
          set({ error: 'Failed to delete session' });
          return;
        }

        const { sessions, currentSessionId } = get();
        const newSessions = { ...sessions };
        delete newSessions[sessionId];
        
        // If deleting current session, switch to another or create new
        let newCurrentSessionId = currentSessionId;
        if (currentSessionId === sessionId) {
          const remainingSessions = Object.keys(newSessions);
          newCurrentSessionId = remainingSessions.length > 0 ? remainingSessions[0] : null;
        }
        
        set({ 
          sessions: newSessions, 
          currentSessionId: newCurrentSessionId 
        });
      },
      
      renameSession: (sessionId: string, newTitle: string) => {
        const { sessions } = get();
        if (sessions[sessionId]) {
          set({
            sessions: {
              ...sessions,
              [sessionId]: {
                ...sessions[sessionId],
                title: newTitle,
                updatedAt: Date.now(),
              },
            },
          });
        }
      },
      
      // Original sendMessage (non-streaming, for fallback)
      sendMessage: async (content: string, resources?: any[]) => {
        let { currentSessionId, sessions } = get();
        
        // Auto-create session if none exists
        if (!currentSessionId) {
          await get().createNewSession();
          currentSessionId = get().currentSessionId;
        }
        
        if (!currentSessionId) {
          set({ error: 'No active session' });
          return;
        }
        
        const session = sessions[currentSessionId];
        if (!session) {
          set({ error: 'Session not found' });
          return;
        }
        
        // Add user message immediately
        const userMessage: Message = { role: 'user', content };
        const updatedMessages = [...session.messages, userMessage];
        
        set({
          sessions: {
            ...sessions,
            [currentSessionId]: {
              ...session,
              messages: updatedMessages,
              updatedAt: Date.now(),
            },
          },
          isLoading: true,
          error: null,
        });
        
        try {
          // Prepare context with resources if provided
          const context = resources ? { excel_resources: resources } : undefined;
          
          const response = await chatService.sendMessage({
            session_id: currentSessionId,
            message: content,
            context,
          });
          
          const assistantMessage: Message = {
            role: 'assistant',
            content: response.message,
            code_blocks: response.code_blocks,
          };
          
          // Update with assistant response
          const currentState = get();
          const currentSession = currentState.sessions[currentSessionId];
          
          set({
            sessions: {
              ...currentState.sessions,
              [currentSessionId]: {
                ...currentSession,
                messages: [...currentSession.messages, assistantMessage],
                updatedAt: Date.now(),
              },
            },
            isLoading: false,
          });
        } catch (error) {
          console.error('SendMessage Error:', error);
          set({ error: 'Failed to send message', isLoading: false });
        }
      },
      
      // New streaming sendMessage with progress tracking
      sendMessageWithProgress: async (content: string, resources?: any[]) => {
        let { currentSessionId, sessions } = get();
        
        // Auto-create session if none exists
        if (!currentSessionId) {
          await get().createNewSession();
          currentSessionId = get().currentSessionId;
        }
        
        if (!currentSessionId) {
          set({ error: 'No active session' });
          return;
        }
        
        const session = sessions[currentSessionId];
        if (!session) {
          set({ error: 'Session not found' });
          return;
        }
        
        // Add user message immediately
        const userMessage: Message = { role: 'user', content };
        const updatedMessages = [...session.messages, userMessage];
        
        // Reset progress and start loading
        set({
          sessions: {
            ...sessions,
            [currentSessionId]: {
              ...session,
              messages: updatedMessages,
              updatedAt: Date.now(),
            },
          },
          isLoading: true,
          error: null,
          agentProgress: {
            currentAgent: null,
            completedAgents: [],
            failedAgent: null,
          },
        });
        
        try {
          // Prepare request body
          const requestBody = {
            session_id: currentSessionId,
            message: content,
            context: resources ? { excel_resources: resources } : undefined,
          };
          const token = getApiToken();
          
          // Use SSE streaming endpoint
          const response = await fetch('/api/chat/stream', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body: JSON.stringify(requestBody),
          });
          
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }
          
          const reader = response.body?.getReader();
          if (!reader) {
            throw new Error('No response body');
          }

          const decoder = new TextDecoder();
          let buffer = '';
          
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            
            // Parse SSE events from buffer
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';  // Keep incomplete line in buffer
            
            // Track event type across lines (SSE format: event: X\ndata: Y\n\n)
            let currentEventType = '';
            
            for (const rawLine of lines) {
              const line = rawLine.trimEnd();
              if (!line) {
                continue;
              }

              if (line.startsWith('event: ')) {
                // Capture event type for the next data line
                currentEventType = line.slice(7).trim();
                continue;
              }
              
              if (line.startsWith('data: ')) {
                const data = line.slice(6).trim();
                try {
                  const event = JSON.parse(data);
                  
                  // Use captured event type (from 'event:' line) 
                  const eventType = currentEventType || event.type;
                  
                  if (eventType === 'complete') {
                    // Final response
                    const assistantMessage: Message = {
                      role: 'assistant',
                      content: event.message || '',
                      code_blocks: event.code_blocks,
                    };
                    
                    const currentState = get();
                    const currentSession = currentState.sessions[currentSessionId!];
                    
                    set({
                      sessions: {
                        ...currentState.sessions,
                        [currentSessionId!]: {
                          ...currentSession,
                          messages: [...currentSession.messages, assistantMessage],
                          updatedAt: Date.now(),
                        },
                      },
                      isLoading: false,
                      agentProgress: {
                        ...currentState.agentProgress,
                        currentAgent: null,
                      },
                    });
                  } else if (eventType === 'error') {
                    set({
                      error: event.message || 'Unknown error',
                      isLoading: false,
                    });
                  } else if (eventType === 'progress' && event.agent) {
                    // Progress event - update agent status
                    const agentType = event.agent as AgentType;
                    const status = event.status;
                    
                    console.log('[SSE] Progress event:', agentType, status);
                    
                    set((state) => {
                      const newCompletedAgents = status === 'completed'
                        ? [...state.agentProgress.completedAgents, agentType]
                        : state.agentProgress.completedAgents;
                      
                      return {
                        agentProgress: {
                          currentAgent: status === 'started' ? agentType : 
                                       (status === 'completed' ? null : state.agentProgress.currentAgent),
                          completedAgents: newCompletedAgents,
                          failedAgent: status === 'failed' ? agentType : state.agentProgress.failedAgent,
                          currentMessage: event.message || event.agent_description,
                        },
                      };
                    });
                  }
                  
                  // Reset event type after processing
                  currentEventType = '';
                } catch (parseError) {
                  console.warn('Failed to parse SSE event:', data, parseError);
                }
              }
            }
          }
        } catch (error) {
          console.error('SendMessageWithProgress Error:', error);
          // Avoid re-sending the same message automatically if stream already started,
          // otherwise backend may execute workflow twice and persist duplicated history.
          try {
            await get().syncSessionsFromServer();
          } catch {
            // Ignore secondary sync error; keep primary error message below.
          }
          set({ error: 'Failed to stream progress. Session has been synced from server.', isLoading: false });
        }
      },
      
      // Legacy compatibility - clear current session
      clearSession: () => {
        const { currentSessionId } = get();
        if (currentSessionId) {
          void get().deleteSession(currentSessionId);
        }
      },

      setAuthUser: (userId: number | null) => {
        const currentAuthUserId = get().authUserId;
        if (currentAuthUserId === userId) return;

        // Hard reset chat state when account changes to prevent cross-user leakage.
        set({
          authUserId: userId,
          sessions: {},
          currentSessionId: null,
          isLoading: false,
          error: null,
          agentProgress: {
            currentAgent: null,
            completedAgents: [],
            failedAgent: null,
            currentMessage: undefined,
          },
        });
      },

      syncSessionsFromServer: async () => {
        const { authUserId } = get();
        if (!authUserId) return;

        try {
          const apiSessions = await chatService.listSessions();
          const mappedSessions: Record<string, Session> = {};

          for (const item of apiSessions) {
            const sessionId = item.session_id;
            const created = new Date(item.created_at).getTime() || Date.now();
            const rawMessages: Message[] = (item.conversation_history || [])
              .map((msg) => ({
                role: msg.role === 'assistant' ? 'assistant' : 'user',
                content: msg.content || '',
                code_blocks: msg.code_blocks,
              }))
              .filter((msg) => msg.content.trim().length > 0);

            // Remove accidental duplicated adjacent messages from historical persisted data.
            let messages = rawMessages.filter((msg, index) => {
              if (index === 0) return true;
              const prev = rawMessages[index - 1];
              return !(prev.role === msg.role && prev.content === msg.content);
            });

            // If all user prompts in this session are identical, keep only the latest run
            // to hide duplicated retries created by historical auto-resend behavior.
            const userMessageIndexes = messages
              .map((m, idx) => (m.role === 'user' ? idx : -1))
              .filter((idx) => idx >= 0);
            const uniqueUserContents = new Set(
              messages.filter((m) => m.role === 'user').map((m) => m.content)
            );
            if (userMessageIndexes.length > 1 && uniqueUserContents.size === 1) {
              const lastUserIdx = userMessageIndexes[userMessageIndexes.length - 1];
              messages = messages.slice(lastUserIdx);
            }

            // Restore code artifacts for Excel/code-generation sessions even if conversation text
            // only contains summary.
            if (item.generated_code && Object.keys(item.generated_code).length > 0) {
              const generatedBlocks = Object.entries(item.generated_code).map(([filename, content]) => ({
                filename,
                content,
                language: filename.endsWith('.tf') ? 'hcl' : 'text',
              }));

              let attached = false;
              for (let i = messages.length - 1; i >= 0; i -= 1) {
                if (messages[i].role === 'assistant') {
                  messages[i] = { ...messages[i], code_blocks: generatedBlocks };
                  attached = true;
                  break;
                }
              }
              if (!attached) {
                messages.push({
                  role: 'assistant',
                  content: 'Terraform code has been generated.',
                  code_blocks: generatedBlocks,
                });
              }
            }

            mappedSessions[sessionId] = {
              id: sessionId,
              title: messages[0]?.content?.slice(0, 30) || `Session ${Object.keys(mappedSessions).length + 1}`,
              messages,
              createdAt: created,
              updatedAt: created,
            };
          }

          const nextCurrentSessionId =
            (get().currentSessionId && mappedSessions[get().currentSessionId!])
              ? get().currentSessionId
              : (Object.keys(mappedSessions)[0] || null);

          set({
            sessions: mappedSessions,
            currentSessionId: nextCurrentSessionId,
          });
        } catch (error) {
          console.error('Failed to sync sessions from server:', error);
          set({ error: 'Failed to load session history' });
        }
      },
    }),
    {
      name: 'iac-chat-storage',
      partialize: (state) => ({ 
        authUserId: state.authUserId,
        sessions: state.sessions,
        currentSessionId: state.currentSessionId,
      }),
    }
  )
);

// Helper hooks for easier access to current session data
export const useCurrentSession = () => {
  const currentSessionId = useChatStore((state) => state.currentSessionId);
  const sessions = useChatStore((state) => state.sessions);
  return currentSessionId ? sessions[currentSessionId] : null;
};

export const useCurrentMessages = () => {
  const session = useCurrentSession();
  return session?.messages || [];
};

export const useAgentProgress = () => {
  return useChatStore((state) => state.agentProgress);
};
