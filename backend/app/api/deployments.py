"""Deployment environment and terraform deployment API routes."""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import DeploymentEnvironment, Deployment
from app.schemas import (
    DeploymentEnvironmentCreate,
    DeploymentEnvironmentUpdate,
    DeploymentEnvironmentResponse,
    DeploymentPlanRequest,
    DeploymentPlanResponse,
    DeploymentApplyRequest,
    DeploymentApplyResponse,
    DeploymentResponse,
    DeploymentStatus,
    PlanSummary,
    SuccessResponse,
)
from app.services.terraform_executor import TerraformExecutor

router = APIRouter()


# ============ Environment CRUD ============


@router.get("/environments", response_model=List[DeploymentEnvironmentResponse])
def list_environments(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    Get all deployment environments.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session

    Returns:
        List of deployment environments
    """
    environments = db.query(DeploymentEnvironment).offset(skip).limit(limit).all()

    # Convert to response with masked credentials
    result = []
    for env in environments:
        response = DeploymentEnvironmentResponse(
            id=env.id,
            name=env.name,
            description=env.description,
            cloud_platform=env.cloud_platform,
            has_aws_credentials=bool(
                env.aws_access_key_id and env.aws_secret_access_key
            ),
            aws_region=env.aws_region,
            has_azure_credentials=bool(
                env.azure_subscription_id
                and env.azure_tenant_id
                and env.azure_client_id
                and env.azure_client_secret
            ),
            is_default=env.is_default,
            created_at=env.created_at,
            updated_at=env.updated_at,
        )
        result.append(response)

    return result


@router.post(
    "/environments",
    response_model=DeploymentEnvironmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_environment(
    env_data: DeploymentEnvironmentCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new deployment environment.

    Args:
        env_data: Environment data
        db: Database session

    Returns:
        Created environment

    Raises:
        HTTPException: If environment with same name exists
    """
    existing = (
        db.query(DeploymentEnvironment)
        .filter(DeploymentEnvironment.name == env_data.name)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Environment with name '{env_data.name}' already exists",
        )

    # If this is set as default, unset other defaults
    if env_data.is_default:
        db.query(DeploymentEnvironment).filter(
            DeploymentEnvironment.is_default == True
        ).update({"is_default": False})

    environment = DeploymentEnvironment(
        name=env_data.name,
        description=env_data.description,
        cloud_platform=env_data.cloud_platform,
        aws_access_key_id=env_data.aws_access_key_id,
        aws_secret_access_key=env_data.aws_secret_access_key,
        aws_region=env_data.aws_region,
        azure_subscription_id=env_data.azure_subscription_id,
        azure_tenant_id=env_data.azure_tenant_id,
        azure_client_id=env_data.azure_client_id,
        azure_client_secret=env_data.azure_client_secret,
        is_default=env_data.is_default,
    )

    db.add(environment)
    db.commit()
    db.refresh(environment)

    return DeploymentEnvironmentResponse(
        id=environment.id,
        name=environment.name,
        description=environment.description,
        cloud_platform=environment.cloud_platform,
        has_aws_credentials=bool(
            environment.aws_access_key_id and environment.aws_secret_access_key
        ),
        aws_region=environment.aws_region,
        has_azure_credentials=bool(
            environment.azure_subscription_id
            and environment.azure_tenant_id
            and environment.azure_client_id
            and environment.azure_client_secret
        ),
        is_default=environment.is_default,
        created_at=environment.created_at,
        updated_at=environment.updated_at,
    )


@router.get(
    "/environments/{environment_id}", response_model=DeploymentEnvironmentResponse
)
def get_environment(
    environment_id: int,
    db: Session = Depends(get_db),
):
    """
    Get a specific deployment environment by ID.

    Args:
        environment_id: Environment ID
        db: Database session

    Returns:
        Deployment environment

    Raises:
        HTTPException: If environment not found
    """
    environment = (
        db.query(DeploymentEnvironment)
        .filter(DeploymentEnvironment.id == environment_id)
        .first()
    )

    if not environment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment with id {environment_id} not found",
        )

    return DeploymentEnvironmentResponse(
        id=environment.id,
        name=environment.name,
        description=environment.description,
        cloud_platform=environment.cloud_platform,
        has_aws_credentials=bool(
            environment.aws_access_key_id and environment.aws_secret_access_key
        ),
        aws_region=environment.aws_region,
        has_azure_credentials=bool(
            environment.azure_subscription_id
            and environment.azure_tenant_id
            and environment.azure_client_id
            and environment.azure_client_secret
        ),
        is_default=environment.is_default,
        created_at=environment.created_at,
        updated_at=environment.updated_at,
    )


