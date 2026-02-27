import axios from 'axios';

let authToken: string | null = null;

export const setApiToken = (token: string | null) => {
  authToken = token;
};

export const getApiToken = (): string | null => authToken;

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  if (authToken) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${authToken}`;
  }
  return config;
});

export interface ChatRequest {
  session_id?: string;
  message: string;
  context?: Record<string, any>;
}

export interface ChatResponse {
  session_id: string;
  message: string;
  code_blocks?: Array<{
    filename: string;
    content: string;
    language: string;
  }>;
  metadata?: {
    workflow_state?: string;
    message_count?: number;
    resource_count?: number;
    compliance_passed?: boolean;
    error?: boolean;
    error_details?: string;
  };
}

export interface ApiSession {
  session_id: string;
  created_at: string;
  conversation_history?: Array<{
    role?: string;
    content?: string;
    code_blocks?: Array<{
      filename: string;
      content: string;
      language: string;
    }>;
  }>;
  generated_code?: Record<string, string>;
}

export interface CodeGenerationResult {
  success: boolean;
  files: Array<{
    filename: string;
    content: string;
    language: string;
  }>;
  summary: string;
  download_url?: string;
}

export interface AuthUser {
  id: number;
  email: string;
  full_name?: string | null;
  provider: string;
  avatar_url?: string | null;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: 'bearer';
  user: AuthUser;
}

export const authService = {
  register: async (data: { email: string; password: string; full_name?: string }) => {
    const response = await api.post<AuthTokenResponse>('/auth/register', data);
    return response.data;
  },
  login: async (data: { email: string; password: string }) => {
    const response = await api.post<AuthTokenResponse>('/auth/login', data);
    return response.data;
  },
  me: async () => {
    const response = await api.get<AuthUser>('/auth/me');
    return response.data;
  },
  getGoogleLoginUrl: () => '/api/auth/google/login',
  getMicrosoftLoginUrl: () => '/api/auth/microsoft/login',
};

export const chatService = {
  sendMessage: async (data: ChatRequest) => {
    try {
      console.log('Sending chat request:', data);
      const response = await api.post<ChatResponse>('/chat', data);
      console.log('Received chat response:', response.data);
      return response.data;
    } catch (error) {
      console.error('API Error in sendMessage:', error);
      throw error;
    }
  },
  
  createSession: async () => {
    // Explicitly send user_id as null to match schema
    const response = await api.post<{ session_id: string }>('/sessions', { user_id: null });
    return response.data;
  },

  listSessions: async () => {
    const response = await api.get<ApiSession[]>('/sessions');
    return response.data;
  },

  deleteSession: async (sessionId: string) => {
    await api.delete(`/sessions/${sessionId}`);
  }
};

export const excelService = {
  uploadFile: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/excel/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
  
  downloadTemplate: async (type: 'aws' | 'azure' | 'full' = 'full') => {
    const response = await api.get(`/excel/template?template_type=${type}`, {
      responseType: 'blob',
    });
    return response.data;
  }
};

export const policyService = {
  getPolicies: async () => {
    const response = await api.get('/policies');
    return response.data;
  },
  
  createPolicy: async (policy: any) => {
    const response = await api.post('/policies', policy);
    return response.data;
  },
  
  updatePolicy: async (id: number, policy: any) => {
    const response = await api.put(`/policies/${id}`, policy);
    return response.data;
  },
  
  deletePolicy: async (id: number) => {
    const response = await api.delete(`/policies/${id}`);
    return response.data;
  },
  
  togglePolicy: async (id: number, enabled: boolean) => {
    const response = await api.patch(`/policies/${id}/toggle`, { enabled });
    return response.data;
  }
};

// Deployment types
export type CloudPlatform = 'aws' | 'azure' | 'all';

export type DeploymentStatusType = 
  | 'pending'
  | 'planning'
  | 'plan_ready'
  | 'plan_failed'
  | 'applying'
  | 'apply_success'
  | 'apply_failed'
  | 'destroyed';

export interface DeploymentEnvironment {
  id: number;
  name: string;
  description: string | null;
  cloud_platform: CloudPlatform;
  has_aws_credentials: boolean;
  aws_region: string | null;
  has_azure_credentials: boolean;
  is_default: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface DeploymentEnvironmentCreate {
  name: string;
  description?: string;
  cloud_platform: CloudPlatform;
  aws_access_key_id?: string;
  aws_secret_access_key?: string;
  aws_region?: string;
  azure_subscription_id?: string;
  azure_tenant_id?: string;
  azure_client_id?: string;
  azure_client_secret?: string;
  is_default?: boolean;
}

export interface PlanSummary {
  add: number;
  change: number;
  destroy: number;
}

export interface Deployment {
  id: number;
  deployment_id: string;
  session_id: string;
  environment_id: number;
  status: DeploymentStatusType;
  plan_output: string | null;
  plan_summary: PlanSummary | null;
  apply_output: string | null;
  terraform_outputs: Record<string, any> | null;
  error_message: string | null;
  created_at: string;
  updated_at: string | null;
  completed_at: string | null;
}

export interface DeploymentPlanRequest {
  session_id: string;
  environment_id: number;
  terraform_code: Record<string, string>;
}

export interface DeploymentPlanResponse {
  deployment_id: string;
  status: DeploymentStatusType;
  plan_output: string;
  plan_summary: PlanSummary;
}

export interface DeploymentApplyResponse {
  deployment_id: string;
  status: DeploymentStatusType;
  apply_output: string | null;
  terraform_outputs: Record<string, any> | null;
  error_message: string | null;
}

export const deploymentService = {
  // Environment CRUD
  getEnvironments: async (): Promise<DeploymentEnvironment[]> => {
    const response = await api.get<DeploymentEnvironment[]>('/deployments/environments');
    return response.data;
  },

  createEnvironment: async (data: DeploymentEnvironmentCreate): Promise<DeploymentEnvironment> => {
    const response = await api.post<DeploymentEnvironment>('/deployments/environments', data);
    return response.data;
  },

  updateEnvironment: async (id: number, data: Partial<DeploymentEnvironmentCreate>): Promise<DeploymentEnvironment> => {
    const response = await api.put<DeploymentEnvironment>(`/deployments/environments/${id}`, data);
    return response.data;
  },

  deleteEnvironment: async (id: number): Promise<void> => {
    await api.delete(`/deployments/environments/${id}`);
  },

  // Deployment operations
  runPlan: async (request: DeploymentPlanRequest): Promise<DeploymentPlanResponse> => {
    console.log(`[API: Deploy] Sending plan request:`, request);
    try {
      const response = await api.post<DeploymentPlanResponse>('/deployments/plan', request);
      console.log(`[API: Deploy] Plan response received:`, response.data);
      return response.data;
    } catch (error: any) {
      console.error(`[API: Deploy] Plan request failed:`, error);
      if (error.response) {
        console.error(`[API: Deploy] Error response:`, error.response.data);
        console.error(`[API: Deploy] Error status:`, error.response.status);
      }
      throw error;
    }
  },

  runApply: async (deploymentId: string): Promise<DeploymentApplyResponse> => {
    console.log(`[API: Deploy] Sending apply request: deployment_id=${deploymentId}`);
    try {
      const response = await api.post<DeploymentApplyResponse>('/deployments/apply', {
        deployment_id: deploymentId,
      });
      console.log(`[API: Deploy] Apply response received:`, response.data);
      return response.data;
    } catch (error: any) {
      console.error(`[API: Deploy] Apply request failed:`, error);
      if (error.response) {
        console.error(`[API: Deploy] Error response:`, error.response.data);
        console.error(`[API: Deploy] Error status:`, error.response.status);
      }
      throw error;
    }
  },

  getDeployment: async (deploymentId: string): Promise<Deployment> => {
    const response = await api.get<Deployment>(`/deployments/${deploymentId}`);
    return response.data;
  },

  listDeployments: async (sessionId?: string): Promise<Deployment[]> => {
    const params = sessionId ? { session_id: sessionId } : {};
    const response = await api.get<Deployment[]>('/deployments', { params });
    return response.data;
  },

  destroyDeployment: async (deploymentId: string): Promise<Deployment> => {
    const response = await api.post<Deployment>(`/deployments/${deploymentId}/destroy`);
    return response.data;
  },
};

export default api;
