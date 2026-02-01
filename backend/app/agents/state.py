"""Agent state definition for LangGraph workflow."""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
from typing_extensions import NotRequired
import operator


class AgentState(TypedDict):
    """
    State object for the IaC generation agent workflow.

    This state is passed between nodes in the LangGraph workflow.
    """

    # Session information
    session_id: str
    user_id: NotRequired[Optional[str]]

    # Conversation
    messages: Annotated[List[Dict[str, str]], operator.add]  # Chat history
    user_input: str  # Latest user input

    # Input type and data
    input_type: NotRequired[str]  # "text" or "excel"
    excel_data: NotRequired[Optional[bytes]]  # Excel file content if uploaded

    # Parsed resources
    resources: NotRequired[List[Dict[str, Any]]]  # Extracted resource definitions
    resource_count: NotRequired[int]

    # Information completeness
    information_complete: NotRequired[bool]
    missing_fields: NotRequired[List[str]]  # List of missing required fields

    # Compliance checking
    compliance_checked: NotRequired[bool]
    compliance_passed: NotRequired[bool]
    compliance_violations: NotRequired[List[Dict[str, Any]]]  # Error-level violations
    compliance_warnings: NotRequired[List[Dict[str, Any]]]  # Warning-level violations

    # Code generation
    generated_code: NotRequired[Dict[str, str]]  # filename -> code content
    generation_summary: NotRequired[str]

    # Code review
    review_passed: NotRequired[bool]  # Whether code review passed
    review_feedback: NotRequired[str]  # Feedback from code reviewer
    review_issues: NotRequired[List[Dict[str, Any]]]  # List of issues found
    review_attempt: NotRequired[int]  # Current review iteration (max 3)

    # Workflow control
    workflow_state: str  # Current workflow stage
    next_action: NotRequired[str]  # What to do next
    should_continue: NotRequired[bool]  # Whether to continue workflow

    # Error handling
    errors: NotRequired[List[str]]
    warnings: NotRequired[List[str]]

    # AI response
    ai_response: NotRequired[str]  # Response to send to user


def create_initial_state(session_id: str, user_input: str) -> AgentState:
    """
    Create initial state for a new workflow execution.

    Args:
        session_id: Session identifier
        user_input: User's input message

    Returns:
        Initial AgentState
    """
    return AgentState(
        session_id=session_id,
        messages=[],
        user_input=user_input,
        workflow_state="initialized",
        resources=[],
        resource_count=0,
        information_complete=False,
        compliance_checked=False,
        compliance_passed=False,
        should_continue=True,
        errors=[],
        warnings=[],
    )
