"""
LangGraph workflow definition for the Planning Agent.

Architecture:
START -> planner -> executor (loop) -> format_assistant -> END
                      |
              [replanner if needed]
                      |
              [approval pause if saving to Spotify]
"""
from langgraph.graph import StateGraph, START, END
from state import PlanningAgentState
from nodes.planner import planner_node
from nodes.executor import executor_node, approval_handler_node
from nodes.replanner import replanner_node
from nodes.format_assistant import format_assistant_node


def should_continue(state: PlanningAgentState) -> str:
    """
    Determine the next step based on current state.

    Routing logic:
    - If error -> format (to show error message)
    - If awaiting approval -> END (pause for user input)
    - If needs replan -> replanner
    - If execution complete -> format
    - Otherwise -> executor (continue executing steps)
    """
    # Check for errors first
    if state.get("error"):
        return "format_assistant"

    # Check if we're waiting for user approval
    if state.get("awaiting_approval"):
        return END

    # Check if replanning is needed
    if state.get("needs_replan"):
        return "replanner"

    # Check if execution is complete
    if state.get("execution_complete"):
        return "format_assistant"

    # Check if there's a plan to execute
    plan = state.get("plan")
    if not plan:
        # No plan yet - shouldn't happen after planner
        return "format_assistant"

    current_step = state.get("current_step", 0)
    if current_step >= len(plan):
        # All steps completed
        return "format_assistant"

    # Continue executing
    return "executor"


def route_after_planner(state: PlanningAgentState) -> str:
    """
    Route after planner node.

    If planner set awaiting_approval (for save_playlist_to_spotify),
    go directly to END to pause for user input.
    """
    if state.get("error"):
        return "format_assistant"

    if state.get("awaiting_approval"):
        return END

    # Start execution
    return "executor"


def route_after_replanner(state: PlanningAgentState) -> str:
    """
    Route after replanner node.
    """
    if state.get("error") or state.get("execution_complete"):
        return "format_assistant"

    # Start executing the new plan
    return "executor"


def build_planning_agent_graph():
    """
    Builds the LangGraph workflow for the Planning Agent.

    Graph structure:
    START -> planner -> executor (loop) -> format_assistant -> END
                           |
                   [replanner on failure]
                           |
                   [END on approval needed - pause]
    """
    workflow = StateGraph(PlanningAgentState)

    # Add nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("replanner", replanner_node)
    workflow.add_node("format_assistant", format_assistant_node)

    # Start with planner
    workflow.add_edge(START, "planner")

    # After planner, route based on state
    workflow.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "executor": "executor",
            "format_assistant": "format_assistant",
            END: END
        }
    )

    # After executor, check what to do next
    workflow.add_conditional_edges(
        "executor",
        should_continue,
        {
            "executor": "executor",
            "replanner": "replanner",
            "format_assistant": "format_assistant",
            END: END
        }
    )

    # After replanner, start executing the new plan
    workflow.add_conditional_edges(
        "replanner",
        route_after_replanner,
        {
            "executor": "executor",
            "format_assistant": "format_assistant"
        }
    )

    # Format assistant always ends
    workflow.add_edge("format_assistant", END)

    return workflow.compile()


def build_approval_continuation_graph():
    """
    Builds a graph for continuing after approval.

    This is used when resuming from an approval pause.
    START -> approval_handler -> executor (loop) -> format_assistant -> END
    """
    workflow = StateGraph(PlanningAgentState)

    workflow.add_node("approval_handler", approval_handler_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("replanner", replanner_node)
    workflow.add_node("format_assistant", format_assistant_node)

    workflow.add_edge(START, "approval_handler")

    # After approval handler, either continue or end
    workflow.add_conditional_edges(
        "approval_handler",
        should_continue,
        {
            "executor": "executor",
            "replanner": "replanner",
            "format_assistant": "format_assistant",
            END: END
        }
    )

    # Executor routing (same as main graph)
    workflow.add_conditional_edges(
        "executor",
        should_continue,
        {
            "executor": "executor",
            "replanner": "replanner",
            "format_assistant": "format_assistant",
            END: END
        }
    )

    workflow.add_conditional_edges(
        "replanner",
        route_after_replanner,
        {
            "executor": "executor",
            "format_assistant": "format_assistant"
        }
    )

    workflow.add_edge("format_assistant", END)

    return workflow.compile()


# Compile the main graph
_graph = build_planning_agent_graph()
_approval_graph = build_approval_continuation_graph()


def get_graph():
    """Get the main planning agent graph."""
    return _graph


def get_approval_graph():
    """Get the approval continuation graph."""
    return _approval_graph
