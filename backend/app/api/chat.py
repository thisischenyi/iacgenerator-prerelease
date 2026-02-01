"""Chat API routes."""

import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.models import Session
from app.schemas import ChatRequest, ChatResponse
from app.agents.workflow import IaCAgentWorkflow

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat(
    chat_request: ChatRequest,
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
    print("\n" + "=" * 80)
    print(f"[API:Chat] Received chat request")
    print(f"[API:Chat] Session ID: {chat_request.session_id}")
    print(f"[API:Chat] Message: {chat_request.message[:100]}...")
    print("=" * 80)

    # Get or create session
    if chat_request.session_id:
        session = (
            db.query(Session)
            .filter(Session.session_id == chat_request.session_id)
            .first()
        )
        if not session:
            print(f"[API:Chat] ERROR: Session {chat_request.session_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session with id {chat_request.session_id} not found",
            )
        print(f"[API:Chat] Session found: {session.session_id}")
    else:
        print("[API:Chat] ERROR: Session ID missing in request")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session ID is required",
        )

    try:
        # Initialize workflow
        print("[API:Chat] Initializing IaCAgentWorkflow...")
        workflow = IaCAgentWorkflow(db)

        # Check if Excel resources are provided in context
        excel_resources = None
        if chat_request.context and "excel_resources" in chat_request.context:
            excel_resources = chat_request.context["excel_resources"]
            print(
                f"[API:Chat] Excel resources found in context: {len(excel_resources)} resources"
            )
        else:
            print("[API:Chat] No Excel resources in context")

        print(f"[API:Chat] Executing workflow for session {session.session_id}")
        # Execute workflow
        final_state = workflow.run(
            session_id=session.session_id,
            user_input=chat_request.message,
            excel_data=None,
            excel_resources=excel_resources,
        )
        print("[API:Chat] Workflow execution completed")
        print(f"[API:Chat] Final state: {final_state.get('workflow_state')}")

        # Get latest message from state
        messages = final_state.get("messages", [])
        print(f"[API:Chat] Total messages in final state: {len(messages)}")
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

        print(f"[API:Chat] Last AI message: {last_message[:100]}...")

        # Prepare code blocks if code was generated
        code_blocks = None
        generated_code = final_state.get("generated_code")

        if generated_code:
            print(f"[API:Chat] Generated code files: {list(generated_code.keys())}")
            code_blocks = [
                {"filename": filename, "content": content, "language": "hcl"}
                for filename, content in generated_code.items()
            ]
            print(f"[API:Chat] Prepared {len(code_blocks)} code blocks for response")
        else:
            print("[API:Chat] No generated code in final state")

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

        print(f"[API:Chat] Response prepared successfully")
        print("=" * 80 + "\n")
        return response

    except Exception as e:
        error_message = f"Error processing message: {str(e)}"
        print(f"[API:Chat] ERROR: {error_message}")
        import traceback

        traceback.print_exc()

        sid = chat_request.session_id if chat_request.session_id else ""

        print("=" * 80 + "\n")
        return ChatResponse(
            session_id=sid,
            message=error_message,
            code_blocks=None,
            metadata={"error": True, "error_details": str(e)},
        )


@router.post("/stream")
async def chat_stream(
    chat_request: ChatRequest,
    db: DBSession = Depends(get_db),
):
    """
    Process chat message with streaming progress updates via SSE.
    """
    print("\n" + "=" * 80)
    print(f"[API:ChatStream] Received streaming chat request")
    print(f"[API:ChatStream] Session ID: {chat_request.session_id}")
    print("=" * 80)

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

    async def generate_events():
        """Generate SSE events from agent progress."""
        import asyncio
        from app.agents.progress import ProgressTracker, ProgressEvent

        # Use a queue to bridge sync callbacks to async generator
        queue = asyncio.Queue()

        # Define callback for ProgressTracker
        def progress_callback(event: ProgressEvent):
            # This runs in the workflow thread
            loop.call_soon_threadsafe(queue.put_nowait, event)

        # Register callback
        ProgressTracker.register_callback(
            str(chat_request.session_id), progress_callback
        )

        # Run workflow in thread pool
        loop = asyncio.get_event_loop()
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
