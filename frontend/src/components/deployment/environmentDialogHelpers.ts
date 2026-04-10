import type {
  DeploymentEnvironmentDetail,
  DeploymentEnvironmentCreate,
} from '../../services/api';

export const MASKED_SECRET_VALUE = '***';

export const initialEnvironmentFormState: DeploymentEnvironmentCreate = {
  name: '',
  description: '',
  cloud_platform: 'aws',
  aws_access_key_id: '',
  aws_secret_access_key: '',
  aws_region: 'us-east-1',
  azure_subscription_id: '',
  azure_tenant_id: '',
  azure_client_id: '',
  azure_client_secret: '',
  is_default: false,
};

export const buildEnvironmentFormStateForEdit = (
  environment: DeploymentEnvironmentDetail
): DeploymentEnvironmentCreate => ({
  ...initialEnvironmentFormState,
  name: environment.name,
  description: environment.description ?? '',
  cloud_platform: environment.cloud_platform,
  aws_access_key_id:
    environment.cloud_platform === 'aws'
      ? environment.aws_access_key_id ?? ''
      : initialEnvironmentFormState.aws_access_key_id,
  aws_secret_access_key:
    environment.cloud_platform === 'aws'
      ? environment.aws_secret_access_key ?? ''
      : initialEnvironmentFormState.aws_secret_access_key,
  aws_region:
    environment.cloud_platform === 'aws'
      ? environment.aws_region ?? 'us-east-1'
      : initialEnvironmentFormState.aws_region,
  azure_subscription_id:
    environment.cloud_platform === 'azure'
      ? environment.azure_subscription_id ?? ''
      : initialEnvironmentFormState.azure_subscription_id,
  azure_tenant_id:
    environment.cloud_platform === 'azure'
      ? environment.azure_tenant_id ?? ''
      : initialEnvironmentFormState.azure_tenant_id,
  azure_client_id:
    environment.cloud_platform === 'azure'
      ? environment.azure_client_id ?? ''
      : initialEnvironmentFormState.azure_client_id,
  azure_client_secret:
    environment.cloud_platform === 'azure'
      ? environment.azure_client_secret ?? ''
      : initialEnvironmentFormState.azure_client_secret,
  is_default: environment.is_default,
});

export const buildEnvironmentUpdatePayload = (
  formData: DeploymentEnvironmentCreate,
  environment: DeploymentEnvironmentDetail
): Partial<DeploymentEnvironmentCreate> => {
  const payload: Partial<DeploymentEnvironmentCreate> = {};
  const trimmedName = formData.name.trim();
  const description = formData.description ?? '';

  if (trimmedName && trimmedName !== environment.name) {
    payload.name = trimmedName;
  }
  if (description !== (environment.description ?? '')) {
    payload.description = description;
  }
  if (formData.is_default !== environment.is_default) {
    payload.is_default = formData.is_default;
  }

  if (
    environment.cloud_platform === 'aws' &&
    formData.aws_region &&
    formData.aws_region !== environment.aws_region
  ) {
    payload.aws_region = formData.aws_region;
  }

  const credentialFields: Array<keyof DeploymentEnvironmentCreate> =
    environment.cloud_platform === 'aws'
      ? ['aws_access_key_id', 'aws_secret_access_key']
      : [
          'azure_subscription_id',
          'azure_tenant_id',
          'azure_client_id',
          'azure_client_secret',
        ];

  const currentCredentialValues: Partial<DeploymentEnvironmentCreate> =
    environment.cloud_platform === 'aws'
      ? {
          aws_access_key_id: environment.aws_access_key_id ?? '',
          aws_secret_access_key: environment.aws_secret_access_key ?? '',
        }
      : {
          azure_subscription_id: environment.azure_subscription_id ?? '',
          azure_tenant_id: environment.azure_tenant_id ?? '',
          azure_client_id: environment.azure_client_id ?? '',
          azure_client_secret: environment.azure_client_secret ?? '',
        };

  for (const field of credentialFields) {
    const value = formData[field];
    if (typeof value === 'string' && value.trim()) {
      const trimmedValue = value.trim();
      if (
        trimmedValue === currentCredentialValues[field] ||
        trimmedValue === MASKED_SECRET_VALUE
      ) {
        continue;
      }
      switch (field) {
        case 'aws_access_key_id':
          payload.aws_access_key_id = trimmedValue;
          break;
        case 'aws_secret_access_key':
          payload.aws_secret_access_key = trimmedValue;
          break;
        case 'azure_subscription_id':
          payload.azure_subscription_id = trimmedValue;
          break;
        case 'azure_tenant_id':
          payload.azure_tenant_id = trimmedValue;
          break;
        case 'azure_client_id':
          payload.azure_client_id = trimmedValue;
          break;
        case 'azure_client_secret':
          payload.azure_client_secret = trimmedValue;
          break;
      }
    }
  }

  return payload;
};
