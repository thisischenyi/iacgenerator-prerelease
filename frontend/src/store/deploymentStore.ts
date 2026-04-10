import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import {
  deploymentService,
  type DeploymentEnvironment,
  type DeploymentEnvironmentCreate,
  type Deployment,
  type DeploymentPlanResponse,
  type DeploymentApplyResponse,
  type DeploymentStatusType,
} from '../services/api';

type ApiErrorDetail = {
  message?: string;
  error?: string;
  plan_output?: string;
  apply_output?: string;
};

type ApiError = { response?: { data?: { detail?: string | ApiErrorDetail } } };

export const getApiErrorDetail = (error: unknown, fallback: string): string => {
  const detail = (error as ApiError).response?.data?.detail;
  if (!detail) return fallback;
  if (typeof detail === 'string') {
    return detail;
  }

  const primaryParts = [detail.message, detail.error].filter(
    (part): part is string => typeof part === 'string' && part.trim().length > 0
  );
  const primaryMessage = primaryParts.join(': ') || fallback;
  const executionOutput =
    (typeof detail.plan_output === 'string' && detail.plan_output.trim()) ||
    (typeof detail.apply_output === 'string' && detail.apply_output.trim()) ||
    '';

  return executionOutput
    ? `${primaryMessage}\n\n${executionOutput}`
    : primaryMessage;
};

interface DeploymentState {
  // Environments
  environments: DeploymentEnvironment[];
  environmentsLoading: boolean;
  environmentsError: string | null;

  // Current deployment
  currentDeployment: Deployment | null;
  planResponse: DeploymentPlanResponse | null;
  applyResponse: DeploymentApplyResponse | null;
  deploymentLoading: boolean;
  deploymentError: string | null;

  // Actions - Environments
  fetchEnvironments: () => Promise<void>;
  createEnvironment: (data: DeploymentEnvironmentCreate) => Promise<DeploymentEnvironment>;
  updateEnvironment: (id: number, data: Partial<DeploymentEnvironmentCreate>) => Promise<void>;
  deleteEnvironment: (id: number) => Promise<void>;

  // Actions - Deployment
  runPlan: (
    sessionId: string,
    environmentId: number,
    terraformCode: Record<string, string>
  ) => Promise<DeploymentPlanResponse>;
  runApply: (deploymentId: string) => Promise<DeploymentApplyResponse>;
  getDeploymentStatus: (deploymentId: string) => Promise<Deployment>;
  clearDeployment: () => void;
}

export const useDeploymentStore = create<DeploymentState>()(
  persist(
    (set) => ({
      // Initial state
      environments: [],
      environmentsLoading: false,
      environmentsError: null,

      currentDeployment: null,
      planResponse: null,
      applyResponse: null,
      deploymentLoading: false,
      deploymentError: null,

      // Environment actions
      fetchEnvironments: async () => {
        set({ environmentsLoading: true, environmentsError: null });
        try {
          const environments = await deploymentService.getEnvironments();
          set({ environments, environmentsLoading: false });
        } catch (error: unknown) {
          console.error('Failed to fetch environments:', error);
          set({
            environmentsError: getApiErrorDetail(error, 'Failed to fetch environments'),
            environmentsLoading: false,
          });
        }
      },

      createEnvironment: async (data: DeploymentEnvironmentCreate) => {
        set({ environmentsLoading: true, environmentsError: null });
        try {
          const newEnv = await deploymentService.createEnvironment(data);
          set((state) => ({
            environments: [...state.environments, newEnv],
            environmentsLoading: false,
          }));
          return newEnv;
        } catch (error: unknown) {
          console.error('Failed to create environment:', error);
          set({
            environmentsError: getApiErrorDetail(error, 'Failed to create environment'),
            environmentsLoading: false,
          });
          throw error;
        }
      },

      updateEnvironment: async (id: number, data: Partial<DeploymentEnvironmentCreate>) => {
        set({ environmentsLoading: true, environmentsError: null });
        try {
          const updated = await deploymentService.updateEnvironment(id, data);
          set((state) => ({
            environments: state.environments.map((env) =>
              env.id === id ? updated : env
            ),
            environmentsLoading: false,
          }));
        } catch (error: unknown) {
          console.error('Failed to update environment:', error);
          set({
            environmentsError: getApiErrorDetail(error, 'Failed to update environment'),
            environmentsLoading: false,
          });
          throw error;
        }
      },

      deleteEnvironment: async (id: number) => {
        set({ environmentsLoading: true, environmentsError: null });
        try {
          await deploymentService.deleteEnvironment(id);
          set((state) => ({
            environments: state.environments.filter((env) => env.id !== id),
            environmentsLoading: false,
          }));
        } catch (error: unknown) {
          console.error('Failed to delete environment:', error);
          set({
            environmentsError: getApiErrorDetail(error, 'Failed to delete environment'),
            environmentsLoading: false,
          });
          throw error;
        }
      },

      // Deployment actions
      runPlan: async (
        sessionId: string,
        environmentId: number,
        terraformCode: Record<string, string>
      ) => {
        console.log(`[Store: Deploy] runPlan called: sessionId=${sessionId}, environmentId=${environmentId}`);
        set({
          deploymentLoading: true,
          deploymentError: null,
          planResponse: null,
          applyResponse: null,
        });
        try {
          console.log(`[Store: Deploy] Calling deploymentService.runPlan...`);
          const response = await deploymentService.runPlan({
            session_id: sessionId,
            environment_id: environmentId,
            terraform_code: terraformCode,
          });
          console.log(`[Store: Deploy] runPlan success:`, response);
          set({
            planResponse: response,
            deploymentLoading: false,
          });
          return response;
        } catch (error: unknown) {
          console.error('[Store: Deploy] runPlan failed:', error);
          set({
            deploymentError: getApiErrorDetail(error, 'Failed to run terraform plan'),
            deploymentLoading: false,
          });
          throw error;
        }
      },

      runApply: async (deploymentId: string) => {
        console.log(`[Store: Deploy] runApply called: deploymentId=${deploymentId}`);
        set({ deploymentLoading: true, deploymentError: null });
        try {
          console.log(`[Store: Deploy] Calling deploymentService.runApply...`);
          const response = await deploymentService.runApply(deploymentId);
          console.log(`[Store: Deploy] runApply success:`, response);
          set({
            applyResponse: response,
            deploymentLoading: false,
          });
          return response;
        } catch (error: unknown) {
          console.error('[Store: Deploy] runApply failed:', error);
          set({
            deploymentError: getApiErrorDetail(error, 'Failed to run terraform apply'),
            deploymentLoading: false,
          });
          throw error;
        }
      },

      getDeploymentStatus: async (deploymentId: string) => {
        try {
          const deployment = await deploymentService.getDeployment(deploymentId);
          set({ currentDeployment: deployment });
          return deployment;
        } catch (error: unknown) {
          console.error('Failed to get deployment status:', error);
          throw error;
        }
      },

      clearDeployment: () => {
        set({
          currentDeployment: null,
          planResponse: null,
          applyResponse: null,
          deploymentError: null,
        });
      },
    }),
    {
      name: 'iac-deployment-storage',
      partialize: (state) => ({
        environments: state.environments,
      }),
    }
  )
);

// Helper to check if deployment is in a terminal state
export const isDeploymentComplete = (status: DeploymentStatusType): boolean => {
  return ['plan_failed', 'apply_success', 'apply_failed', 'destroyed'].includes(status);
};

// Helper to check if deployment can be applied
export const canApplyDeployment = (status: DeploymentStatusType): boolean => {
  return status === 'plan_ready';
};

