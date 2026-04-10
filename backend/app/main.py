"""FastAPI main application entry point."""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.database import engine, Base
from app.core.security import get_current_user
from app.api import (
    auth,
    policies,
    llm_config,
    sessions,
    chat,
    excel,
    generate,
    health,
    deployments,
)

settings = get_settings()

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI application
app = FastAPI(
    title="Cloud IaC Code Generator with Agentic AI",
    description="AI-driven tool to generate Infrastructure as Code for AWS and Azure platforms",
    version="1.0.0",
    debug=settings.DEBUG,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(
    policies.router,
    prefix="/api/policies",
    tags=["Security Policies"],
    dependencies=[Depends(get_current_user)],
)
app.include_router(
    llm_config.router,
    prefix="/api/llm-config",
    tags=["LLM Configuration"],
    dependencies=[Depends(get_current_user)],
)
app.include_router(
    sessions.router,
    prefix="/api/sessions",
    tags=["Sessions"],
    dependencies=[Depends(get_current_user)],
)
app.include_router(
    chat.router,
    prefix="/api/chat",
    tags=["Chat"],
    dependencies=[Depends(get_current_user)],
)
app.include_router(
    excel.router,
    prefix="/api/excel",
    tags=["Excel Processing"],
    dependencies=[Depends(get_current_user)],
)
app.include_router(
    generate.router,
    prefix="/api/generate",
    tags=["Code Generation"],
    dependencies=[Depends(get_current_user)],
)
app.include_router(
    deployments.router,
    prefix="/api/deployments",
    tags=["Deployments"],
    dependencies=[Depends(get_current_user)],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Cloud IaC Code Generator API",
        "version": "1.0.0",
        "docs": "/docs",
    }
