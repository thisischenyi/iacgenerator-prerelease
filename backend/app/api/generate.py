"""Code generation API routes."""

import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Session, User
from app.schemas import CodeGenerationResult, GeneratedCode, ResourceCollection
from app.services.terraform_generator import TerraformCodeGenerator
from app.services.file_utils import FileUtilsService

router = APIRouter()
file_utils = FileUtilsService()


@router.get("/download/{filename}")
async def download_file(filename: str):
    """
    Download a generated ZIP file.

    Args:
        filename: Name of the file to download

    Returns:
        FileResponse with the ZIP file
    """
    # Sanitize filename to prevent directory traversal
    filename = os.path.basename(filename)
    file_path = os.path.join(file_utils.output_dir, filename)

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    return FileResponse(path=file_path, filename=filename, media_type="application/zip")


@router.post("", response_model=CodeGenerationResult)
async def generate_code(
    resources: ResourceCollection,
    session_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """
    Generate IaC code from resource definitions.

    Args:
        resources: Resource collection
        session_id: Optional session ID to associate generation with
        db: Database session

    Returns:
        Generated code files

    Raises:
        HTTPException: If generation fails
    """
    # Validate session if provided
    if session_id:
        session = db.query(Session).filter(Session.session_id == session_id).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session with id {session_id} not found",
            )
        if session.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to use this session",
            )

    if not resources.resources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No resources provided for code generation",
        )

    try:
        # Initialize Terraform code generator
        generator = TerraformCodeGenerator()

        # Convert Pydantic models to dicts for template rendering
        resources_dict = [r.model_dump() for r in resources.resources]

        # Generate Terraform code
        generated_files = generator.generate_code(resources_dict)

        # Create ZIP file
        zip_bytes, zip_filename = file_utils.create_zip_from_files(generated_files)
        file_utils.save_zip_to_disk(zip_bytes, zip_filename)

        # Clean up old files occasionally
        try:
            file_utils.cleanup_old_files()
        except Exception:
            pass

        # Convert to GeneratedCode schema
        code_files = [
            GeneratedCode(
                filename=filename,
                content=content,
                language="hcl" if filename.endswith(".tf") else "markdown",
            )
            for filename, content in generated_files.items()
        ]

        # Create summary
        resource_counts = {}
        for resource in resources.resources:
            rt = resource.resource_type
            resource_counts[rt] = resource_counts.get(rt, 0) + 1

        summary_lines = [
            f"Generated {len(code_files)} Terraform files",
            f"Total resources: {len(resources.resources)}",
            "Resource breakdown: "
            + ", ".join([f"{count}x {rt}" for rt, count in resource_counts.items()]),
        ]
        summary = " | ".join(summary_lines)

        # Construct download URL
        # Assuming API is served at /api/generate
        download_url = f"/api/generate/download/{zip_filename}"

        return CodeGenerationResult(
            success=True, files=code_files, summary=summary, download_url=download_url
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Code generation failed: {str(e)}",
        )
