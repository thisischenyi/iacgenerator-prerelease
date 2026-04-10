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
  isInitialized: boolean;
  initializeAuth: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  setTokenFromOAuth: (code: string) => Promise<void>;
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
      isInitialized: false,

      initializeAuth: async () => {
        const { accessToken } = get();
        if (!accessToken) {
          useChatStore.getState().setAuthUser(null);
          set({ isInitialized: true });
          return;
        }
        setApiToken(accessToken);
        try {
          const me = await authService.me();
          useChatStore.getState().setAuthUser(me.id);
          await useChatStore.getState().syncSessionsFromServer();
          set({ user: me, isAuthenticated: true, isInitialized: true });
        } catch {
          setApiToken(null);
          useChatStore.getState().setAuthUser(null);
          set({ accessToken: null, user: null, isAuthenticated: false, isInitialized: true });
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
          set({
            error: getErrorMessage(error, 'Invalid email or password'),
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
          set({
            error: getErrorMessage(error, 'Registration failed. Please try again.'),
            loading: false,
          });
          throw error;
        }
      },

      setTokenFromOAuth: async (code: string) => {
        set({ loading: true, error: null });
        try {
          // Exchange one-time code for JWT via backend
          const exchangeResp = await authService.exchangeCode(code);
          const token = exchangeResp.access_token;
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
        // Do NOT persist accessToken to localStorage to reduce XSS risk.
        // Token is kept in memory; user must re-login after closing the tab.
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        // On rehydrate, there is no accessToken in storage anymore.
        // The user will need to re-authenticate via initializeAuth.
        if (state) {
          state.accessToken = null;
          state.isAuthenticated = false;
        }
      },
    }
  )
);
