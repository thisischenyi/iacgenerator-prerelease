"""Terraform execution service.

This service handles terraform init, plan, and apply operations.
"""

import os
import re
import json
import shutil
import subprocess
import tempfile
import uuid
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple, Any

from sqlalchemy.orm import Session

from app.models import DeploymentEnvironment, Deployment, DeploymentStatus

logger = logging.getLogger(__name__)


class TerraformExecutor:
    """Service for executing Terraform commands."""

    def __init__(self, db: Session):
        """Initialize the executor.

        Args:
            db: Database session for storing deployment state
        """
        self.db = db
        self.terraform_bin = self._find_terraform_binary()

    def _find_terraform_binary(self) -> str:
        """Find the terraform binary path.

        Returns:
            Path to terraform binary

        Raises:
            RuntimeError: If terraform is not installed
        """
        # Try common locations
        if os.name == "nt":  # Windows
            terraform_paths = [
                shutil.which("terraform"),
                r"C:\terraform\terraform.exe",
                os.path.expanduser(r"~\terraform\terraform.exe"),
            ]

            # Add Winget path search
            local_app_data = os.environ.get("LOCALAPPDATA", "")
            if local_app_data:
                winget_packages = os.path.join(
                    local_app_data, "Microsoft", "WinGet", "Packages"
                )
                if os.path.exists(winget_packages):
                    for item in os.listdir(winget_packages):
                        if "Hashicorp.Terraform" in item:
                            tf_path = os.path.join(
                                winget_packages, item, "terraform.exe"
                            )
                            if os.path.exists(tf_path):
                                terraform_paths.append(tf_path)
        else:  # Unix/Linux/Mac
            terraform_paths = [
                shutil.which("terraform"),
                "/usr/local/bin/terraform",
                "/usr/bin/terraform",
                os.path.expanduser("~/.local/bin/terraform"),
            ]

        for path in terraform_paths:
            if path and os.path.isfile(path):
                return path

        raise RuntimeError(
            "Terraform CLI not found. Please install Terraform and ensure it's in PATH."
        )

    def _prepare_work_dir(
        self, terraform_code: Dict[str, str], deployment_id: str
    ) -> str:
        """Prepare a working directory with terraform files.

        Args:
            terraform_code: Dictionary of filename -> content
            deployment_id: Unique deployment ID for directory naming

        Returns:
            Path to the working directory
        """
        # Create a temp directory for this deployment
        work_dir = os.path.join(
            tempfile.gettempdir(), "iac4_deployments", deployment_id
        )
        os.makedirs(work_dir, exist_ok=True)

        # Write all terraform files
        for filename, content in terraform_code.items():
            filepath = os.path.join(work_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

        return work_dir

    def _get_env_variables(self, environment: DeploymentEnvironment) -> Dict[str, str]:
        """Get environment variables for terraform execution.

        Args:
            environment: Deployment environment configuration

        Returns:
            Dictionary of environment variables
        """
        env = os.environ.copy()

        if environment.cloud_platform.value == "aws":
            if environment.aws_access_key_id:
                env["AWS_ACCESS_KEY_ID"] = environment.aws_access_key_id
            if environment.aws_secret_access_key:
                env["AWS_SECRET_ACCESS_KEY"] = environment.aws_secret_access_key
            if environment.aws_region:
                env["AWS_DEFAULT_REGION"] = environment.aws_region

        elif environment.cloud_platform.value == "azure":
            if environment.azure_subscription_id:
                env["ARM_SUBSCRIPTION_ID"] = environment.azure_subscription_id
                # Also set as TF_VAR for the provider configuration
                env["TF_VAR_azure_subscription_id"] = environment.azure_subscription_id
            if environment.azure_tenant_id:
                env["ARM_TENANT_ID"] = environment.azure_tenant_id
            if environment.azure_client_id:
                env["ARM_CLIENT_ID"] = environment.azure_client_id
            if environment.azure_client_secret:
                env["ARM_CLIENT_SECRET"] = environment.azure_client_secret

        return env

    def _cleanup_lock_files(self, work_dir: str) -> None:
        """Remove terraform lock files to prevent deadlocks.

        Args:
            work_dir: Working directory containing terraform files
        """
        lock_file = os.path.join(work_dir, ".terraform.tfstate.lock.info")
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
                logger.info(f"[TF] Removed stale lock file: {lock_file}")
            except Exception as e:
                logger.warning(f"[TF] Failed to remove lock file: {e}")

    def _run_command(
        self,
        args: list,
        work_dir: str,
        env: Dict[str, str],
        timeout: int = 600,
    ) -> Tuple[int, str, str]:
        """Run a command and return output.

        Args:
            args: Command arguments
            work_dir: Working directory
            env: Environment variables
            timeout: Command timeout in seconds

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        try:
            # Use encoding='utf-8' explicitly for Windows compatibility
            # Terraform outputs UTF-8, but Windows default is often GBK/CP936
            result = subprocess.run(
                args,
                cwd=work_dir,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",  # Replace undecodable bytes instead of failing
                timeout=timeout,
            )
            return result.returncode, result.stdout or "", result.stderr or ""
        except subprocess.TimeoutExpired:
            # Clean up lock files on timeout to prevent deadlocks
            self._cleanup_lock_files(work_dir)
            return -1, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return -1, "", str(e)

    def _parse_plan_output(self, plan_output: str) -> Dict[str, int]:
        """Parse terraform plan output to extract resource counts.

        Args:
            plan_output: Raw terraform plan output

        Returns:
            Dictionary with add, change, destroy counts
        """
        summary = {"add": 0, "change": 0, "destroy": 0}

        # Look for the plan summary line like:
        # "Plan: 2 to add, 1 to change, 0 to destroy."
        match = re.search(
            r"Plan: (\d+) to add, (\d+) to change, (\d+) to destroy",
            plan_output,
        )
        if match:
            summary["add"] = int(match.group(1))
            summary["change"] = int(match.group(2))
            summary["destroy"] = int(match.group(3))

        return summary

    def create_deployment(
        self,
        session_id: str,
        environment_id: int,
        terraform_code: Dict[str, str],
    ) -> Deployment:
        """Create a new deployment record.

        Args:
            session_id: Chat session ID
            environment_id: Target environment ID
            terraform_code: Terraform files to deploy

        Returns:
            Created Deployment object
        """
        deployment_id = f"dep_{uuid.uuid4().hex[:16]}"

        deployment = Deployment(
            deployment_id=deployment_id,
            session_id=session_id,
            environment_id=environment_id,
            status=DeploymentStatus.PENDING,
            terraform_code=terraform_code,
        )

        self.db.add(deployment)
        self.db.commit()
        self.db.refresh(deployment)

        return deployment

    def run_plan(self, deployment_id: str) -> Deployment:
        """Run terraform init and plan.

        Args:
            deployment_id: Deployment ID

        Returns:
            Updated Deployment object with plan results

        Raises:
            ValueError: If deployment or environment not found
        """
        logger.info(f"[TF] run_plan called for deployment_id={deployment_id}")

        deployment = (
            self.db.query(Deployment)
            .filter(Deployment.deployment_id == deployment_id)
            .first()
        )
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        environment = (
            self.db.query(DeploymentEnvironment)
            .filter(DeploymentEnvironment.id == deployment.environment_id)
            .first()
        )
        if not environment:
            raise ValueError(f"Environment {deployment.environment_id} not found")

        logger.info(
            f"[TF] Environment: {environment.name}, Platform: {environment.cloud_platform}"
        )

        # Update status
        deployment.status = DeploymentStatus.PLANNING
        self.db.commit()

        try:
            # Prepare working directory
            work_dir = self._prepare_work_dir(
                deployment.terraform_code, deployment.deployment_id
            )
            deployment.work_dir = work_dir
            self.db.commit()

            logger.info(f"[TF] Work directory: {work_dir}")
            logger.info(
                f"[TF] Terraform files: {list(deployment.terraform_code.keys()) if deployment.terraform_code else 'None'}"
            )

            # Log main.tf content for debugging
            if deployment.terraform_code and "main.tf" in deployment.terraform_code:
                main_tf = deployment.terraform_code["main.tf"]
                logger.info(f"[TF] main.tf content ({len(main_tf)} chars):")
                # Log first 1000 chars
                for line in main_tf[:1500].split("\n"):
                    logger.info(f"[TF]   {line}")
                if len(main_tf) > 1500:
                    logger.info(
                        f"[TF]   ... (truncated, {len(main_tf) - 1500} more chars)"
                    )

            # Get environment variables
            env = self._get_env_variables(environment)
            logger.info(
                f"[TF] Environment variables set: {[k for k in env.keys() if k.startswith(('ARM_', 'AWS_', 'TF_'))]}"
            )

            # Run terraform init
            logger.info(f"[TF] Running terraform init...")
            returncode, stdout, stderr = self._run_command(
                [self.terraform_bin, "init", "-no-color", "-input=false"],
                work_dir,
                env,
                timeout=900,  # 15 minutes for provider downloads
            )
            logger.info(f"[TF] terraform init returncode: {returncode}")

            if returncode != 0:
                logger.error(f"[TF] terraform init FAILED!")
                logger.error(f"[TF] stdout: {stdout[:1000]}")
                logger.error(f"[TF] stderr: {stderr[:1000]}")
                deployment.status = DeploymentStatus.PLAN_FAILED
                deployment.error_message = f"terraform init failed:\n{stderr or stdout}"
                self.db.commit()
                return deployment

            # Run terraform plan
            logger.info(f"[TF] Running terraform plan...")
            returncode, stdout, stderr = self._run_command(
                [
                    self.terraform_bin,
                    "plan",
                    "-no-color",
                    "-input=false",
                    "-out=tfplan",
                ],
                work_dir,
                env,
                timeout=1800,  # 30 minutes for complex deployments
            )

            plan_output = stdout + stderr
            logger.info(f"[TF] terraform plan returncode: {returncode}")

            if returncode != 0:
                logger.error(f"[TF] terraform plan FAILED!")
                logger.error(f"[TF] Plan output (first 2000 chars):")
                for line in plan_output[:2000].split("\n"):
                    logger.error(f"[TF]   {line}")
                if len(plan_output) > 2000:
                    logger.error(
                        f"[TF] ... (truncated {len(plan_output) - 4000} chars) ..."
                    )
                    logger.error(f"[TF] Plan output (last 2000 chars):")
                    for line in plan_output[-2000:].split("\n"):
                        logger.error(f"[TF]   {line}")
                deployment.status = DeploymentStatus.PLAN_FAILED
                deployment.plan_output = plan_output
                deployment.error_message = "terraform plan failed"
                self.db.commit()
                return deployment

            # Parse plan output
            plan_summary = self._parse_plan_output(plan_output)
            logger.info(f"[TF] Plan SUCCESS! Summary: {plan_summary}")

            deployment.status = DeploymentStatus.PLAN_READY
            deployment.plan_output = plan_output
            deployment.plan_summary = plan_summary
            self.db.commit()

            return deployment

        except Exception as e:
            logger.exception(f"[TF] Exception during plan: {e}")
            deployment.status = DeploymentStatus.PLAN_FAILED
            deployment.error_message = str(e)
            self.db.commit()
            return deployment

    def run_apply(self, deployment_id: str) -> Deployment:
        """Run terraform apply.

        Args:
            deployment_id: Deployment ID

        Returns:
            Updated Deployment object with apply results

        Raises:
            ValueError: If deployment not found or not in PLAN_READY state
        """
        # 1. Function start - print deployment_id and status
        logger.info(f"[TF] run_apply called for deployment_id={deployment_id}")

        deployment = (
            self.db.query(Deployment)
            .filter(Deployment.deployment_id == deployment_id)
            .first()
        )
        # 2. After deployment lookup - print if found or not
        if not deployment:
            logger.error(f"[TF] Deployment {deployment_id} NOT FOUND")
            raise ValueError(f"Deployment {deployment_id} not found")
        logger.info(
            f"[TF] Deployment found: id={deployment.id}, status={deployment.status}"
        )

        # 3. After status check - print current status
        current_status = deployment.status
        logger.info(f"[TF] Current deployment status: {current_status}")
        if deployment.status != DeploymentStatus.PLAN_READY:
            logger.error(
                f"[TF] Invalid status for apply: expected PLAN_READY, got {current_status}"
            )
            raise ValueError(
                f"Deployment must be in PLAN_READY state, current: {deployment.status}"
            )
        logger.info(f"[TF] Status check passed - deployment is ready for apply")

        environment = (
            self.db.query(DeploymentEnvironment)
            .filter(DeploymentEnvironment.id == deployment.environment_id)
            .first()
        )
        # 4. After environment lookup - print environment details
        if not environment:
            logger.error(f"[TF] Environment {deployment.environment_id} NOT FOUND")
            raise ValueError(f"Environment {deployment.environment_id} not found")
        logger.info(
            f"[TF] Environment found: id={environment.id}, name={environment.name}, platform={environment.cloud_platform}"
        )

        # Update status
        deployment.status = DeploymentStatus.APPLYING
        self.db.commit()
        logger.info(f"[TF] Deployment status updated to APPLYING")

        try:
            work_dir = deployment.work_dir
            if not work_dir or not os.path.exists(work_dir):
                logger.error(f"[TF] Working directory not found or invalid: {work_dir}")
                raise ValueError("Working directory not found")
            logger.info(f"[TF] Working directory verified: {work_dir}")

            env = self._get_env_variables(environment)
            logger.info(
                f"[TF] Environment variables configured for {environment.cloud_platform}"
            )

            # 5. Before terraform apply - print work_dir and command
            apply_cmd = [
                self.terraform_bin,
                "apply",
                "-no-color",
                "-input=false",
                "-auto-approve",
                "tfplan",
            ]
            logger.info(f"[TF] Preparing terraform apply")
            logger.info(f"[TF] Work directory: {work_dir}")
            logger.info(f"[TF] Command: {' '.join(apply_cmd)}")

            # 6. During apply execution - print when command starts
            logger.info(f"[TF] Starting terraform apply execution...")
            # Run terraform apply with the saved plan
            returncode, stdout, stderr = self._run_command(
                apply_cmd,
                work_dir,
                env,
                timeout=1800,  # 30 minutes for apply
            )

            apply_output = stdout + stderr

            # 7. After apply completes - print returncode and output length
            logger.info(f"[TF] terraform apply completed - returncode: {returncode}")
            logger.info(
                f"[TF] Apply output length: stdout={len(stdout)} chars, stderr={len(stderr)} chars"
            )

            if returncode != 0:
                # 8. If apply fails - print error details
                logger.error(f"[TF] terraform apply FAILED!")
                logger.error(f"[TF] Apply output (first 2000 chars):")
                for line in apply_output[:2000].split("\n"):
                    logger.error(f"[TF]   {line}")
                if len(apply_output) > 2000:
                    logger.error(
                        f"[TF] ... (truncated, {len(apply_output) - 2000} more chars)"
                    )
                deployment.status = DeploymentStatus.APPLY_FAILED
                deployment.apply_output = apply_output
                deployment.error_message = "terraform apply failed"
                self.db.commit()
                logger.info(f"[TF] Deployment status updated to APPLY_FAILED")
                return deployment

            logger.info(f"[TF] terraform apply SUCCESS")

            # 9. Before getting outputs - print command
            output_cmd = [self.terraform_bin, "output", "-json"]
            logger.info(f"[TF] Getting terraform outputs")
            logger.info(f"[TF] Command: {' '.join(output_cmd)}")
            # Get terraform outputs
            returncode, stdout, stderr = self._run_command(
                output_cmd,
                work_dir,
                env,
            )

            terraform_outputs = {}
            # 10. After getting outputs - print success/failure
            logger.info(
                f"[TF] terraform output command completed - returncode: {returncode}"
            )
            if returncode == 0 and stdout.strip():
                try:
                    terraform_outputs = json.loads(stdout)
                    logger.info(
                        f"[TF] Successfully parsed terraform outputs - {len(terraform_outputs)} output(s) found"
                    )
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"[TF] Failed to parse terraform outputs as JSON: {e}"
                    )
            else:
                logger.warning(
                    f"[TF] terraform output command failed or returned empty - returncode: {returncode}"
                )

            deployment.status = DeploymentStatus.APPLY_SUCCESS
            deployment.apply_output = apply_output
            deployment.terraform_outputs = terraform_outputs
            deployment.completed_at = datetime.utcnow()
            self.db.commit()

            # 11. Final status update - print final status
            logger.info(f"[TF] Deployment status updated to APPLY_SUCCESS")
            logger.info(f"[TF] Deployment completed at: {deployment.completed_at}")
            logger.info(
                f"[TF] run_apply finished successfully for deployment_id={deployment_id}"
            )

            return deployment

        except Exception as e:
            logger.exception(f"[TF] Exception during apply: {e}")
            deployment.status = DeploymentStatus.APPLY_FAILED
            deployment.error_message = str(e)
            self.db.commit()
            logger.info(
                f"[TF] Deployment status updated to APPLY_FAILED due to exception"
            )
            return deployment

    def get_deployment(self, deployment_id: str) -> Optional[Deployment]:
        """Get deployment by ID.

        Args:
            deployment_id: Deployment ID

        Returns:
            Deployment object or None
        """
        return (
            self.db.query(Deployment)
            .filter(Deployment.deployment_id == deployment_id)
            .first()
        )

    def list_deployments(
        self, session_id: Optional[str] = None, limit: int = 50
    ) -> list:
        """List deployments.

        Args:
            session_id: Filter by session ID
            limit: Maximum number of results

        Returns:
            List of Deployment objects
        """
        query = self.db.query(Deployment)

        if session_id:
            query = query.filter(Deployment.session_id == session_id)

        return query.order_by(Deployment.created_at.desc()).limit(limit).all()

    def cleanup_deployment(self, deployment_id: str) -> bool:
        """Clean up deployment working directory.

        Args:
            deployment_id: Deployment ID

        Returns:
            True if cleanup successful
        """
        deployment = self.get_deployment(deployment_id)
        if not deployment or not deployment.work_dir:
            return False

        try:
            if os.path.exists(deployment.work_dir):
                shutil.rmtree(deployment.work_dir)
            return True
        except Exception:
            return False

    def destroy_resources(self, deployment_id: str) -> Deployment:
        """Run terraform destroy.

        Args:
            deployment_id: Deployment ID

        Returns:
            Updated Deployment object

        Raises:
            ValueError: If deployment not found
        """
        deployment = self.get_deployment(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        if deployment.status != DeploymentStatus.APPLY_SUCCESS:
            raise ValueError("Can only destroy successfully applied deployments")

        environment = (
            self.db.query(DeploymentEnvironment)
            .filter(DeploymentEnvironment.id == deployment.environment_id)
            .first()
        )
        if not environment:
            raise ValueError(f"Environment {deployment.environment_id} not found")

        work_dir = deployment.work_dir
        if not work_dir or not os.path.exists(work_dir):
            # Recreate the working directory from stored code
            work_dir = self._prepare_work_dir(
                deployment.terraform_code, deployment.deployment_id
            )
            deployment.work_dir = work_dir

            # Need to reinitialize
            env = self._get_env_variables(environment)
            self._run_command([self.terraform_bin, "init", "-no-color"], work_dir, env)

        env = self._get_env_variables(environment)

        returncode, stdout, stderr = self._run_command(
            [
                self.terraform_bin,
                "destroy",
                "-no-color",
                "-input=false",
                "-auto-approve",
            ],
            work_dir,
            env,
            timeout=1800,
        )

        if returncode == 0:
            deployment.status = DeploymentStatus.DESTROYED
            deployment.apply_output = (
                deployment.apply_output or ""
            ) + f"\n\n--- DESTROY OUTPUT ---\n{stdout}{stderr}"
        else:
            deployment.error_message = f"terraform destroy failed:\n{stderr or stdout}"

        self.db.commit()
        return deployment
