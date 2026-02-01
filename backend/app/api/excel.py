"""Excel processing API routes."""

import io
import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Response
from app.schemas import ExcelParseResult, TemplateType
from app.services.excel_parser import ExcelParserService
from app.services.excel_generator import ExcelGeneratorService

router = APIRouter()

# Initialize services
excel_parser = ExcelParserService()
excel_generator = ExcelGeneratorService()


@router.post("/upload", response_model=ExcelParseResult)
async def upload_excel(
    file: UploadFile = File(...),
):
    """
    Upload and parse Excel file containing resource definitions.

    Args:
        file: Uploaded Excel file

    Returns:
        Parsed resource information

    Raises:
        HTTPException: If file format is invalid or parsing fails
    """
    # Validate file type
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only .xlsx and .xls files are supported",
        )

    # Check file size (10MB limit from settings)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 10MB limit",
        )

    # Parse Excel file
    result = excel_parser.parse_excel_file(content)

    if not result.success and result.errors:
        # If parsing failed critically (e.g. invalid file format), we might want to raise 400
        # However, the schema allows returning errors in the body, which is often better for UI
        pass

    return result


@router.get("/template")
async def download_template(
    template_type: TemplateType = TemplateType.FULL,
):
    """
    Download Excel template for resource definitions.

    Args:
        template_type: Type of template (AWS, Azure, or Full)

    Returns:
        Excel template file
    """
    # Generate template
    content = excel_generator.generate_template(template_type)

    # Create filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d")
    filename = f"iac_template_{template_type.value}_{timestamp}.xlsx"

    # Return file response
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