@router.put(
    "/environments/{environment_id}", response_model=DeploymentEnvironmentResponse
)
def update_environment(
    environment_id: int,
    env_data: DeploymentEnvironmentUpdate,
    db: Session = Depends(get_db),
):
    """
    Update a deployment environment.

    Args:
        environment_id: Environment ID
        env_data: Environment update data
        db: Database session

    Returns:
        Updated environment

    Raises:
        HTTPException: If environment not found or name conflict
    """
    environment = (
        db.query(DeploymentEnvironment)
        .filter(DeploymentEnvironment.id == environment_id)
        .first()
    )

    if not environment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment with id {environment_id} not found",
        )

    # Check for name conflict
    if env_data.name and env_data.name != environment.name:
        existing = (
            db.query(DeploymentEnvironment)
            .filter(DeploymentEnvironment.name == env_data.name)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Environment with name '{env_data.name}' already exists",
            )

    # If setting as default, unset other defaults
    if env_data.is_default:
        db.query(DeploymentEnvironment).filter(
            DeploymentEnvironment.id != environment_id,
            DeploymentEnvironment.is_default == True,
        ).update({"is_default": False})

    update_data = env_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(environment, field, value)

    db.commit()
    db.refresh(environment)

    return DeploymentEnvironmentResponse(
        id=environment.id,
        name=environment.name,
        description=environment.description,
        cloud_platform=environment.cloud_platform,
        has_aws_credentials=bool(
            environment.aws_access_key_id and environment.aws_secret_access_key
        ),
        aws_region=environment.aws_region,
        has_azure_credentials=bool(
            environment.azure_subscription_id
            and environment.azure_tenant_id
            and environment.azure_client_id
            and environment.azure_client_secret
        ),
        is_default=environment.is_default,
        created_at=environment.created_at,
        updated_at=environment.updated_at,
    )


