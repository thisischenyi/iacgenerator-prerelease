import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authService, setApiToken, type AuthUser } from '../services/api';
import { useChatStore } from './chatStore';

interface AuthState {
  accessToken: string | null;
  user: AuthUser | null;
  loading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  initializeAuth: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  setTokenFromOAuth: (token: string) => Promise<void>;
  logout: () => void;
  clearError: () => void;
}

const getErrorMessage = (error: unknown, fallback: string): string => {
  const maybeError = error as {
    response?: {
      data?: {
        detail?: unknown;
      };
    };
  };
  const detail = maybeError?.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') return item;
        if (item?.msg) return String(item.msg);
        return '';
      })
      .filter(Boolean)
      .join('; ') || fallback;
  }
  if (detail && typeof detail === 'object') {
    const objectDetail = detail as Record<string, unknown>;
    if ('msg' in objectDetail) return String(objectDetail.msg);
    return fallback;
  }
  return fallback;
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      user: null,
      loading: false,
      error: null,
      isAuthenticated: false,

      initializeAuth: async () => {
        const { accessToken } = get();
        if (!accessToken) {
          useChatStore.getState().setAuthUser(null);
          return;
        }
        setApiToken(accessToken);
        try {
          const me = await authService.me();
          useChatStore.getState().setAuthUser(me.id);
          await useChatStore.getState().syncSessionsFromServer();
          set({ user: me, isAuthenticated: true });
        } catch {
          setApiToken(null);
          useChatStore.getState().setAuthUser(null);
          set({ accessToken: null, user: null, isAuthenticated: false });
        }
      },

      login: async (email: string, password: string) => {
        set({ loading: true, error: null });
        try {
          const result = await authService.login({ email, password });
          setApiToken(result.access_token);
          useChatStore.getState().setAuthUser(result.user.id);
          await useChatStore.getState().syncSessionsFromServer();
          set({
            accessToken: result.access_token,
            user: result.user,
            isAuthenticated: true,
            loading: false,
          });
        } catch (error: unknown) {
          void error;
          set({
            error: 'Invalid email or password',
            loading: false,
          });
          throw error;
        }
      },

      register: async (email: string, password: string, fullName?: string) => {
        set({ loading: true, error: null });
        try {
          const result = await authService.register({
            email,
            password,
            full_name: fullName,
          });
          setApiToken(result.access_token);
          useChatStore.getState().setAuthUser(result.user.id);
          await useChatStore.getState().syncSessionsFromServer();
          set({
            accessToken: result.access_token,
            user: result.user,
            isAuthenticated: true,
            loading: false,
          });
        } catch (error: unknown) {
          void error;
          set({
            error: 'Invalid email or password',
            loading: false,
          });
          throw error;
        }
      },

      setTokenFromOAuth: async (token: string) => {
        set({ loading: true, error: null });
        try {
          setApiToken(token);
          const me = await authService.me();
          useChatStore.getState().setAuthUser(me.id);
          await useChatStore.getState().syncSessionsFromServer();
          set({
            accessToken: token,
            user: me,
            isAuthenticated: true,
            loading: false,
          });
        } catch (error: unknown) {
          setApiToken(null);
          useChatStore.getState().setAuthUser(null);
          set({
            accessToken: null,
            user: null,
            isAuthenticated: false,
            loading: false,
            error: getErrorMessage(error, 'OAuth login failed'),
          });
          throw error;
        }
      },

      logout: () => {
        setApiToken(null);
        useChatStore.getState().setAuthUser(null);
        set({
          accessToken: null,
          user: null,
          isAuthenticated: false,
          error: null,
        });
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'iac-auth-storage',
      partialize: (state) => ({
        accessToken: state.accessToken,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        if (state?.accessToken) {
          setApiToken(state.accessToken);
        }
      },
    }
  )
);
