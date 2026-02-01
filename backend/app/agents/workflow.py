"""LangGraph workflow for IaC generation agent."""

from typing import Generator, Callable, Optional
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from app.agents.state import AgentState, create_initial_state
from app.agents.nodes import AgentNodes
from app.agents.progress import ProgressTracker, AgentType, ProgressEvent
from app.models import Session as DBSessionModel


# Map node names to AgentType
NODE_TO_AGENT_TYPE = {
    "input_parser": AgentType.INPUT_PARSER,
    "information_collector": AgentType.INFORMATION_COLLECTOR,
    "compliance_checker": AgentType.COMPLIANCE_CHECKER,
    "code_generator": AgentType.CODE_GENERATOR,
    "code_reviewer": AgentType.CODE_REVIEWER,
}


class IaCAgentWorkflow:
    """LangGraph workflow for IaC code generation."""

    def __init__(self, db: Session):
        """
        Initialize workflow.

        Args:
            db: Database session
        """
        self.db = db
        self.nodes = AgentNodes(db)
        self.app = self._build_graph()

    def _load_state(self, session_id: str) -> AgentState | None:
        """
        Load agent state from database.

        Args:
            session_id: Session identifier

        Returns:
            Agent state or None if not found
        """
        session = (
            self.db.query(DBSessionModel)
            .filter(DBSessionModel.session_id == session_id)
            .first()
        )

        if not session:
            return None

        # Reconstruct state from session fields
        # Use placeholder user_input, it will be updated in run()
        state = create_initial_state(session_id=session_id, user_input="")
        state["session_id"] = session.session_id

        # Load messages (assuming stored as list of dicts in DB)
        if session.conversation_history:
            state["messages"] = session.conversation_history

        # Load other fields
        if session.resource_info:
            state["resources"] = session.resource_info

        if session.compliance_results:
            state["compliance_results"] = session.compliance_results

        if session.generated_code:
            state["generated_code"] = session.generated_code

        if session.workflow_state:
            state["workflow_state"] = session.workflow_state

        return state

    def _save_state(self, session_id: str, state: AgentState):
        """
        Save agent state to database.

        Args:
            session_id: Session identifier
            state: Agent state to save
        """
        session = (
            self.db.query(DBSessionModel)
            .filter(DBSessionModel.session_id == session_id)
            .first()
        )

        if not session:
            # Should exist if we are running workflow
            return

        # Update session fields
        session.conversation_history = state.get("messages", [])

        session.resource_info = state.get("resources", [])

        session.compliance_results = state.get("compliance_results", {})
        session.generated_code = state.get("generated_code", {})
        session.workflow_state = state.get("workflow_state", "unknown")

        self.db.commit()

    def _build_graph(self):
        """
        Build the LangGraph workflow.

        Returns:
            Compiled StateGraph
        """
        # Create graph
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("input_parser", self.nodes.input_parser)
        workflow.add_node("information_collector", self.nodes.information_collector)
        workflow.add_node("compliance_checker", self.nodes.compliance_checker)
        workflow.add_node("code_generator", self.nodes.code_generator)
        workflow.add_node("code_reviewer", self.nodes.code_reviewer)

        # Set entry point
        workflow.set_entry_point("input_parser")

        # Add conditional edges
        workflow.add_conditional_edges(
            "input_parser",
            self.nodes.should_continue_workflow,
            {
                "information_collector": "information_collector",
                "compliance_checker": "compliance_checker",
                "end": END,
            },
        )

        workflow.add_conditional_edges(
            "information_collector",
            self.nodes.should_continue_workflow,
            {
                "information_collector": "information_collector",
                "compliance_checker": "compliance_checker",
                "end": END,
            },
        )

        workflow.add_conditional_edges(
            "compliance_checker",
            self.nodes.should_continue_workflow,
            {"code_generator": "code_generator", "end": END},
        )

        workflow.add_edge("code_generator", "code_reviewer")

        # Code reviewer can loop back to code_generator if review fails
        workflow.add_conditional_edges(
            "code_reviewer",
            self.nodes.should_regenerate_code,
            {"regenerate": "code_generator", "end": END},
        )

        # Compile
        return workflow.compile()

    def run(
        self,
        session_id: str,
        user_input: str,
        excel_data: bytes | None = None,
        excel_resources: list | None = None,
    ) -> AgentState:
        """
        Execute the workflow.

        Args:
            session_id: Session identifier
            user_input: User's input message
            excel_data: Optional Excel file content (raw bytes)
            excel_resources: Optional parsed Excel resources (list of ResourceInfo)

        Returns:
            Final agent state
        """
        print("\n" + "=" * 80)
        print(f"[Workflow] STARTING WORKFLOW")
        print(f"[Workflow] Session ID: {session_id}")
        print(f"[Workflow] User input length: {len(user_input)} chars")
        print(f"[Workflow] Excel data: {'Yes' if excel_data else 'No'}")
        print(
            f"[Workflow] Excel resources: {len(excel_resources) if excel_resources else 0} resources"
        )
        print("=" * 80)

        # Load existing state from DB or create new
        state = self._load_state(session_id)

        if not state:
            print("[Workflow] No existing state found, creating initial state")
            state = create_initial_state(session_id=session_id, user_input=user_input)
            state["session_id"] = session_id
        else:
            print(
                f"[Workflow] Loaded existing state with {len(state.get('messages', []))} messages"
            )

        # Add user message
        state["messages"].append({"role": "user", "content": user_input})
        state["user_input"] = user_input  # Update latest input
        print(
            f"[Workflow] Added user message, total messages: {len(state['messages'])}"
        )

        if excel_data:
            print(f"[Workflow] Adding Excel data to state ({len(excel_data)} bytes)")
            state["excel_data"] = excel_data

        if excel_resources:
            print(f"[Workflow] Adding {len(excel_resources)} parsed resources to state")
            # Convert ResourceInfo objects to dicts if needed
            resources_dicts = []
            for res in excel_resources:
                if isinstance(res, dict):
                    resources_dicts.append(res)
                else:
                    # Assume it's a Pydantic model
                    resources_dicts.append(res if isinstance(res, dict) else res)
            state["resources"] = resources_dicts

        # Run graph
        print("[Workflow] Invoking LangGraph execution...")
        try:
            final_state = self.app.invoke(state)
            print("[Workflow] Graph execution completed successfully")
            print(
                f"[Workflow] Final workflow state: {final_state.get('workflow_state')}"
            )
            print(
                f"[Workflow] Total messages: {len(final_state.get('messages') or [])}"
            )
            print(
                f"[Workflow] Generated code files: {len(final_state.get('generated_code') or {})}"
            )

            # Save state to DB
            print("[Workflow] Saving state to database...")
            self._save_state(session_id, final_state)
            print("[Workflow] State saved successfully")

            print("=" * 80)
            print("[Workflow] WORKFLOW COMPLETED SUCCESSFULLY")
            print("=" * 80 + "\n")
            return final_state
        except Exception as e:
            print(f"[Workflow] ERROR during graph execution: {e}")
            import traceback

            traceback.print_exc()
            print("=" * 80)

            # Return current state with error message
            state["messages"].append(
                {"role": "assistant", "content": f"Error: {str(e)}"}
            )
            state["workflow_state"] = "error"
            state["errors"] = (state.get("errors") or []) + [str(e)]

            print("[Workflow] WORKFLOW FAILED")
            print("=" * 80 + "\n")
            return state

    def run_streaming(
        self,
        session_id: str,
        user_input: str,
        progress_callback: Optional[Callable[[ProgressEvent], None]] = None,
        excel_data: bytes | None = None,
        excel_resources: list | None = None,
    ) -> Generator[ProgressEvent, None, AgentState]:
        """
        Execute the workflow with streaming progress updates.

        Args:
            session_id: Session identifier
            user_input: User's input message
            progress_callback: Optional callback for progress events
            excel_data: Optional Excel file content
            excel_resources: Optional parsed Excel resources

        Yields:
            ProgressEvent for each node execution

        Returns:
            Final agent state
        """
        print("\n" + "=" * 80)
        print(f"[Workflow] STARTING STREAMING WORKFLOW")
        print(f"[Workflow] Session ID: {session_id}")
        print("=" * 80)

        # Register progress callback if provided
        if progress_callback:
            ProgressTracker.register_callback(session_id, progress_callback)

        # Load or create state (same as run method)
        state = self._load_state(session_id)
        if not state:
            state = create_initial_state(session_id=session_id, user_input=user_input)
            state["session_id"] = session_id

        state["messages"].append({"role": "user", "content": user_input})
        state["user_input"] = user_input

        if excel_data:
            state["excel_data"] = excel_data

        if excel_resources:
            resources_dicts = []
            for res in excel_resources:
                if isinstance(res, dict):
                    resources_dicts.append(res)
                else:
                    resources_dicts.append(res if isinstance(res, dict) else res)
            state["resources"] = resources_dicts

        try:
            # Use LangGraph's stream method for node-by-node execution
            final_state = None
            for chunk in self.app.stream(state):
                # chunk is a dict with node_name -> output_state
                for node_name, node_output in chunk.items():
                    agent_type = NODE_TO_AGENT_TYPE.get(node_name)
                    if agent_type:
                        # Emit progress event
                        event = ProgressEvent(
                            agent=agent_type,
                            status="completed",
                            message=f"完成: {agent_type.value}",
                        )

                        # Call callback if registered
                        if progress_callback:
                            progress_callback(event)

                        # Yield the event for SSE streaming
                        yield event

                    final_state = node_output

            # Save final state
            if final_state:
                self._save_state(session_id, final_state)

            print("[Workflow] STREAMING WORKFLOW COMPLETED")
            print("=" * 80 + "\n")

            return final_state

        except Exception as e:
            print(f"[Workflow] ERROR during streaming execution: {e}")
            import traceback

            traceback.print_exc()

            state["messages"].append(
                {"role": "assistant", "content": f"Error: {str(e)}"}
            )
            state["workflow_state"] = "error"
            state["errors"] = (state.get("errors") or []) + [str(e)]

            return state

        finally:
            # Unregister callback
            if progress_callback:
                ProgressTracker.unregister_callback(session_id)
