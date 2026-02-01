# Agent Guidelines for IaC4 Project

This document provides coding guidelines and conventions for AI agents working on the IaC4 project.

## Project Overview

IaC4 is an AI-powered tool that generates Infrastructure as Code (Terraform) for AWS and Azure.
- **Backend**: Python 3.10+ with FastAPI, LangGraph, SQLAlchemy (SQLite/PostgreSQL), Pydantic v2.
- **Frontend**: React 19 with Vite, TypeScript, Material UI (MUI), Zustand.

## Quick Commands

### Backend (`/backend`)
| Action | Command |
|--------|---------|
| **Setup** | `pip install -r requirements.txt` |
| **Env** | `cp .env.example .env` (Edit with keys) |
| **Run** | `uvicorn app.main:app --host 0.0.0.0 --port 8666 --reload` |
| **Lint** | `ruff check .` (Check), `ruff check --fix .` (Fix), `ruff format .` (Format) |
| **DB Apply** | `alembic upgrade head` |
| **DB New** | `alembic revision --autogenerate -m "description"` |

**Testing (Backend)**
*Note: Run from `backend/` directory*
- **Run all tests**: `pytest`
- **Run single file**: `pytest tests/test_file.py`
- **Run single test**: `pytest tests/test_file.py::test_function_name`
- **With coverage**: `pytest --cov=app --cov-report=html`

### Frontend (`/frontend`)
| Action | Command |
|--------|---------|
| **Setup** | `npm install` |
| **Run** | `npm run dev` |
| **Build** | `npm run build` |
| **Lint** | `npm run lint` |

## Backend Code Guidelines

### Organization
- `app/agents/`: LangGraph definitions
- `app/api/`: FastAPI routes
- `app/core/`: Config & Database
- `app/models/`: SQLAlchemy models
- `app/schemas/`: Pydantic schemas (v2)

### Python Style
- **Type Hints**: **Mandatory** for all function arguments and return values.
  ```python
  def get_data(user_id: int) -> Dict[str, Any]: ...
  ```
- **Docstrings**: Triple-quoted docstrings for all modules, classes, and public functions.
- **Imports**: Group into: 1. Standard Lib, 2. Third-party, 3. Local Application.
- **Naming**: `PascalCase` classes, `snake_case` functions/vars, `UPPER_CASE` constants.
- **Async**: Use `async def` for DB operations and external API calls.

### Pydantic & Models
- Use Pydantic v2 styles (`model_validate`, `field_validator`).
- Enable ORM mode: `model_config = ConfigDict(from_attributes=True)`.
- SQLAlchemy models must inherit from `Base` and define `__tablename__`.

### Error Handling
- Use `fastapi.HTTPException` for API errors.
- Return appropriate status codes (400, 401, 403, 404, 500).

## Frontend Code Guidelines

### Stack
- **Framework**: React 19 + Vite
- **Language**: TypeScript (Strict mode)
- **UI Library**: Material UI (MUI) v6
- **State**: Zustand for global state, local `useState` for UI state.

### React/TS Style
- **Components**: Functional components only. Use PascalCase files (`UserProfile.tsx`).
- **Props**: Define strict Interfaces for props. Avoid `any`.
  ```typescript
  interface Props {
    title: string;
    isActive?: boolean;
  }
  ```
- **Styling**: Prefer MUI `sx` prop for one-offs, or `@emotion/styled` for reusable components.
- **Hooks**: Custom hooks must start with `use`.

## Critical Instructions for Agents

1. **Test Safety**: Always verify changes by running relevant tests. If no test exists, create a basic one in `backend/tests/`.
2. **Secrets**: NEVER commit secrets (API keys, passwords). Use `.env`.
3. **Paths**: Use absolute paths for file operations.
4. **Agent Framework**: This project uses LangGraph. Do not introduce LangChain agents unless wrapped in LangGraph nodes.
5. **Context**: Read `backend/app/core/config.py` to understand available settings before modifying logic.
