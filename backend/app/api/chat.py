"""Chat API routes."""

import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Session, User
from app.schemas import ChatRequest, ChatResponse
from app.agents.workflow import IaCAgentWorkflow

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=ChatResponse)
async def chat(
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """
    Process chat message through LangGraph agent.

    Args:
        chat_request: Chat request
        db: Database session

    Returns:
        Chat response
    """
    logger.info("[API:Chat] Received chat request | session=%s | message=%.100s", chat_request.session_id, chat_request.message)

    # Get or create session
    if chat_request.session_id:
        session = (
            db.query(Session)
            .filter(Session.session_id == chat_request.session_id)
            .first()
        )
        if not session:
            logger.warning("[API:Chat] Session %s not found", chat_request.session_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session with id {chat_request.session_id} not found",
            )
        if session.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to use this session",
            )
        logger.debug("[API:Chat] Session found: %s", session.session_id)
    else:
        logger.warning("[API:Chat] Session ID missing in request")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session ID is required",
        )

    try:
        # Initialize workflow
        logger.debug("[API:Chat] Initializing IaCAgentWorkflow")
        workflow = IaCAgentWorkflow(db)

        # Check if Excel resources are provided in context
        excel_resources = None
        if chat_request.context and "excel_resources" in chat_request.context:
            excel_resources = chat_request.context["excel_resources"]
            logger.debug("[API:Chat] Excel resources found: %d resources", len(excel_resources))
        else:
            logger.debug("[API:Chat] No Excel resources in context")

        logger.info("[API:Chat] Executing workflow for session %s", session.session_id)
        # Execute workflow
        final_state = workflow.run(
            session_id=session.session_id,
            user_input=chat_request.message,
            excel_data=None,
            excel_resources=excel_resources,
        )
        logger.info("[API:Chat] Workflow execution completed")
        logger.debug("[API:Chat] Final state: %s", final_state.get('workflow_state'))

        # Get latest message from state
        messages = final_state.get("messages", [])
        logger.debug("[API:Chat] Total messages: %d", len(messages))
        last_message = ""
        if messages:
            for msg in reversed(messages):
                if isinstance(msg, dict):
                    if msg.get("role") == "assistant":
                        last_message = msg.get("content", "")
                        break
                elif hasattr(msg, "content"):
                    if msg.type == "ai":
                        last_message = msg.content
                        break

        logger.debug("[API:Chat] Last AI message: %.100s", last_message)

        # Prepare code blocks if code was generated
        code_blocks = None
        generated_code = final_state.get("generated_code")

        if generated_code:
            logger.debug("[API:Chat] Generated code files: %s", list(generated_code.keys()))
            code_blocks = [
                {"filename": filename, "content": content, "language": "hcl"}
                for filename, content in generated_code.items()
            ]
            logger.debug("[API:Chat] Prepared %d code blocks", len(code_blocks))
        else:
            logger.debug("[API:Chat] No generated code in final state")

        response = ChatResponse(
            session_id=session.session_id,
            message=last_message,
            code_blocks=code_blocks,
            metadata={
                "workflow_state": final_state.get("workflow_state"),
                "message_count": len(messages) if messages else 0,
                "resource_count": len(final_state.get("resources", [])),
                "compliance_passed": final_state.get("compliance_results", {}).get(
                    "passed", False
                ),
            },
        )

        logger.info("[API:Chat] Response prepared successfully")
        
        return response

    except Exception:
        logger.exception("[API:Chat] Unhandled exception processing chat message")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while processing your message.",
        )


@router.post("/stream")
async def chat_stream(
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """
    Process chat message with streaming progress updates via SSE.
    """
    logger.info("[API:ChatStream] Received streaming request | session=%s", chat_request.session_id)

    if not chat_request.session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session ID is required",
        )

    session = (
        db.query(Session).filter(Session.session_id == chat_request.session_id).first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id {chat_request.session_id} not found",
        )
    if session.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to use this session",
        )

    async def generate_events():
        """Generate SSE events from agent progress."""
        import asyncio
        from app.agents.progress import ProgressTracker, ProgressEvent

        # Use a queue to bridge sync callbacks to async generator
        queue = asyncio.Queue()

        # Capture the running loop before the callback closure uses it
        loop = asyncio.get_running_loop()

        # Define callback for ProgressTracker
        def progress_callback(event: ProgressEvent):
            # This runs in the workflow thread
            loop.call_soon_threadsafe(queue.put_nowait, event)

        # Register callback
        ProgressTracker.register_callback(
            str(chat_request.session_id), progress_callback
        )

        # Run workflow in thread pool
        import concurrent.futures

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        final_state_container = {"state": None, "error": None}

        def run_workflow():
            try:
                workflow = IaCAgentWorkflow(db)
                excel_resources = None
                if chat_request.context and "excel_resources" in chat_request.context:
                    excel_resources = chat_request.context["excel_resources"]

                final_state_container["state"] = workflow.run(
                    session_id=str(chat_request.session_id),
                    user_input=chat_request.message,
                    excel_data=None,
                    excel_resources=excel_resources,
                )
            except Exception as e:
                import traceback

                traceback.print_exc()
                final_state_container["error"] = str(e)

        # Start workflow
        workflow_future = loop.run_in_executor(executor, run_workflow)

        try:
            # While workflow is running, yield events from queue
            while not workflow_future.done() or not queue.empty():
                try:
                    # Wait for an event with timeout to check workflow status
                    event = await asyncio.wait_for(queue.get(), timeout=0.1)
                    yield _sse_event("progress", event.to_dict())
                except asyncio.TimeoutError:
                    continue

            # Workflow finished
            await workflow_future

            if final_state_container["error"]:
                yield _sse_event("error", {"message": final_state_container["error"]})
            elif final_state_container["state"]:
                state = final_state_container["state"]

                # Build final response
                messages = state.get("messages", [])
                last_message = ""
                for msg in reversed(messages):
                    if isinstance(msg, dict) and msg.get("role") == "assistant":
                        last_message = msg.get("content", "")
                        break

                code_blocks = None
                generated_code = state.get("generated_code")
                if generated_code:
                    code_blocks = [
                        {"filename": filename, "content": content, "language": "hcl"}
                        for filename, content in generated_code.items()
                    ]

                yield _sse_event(
                    "complete",
                    {
                        "session_id": chat_request.session_id,
                        "message": last_message,
                        "code_blocks": code_blocks,
                        "metadata": {
                            "workflow_state": state.get("workflow_state"),
                            "resource_count": len(state.get("resources", [])),
                        },
                    },
                )
        finally:
            # Unregister callback
            ProgressTracker.unregister_callback(str(chat_request.session_id))
            executor.shutdown(wait=False)

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse_event(event_type: str, data: dict) -> str:
    """Format SSE event."""
    data_str = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {data_str}\n\n"

