import { create } from 'zustand';
import { policyService } from '../services/api';

export interface Policy {
  id: number;
  name: string;
  description?: string;
  natural_language_rule: string;
  cloud_platform: 'aws' | 'azure' | 'all';
  severity: 'error' | 'warning';
  enabled: boolean;
  created_at: string;
}

interface PolicyState {
  policies: Policy[];
  isLoading: boolean;
  error: string | null;
  
  fetchPolicies: () => Promise<void>;
  createPolicy: (policy: Partial<Policy>) => Promise<void>;
  updatePolicy: (id: number, policy: Partial<Policy>) => Promise<void>;
  togglePolicy: (id: number, enabled: boolean) => Promise<void>;
  deletePolicy: (id: number) => Promise<void>;
}

export const usePolicyStore = create<PolicyState>((set) => ({
  policies: [],
  isLoading: false,
  error: null,
  
  fetchPolicies: async () => {
    try {
      set({ isLoading: true, error: null });
      const policies = await policyService.getPolicies();
      set({ policies, isLoading: false });
    } catch (error) {
      set({ error: 'Failed to fetch policies', isLoading: false });
    }
  },
  
  createPolicy: async (policy) => {
    try {
      set({ isLoading: true, error: null });
      const newPolicy = await policyService.createPolicy(policy);
      set((state) => ({ 
        policies: [...state.policies, newPolicy],
        isLoading: false 
      }));
    } catch (error) {
      set({ error: 'Failed to create policy', isLoading: false });
      throw error;
    }
  },
  
  updatePolicy: async (id, policy) => {
    try {
      set({ isLoading: true, error: null });
      const updatedPolicy = await policyService.updatePolicy(id, policy);
      set((state) => ({
        policies: state.policies.map(p => 
          p.id === id ? updatedPolicy : p
        ),
        isLoading: false
      }));
    } catch (error) {
      set({ error: 'Failed to update policy', isLoading: false });
      throw error;
    }
  },
  
  togglePolicy: async (id, enabled) => {
    try {
      // Optimistic update
      set((state) => ({
        policies: state.policies.map(p => 
          p.id === id ? { ...p, enabled } : p
        )
      }));
      
      await policyService.togglePolicy(id, enabled);
    } catch (error) {
      // Revert on failure
      set((state) => ({
        policies: state.policies.map(p => 
          p.id === id ? { ...p, enabled: !enabled } : p
        ),
        error: 'Failed to toggle policy'
      }));
    }
  },
  
  deletePolicy: async (id) => {
    try {
      await policyService.deletePolicy(id);
      set((state) => ({
        policies: state.policies.filter(p => p.id !== id)
      }));
    } catch (error) {
      set({ error: 'Failed to delete policy' });
    }
  }
}));
