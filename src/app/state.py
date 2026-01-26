"""
State schema for the Planning Agent workflow.
"""
from typing import TypedDict, Optional, List, Dict, Any


class PlanStep(TypedDict):
    """Single step in a plan."""
    step: int
    tool: str
    args: Dict[str, Any]
    reasoning: str


class PendingAction(TypedDict):
    """Context for a pending action awaiting approval."""
    tool: str
    args: Dict[str, Any]
    step_index: int
    description: str


class PlanningAgentState(TypedDict):
    """Central state object for the Planning Agent workflow."""

    # Input fields
    query: str
    history: Optional[List[Dict]]
    session_id: str

    # Planning phase
    plan: Optional[List[PlanStep]]
    plan_string: Optional[str]  # Raw plan output for debugging

    # Execution phase
    current_step: int
    step_results: Dict[str, Any]
    execution_complete: bool
    last_tool_result: Optional[Any]

    # Approval handling (for Spotify saves)
    awaiting_approval: bool
    pending_action: Optional[PendingAction]
    user_approved: Optional[bool]

    # Re-planning
    needs_replan: bool
    replan_reason: Optional[str]

    # Output
    formatted_response: str

    # Error handling
    error: Optional[str]


def create_initial_state(
    query: str,
    session_id: str,
    history: Optional[List[Dict]] = None
) -> PlanningAgentState:
    """Create an initial state for a new planning agent run."""
    return PlanningAgentState(
        query=query,
        history=history or [],
        session_id=session_id,
        plan=None,
        plan_string=None,
        current_step=0,
        step_results={},
        execution_complete=False,
        last_tool_result=None,
        awaiting_approval=False,
        pending_action=None,
        user_approved=None,
        needs_replan=False,
        replan_reason=None,
        formatted_response="",
        error=None,
    )
