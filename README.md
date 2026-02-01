# Cloud IaC Generator

An AI-powered tool to generate Infrastructure as Code (Terraform) for AWS and Azure.

## Project Overview

This project consists of a Python FastAPI backend and a React/Vite frontend. It uses AI agents (powered by LangGraph) to understand user requirements via chat or Excel files and generates compliant Terraform code.

### Key Features
- **AI Chat Interface:** Conversational interface to describe infrastructure needs.
- **Excel Upload:** Bulk generation from structured Excel templates.
- **Policy Management:** Define and enforce security policies (e.g., block specific ports).
- **Code Generation:** Generates `provider.tf`, `variables.tf`, `main.tf`, `outputs.tf`, and `README.md`.
- **Multi-Cloud Support:** AWS and Azure.
- **Automated Deployment:** Directly plan and apply Terraform configurations to cloud environments.

## Project Structure

- `backend/`: FastAPI application, AI agents, database models.
- `frontend/`: React application, UI components.
- `iac_generator.db`: SQLite database (auto-created).

## How to Run

### Prerequisites
- Python 3.10+
- Node.js 18+
- Terraform CLI (must be in system PATH)
- OpenAI API Key (configured in `backend/.env`)

### Backend Setup

1.  Navigate to the backend directory:
    ```bash
    cd backend
    ```
2.  Create a virtual environment (optional but recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Configure environment variables:
    *   Copy `.env.example` to `.env` (if available, otherwise create one).
    *   Set `OPENAI_API_KEY=your_api_key`.
5.  Run the server:
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8666 --reload
    ```
    The API will be available at `http://localhost:8666`. API Docs at `http://localhost:8666/docs`.

### Frontend Setup

1.  Navigate to the frontend directory:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Run the development server:
    ```bash
    npm run dev
    ```
    The application will be available at `http://localhost:5173` (or the port shown in the terminal).

## Testing

### Backend Tests
Run tests from the `backend/` directory:
```bash
pytest
```
Or run the complete flow test script:
```bash
python test_complete_flow.py
```

## Documentation
- `AGENTS.md`: Guidelines for AI agents.
- `API_ENDPOINTS.md`: API documentation.
- `req_spec.md`: Requirements specification.
