import { describe, expect, it } from 'vitest';

import {
  buildEnvironmentFormStateForEdit,
  buildEnvironmentUpdatePayload,
} from './environmentDialogHelpers';
import type { DeploymentEnvironment } from '../../services/api';

describe('environment dialog edit helpers', () => {
  it('builds edit form state from an existing azure environment without exposing secrets', () => {
    const environment: DeploymentEnvironment = {
      id: 7,
      name: 'azure-demo-env',
      description: 'existing azure env',
      cloud_platform: 'azure',
      has_aws_credentials: false,
      aws_region: null,
      has_azure_credentials: true,
      is_default: true,
      created_at: '2026-04-10T00:00:00Z',
      updated_at: null,
    };

    const formState = buildEnvironmentFormStateForEdit(environment);

    expect(formState).toMatchObject({
      name: 'azure-demo-env',
      description: 'existing azure env',
      cloud_platform: 'azure',
      is_default: true,
      azure_subscription_id: '',
      azure_tenant_id: '',
      azure_client_id: '',
      azure_client_secret: '',
    });
  });

  it('omits blank credential fields when building an edit payload', () => {
    const environment: DeploymentEnvironment = {
      id: 9,
      name: 'azure-demo-env',
      description: 'existing azure env',
      cloud_platform: 'azure',
      has_aws_credentials: false,
      aws_region: null,
      has_azure_credentials: true,
      is_default: false,
      created_at: '2026-04-10T00:00:00Z',
      updated_at: null,
    };

    const payload = buildEnvironmentUpdatePayload(
      {
        name: 'azure-demo-env-updated',
        description: 'updated description',
        cloud_platform: 'azure',
        aws_access_key_id: '',
        aws_secret_access_key: '',
        aws_region: 'us-east-1',
        azure_subscription_id: '',
        azure_tenant_id: '',
        azure_client_id: '',
        azure_client_secret: '',
        is_default: true,
      },
      environment
    );

    expect(payload).toEqual({
      name: 'azure-demo-env-updated',
      description: 'updated description',
      is_default: true,
    });
  });
});