@router.delete("/environments/{environment_id}", response_model=SuccessResponse)
def delete_environment(
    environment_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a deployment environment.

    Args:
        environment_id: Environment ID
        db: Database session

    Returns:
        Success response

    Raises:
        HTTPException: If environment not found
    """
    environment = (
        db.query(DeploymentEnvironment)
        .filter(DeploymentEnvironment.id == environment_id)
        .first()
    )

    if not environment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment with id {environment_id} not found",
        )

    db.delete(environment)
    db.commit()

    return SuccessResponse(
        success=True,
        message=f"Environment '{environment.name}' deleted successfully",
    )


# ============ Deployment Operations ============

logger = logging.getLogger(__name__)


@router.post("/plan", response_model=DeploymentPlanResponse)
def create_and_plan(
    request: DeploymentPlanRequest,
    db: Session = Depends(get_db),
):
    """
    Create a deployment and run terraform plan.

    Args:
        request: Plan request with session_id, environment_id, and terraform_code
        db: Database session

    Returns:
        Plan response with plan output and summary

    Raises:
        HTTPException: If environment not found or plan fails
    """
    logger.info(
        f"[DEPLOY] Starting plan for session={request.session_id}, env={request.environment_id}"
    )
    logger.info(
        f"[DEPLOY] Terraform files received: {list(request.terraform_code.keys())}"
    )

    # Verify environment exists
    environment = (
        db.query(DeploymentEnvironment)
        .filter(DeploymentEnvironment.id == request.environment_id)
        .first()
    )
    if not environment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment with id {request.environment_id} not found",
        )

    try:
        executor = TerraformExecutor(db)

        # Validate and fix Azure-specific issues in terraform code before deployment
        from app.services.azure_validator import AzureTerraformValidator

        validated_terraform_code = AzureTerraformValidator.validate_generated_files(
            request.terraform_code
        )
        logger.info(f"[DEPLOY] Terraform code validated by AzureTerraformValidator")

        # Create deployment with validated code
        logger.info(f"[DEPLOY] Creating deployment...")
        deployment = executor.create_deployment(
            session_id=request.session_id,
            environment_id=request.environment_id,
            terraform_code=validated_terraform_code,
        )
        logger.info(f"[DEPLOY] Deployment created: {deployment.deployment_id}")

        # Run plan
        logger.info(f"[DEPLOY] Running terraform plan...")
        deployment = executor.run_plan(deployment.deployment_id)
        logger.info(f"[DEPLOY] Plan completed with status: {deployment.status}")

        plan_summary = PlanSummary(
            add=deployment.plan_summary.get("add", 0) if deployment.plan_summary else 0,
            change=deployment.plan_summary.get("change", 0)
            if deployment.plan_summary
            else 0,
            destroy=deployment.plan_summary.get("destroy", 0)
            if deployment.plan_summary
            else 0,
        )

        if deployment.status == DeploymentStatus.PLAN_FAILED:
            logger.error(f"[DEPLOY] Plan FAILED!")
            logger.error(f"[DEPLOY] Error message: {deployment.error_message}")
            logger.error(
                f"[DEPLOY] Plan output: {deployment.plan_output[:2000] if deployment.plan_output else 'None'}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Terraform plan failed",
                    "deployment_id": deployment.deployment_id,
                    "error": deployment.error_message,
                    "plan_output": deployment.plan_output,
                },
            )

        logger.info(
            f"[DEPLOY] Plan SUCCESS! Summary: add={plan_summary.add}, change={plan_summary.change}, destroy={plan_summary.destroy}"
        )
        return DeploymentPlanResponse(
            deployment_id=deployment.deployment_id,
            status=deployment.status,
            plan_output=deployment.plan_output or "",
            plan_summary=plan_summary,
        )

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/apply", response_model=DeploymentApplyResponse)
def apply_deployment(
    request: DeploymentApplyRequest,
    db: Session = Depends(get_db),
):
    """
    Apply a planned terraform deployment.

    Args:
        request: Apply request with deployment_id
        db: Database session

    Returns:
        Apply response with outputs

    Raises:
        HTTPException: If deployment not found or apply fails
    """
    try:
        print(
            f"[API: Deploy] Apply deployment request received: deployment_id={request.deployment_id}"
        )
        executor = TerraformExecutor(db)
        deployment = executor.run_apply(request.deployment_id)
        print(
            f"[API: Deploy] Deployment apply completed: status={deployment.status}, deployment_id={request.deployment_id}"
        )

        return DeploymentApplyResponse(
            deployment_id=deployment.deployment_id,
            status=deployment.status,
            apply_output=deployment.apply_output,
            terraform_outputs=deployment.terraform_outputs,
            error_message=deployment.error_message,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{deployment_id}", response_model=DeploymentResponse)
def get_deployment(
    deployment_id: str,
    db: Session = Depends(get_db),
):
    """
    Get deployment status and details.

    Args:
        deployment_id: Deployment ID
        db: Database session

    Returns:
        Deployment details

    Raises:
        HTTPException: If deployment not found
    """
    deployment = (
        db.query(Deployment).filter(Deployment.deployment_id == deployment_id).first()
    )

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment {deployment_id} not found",
        )

    plan_summary = None
    if deployment.plan_summary:
        plan_summary = PlanSummary(
            add=deployment.plan_summary.get("add", 0),
            change=deployment.plan_summary.get("change", 0),
            destroy=deployment.plan_summary.get("destroy", 0),
        )

    return DeploymentResponse(
        id=deployment.id,
        deployment_id=deployment.deployment_id,
        session_id=deployment.session_id,
        environment_id=deployment.environment_id,
        status=deployment.status,
        plan_output=deployment.plan_output,
        plan_summary=plan_summary,
        apply_output=deployment.apply_output,
        terraform_outputs=deployment.terraform_outputs,
        error_message=deployment.error_message,
        created_at=deployment.created_at,
        updated_at=deployment.updated_at,
        completed_at=deployment.completed_at,
    )


@router.get("", response_model=List[DeploymentResponse])
def list_deployments(
    session_id: str = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    List deployments.

    Args:
        session_id: Filter by session ID
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session

    Returns:
        List of deployments
    """
    query = db.query(Deployment)

    if session_id:
        query = query.filter(Deployment.session_id == session_id)

    deployments = (
        query.order_by(Deployment.created_at.desc()).offset(skip).limit(limit).all()
    )

    result = []
    for deployment in deployments:
        plan_summary = None
        if deployment.plan_summary:
            plan_summary = PlanSummary(
                add=deployment.plan_summary.get("add", 0),
                change=deployment.plan_summary.get("change", 0),
                destroy=deployment.plan_summary.get("destroy", 0),
            )

        result.append(
            DeploymentResponse(
                id=deployment.id,
                deployment_id=deployment.deployment_id,
                session_id=deployment.session_id,
                environment_id=deployment.environment_id,
                status=deployment.status,
                plan_output=deployment.plan_output,
                plan_summary=plan_summary,
                apply_output=deployment.apply_output,
                terraform_outputs=deployment.terraform_outputs,
                error_message=deployment.error_message,
                created_at=deployment.created_at,
                updated_at=deployment.updated_at,
                completed_at=deployment.completed_at,
            )
        )

    return result


@router.post("/{deployment_id}/destroy", response_model=DeploymentResponse)
def destroy_deployment(
    deployment_id: str,
    db: Session = Depends(get_db),
):
    """
    Destroy resources created by a deployment.

    Args:
        deployment_id: Deployment ID
        db: Database session

    Returns:
        Updated deployment

    Raises:
        HTTPException: If deployment not found or cannot be destroyed
    """
    try:
        executor = TerraformExecutor(db)
        deployment = executor.destroy_resources(deployment_id)

        plan_summary = None
        if deployment.plan_summary:
            plan_summary = PlanSummary(
                add=deployment.plan_summary.get("add", 0),
                change=deployment.plan_summary.get("change", 0),
                destroy=deployment.plan_summary.get("destroy", 0),
            )

        return DeploymentResponse(
            id=deployment.id,
            deployment_id=deployment.deployment_id,
            session_id=deployment.session_id,
            environment_id=deployment.environment_id,
            status=deployment.status,
            plan_output=deployment.plan_output,
            plan_summary=plan_summary,
            apply_output=deployment.apply_output,
            terraform_outputs=deployment.terraform_outputs,
            error_message=deployment.error_message,
            created_at=deployment.created_at,
            updated_at=deployment.updated_at,
            completed_at=deployment.completed_at,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
