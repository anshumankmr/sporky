"""
Executor node for the Planning Agent workflow.

The executor runs the plan steps one by one, invoking the appropriate tools
and tracking results. It handles approval pauses for sensitive operations.
"""
import logging
from typing import Dict, Any, List

from state import PlanningAgentState
from tools.planning_tools import TOOL_REGISTRY
from config.llm_config import get_model_client
from tools.llm_tools import extract_json_from_llm_response

logger = logging.getLogger(__name__)


def resolve_args(args: Dict[str, Any], step_results: Dict[str, Any], state: PlanningAgentState) -> Dict[str, Any]:
    """
    Resolve argument placeholders with actual values.

    Handles:
    - RESULT_STEP_N: Replace with result from step N
    - Session ID injection for memory operations
    """
    resolved = {}

    for key, value in args.items():
        if isinstance(value, str):
            # Handle step result references
            if value.startswith("RESULT_STEP_"):
                step_num = value.replace("RESULT_STEP_", "")
                result_key = f"step_{step_num}"
                if result_key in step_results:
                    step_result = step_results[result_key]
                    # Extract tracks from the result if it's a search result
                    if isinstance(step_result, dict) and "tracks" in step_result:
                        resolved[key] = step_result["tracks"]
                    else:
                        resolved[key] = step_result
                else:
                    logger.warning(f"Step result {result_key} not found, using empty list")
                    resolved[key] = []
            else:
                resolved[key] = value
        else:
            resolved[key] = value

    # Inject session_id for memory operations
    if "session_id" not in resolved:
        resolved["session_id"] = state.get("session_id", "")

    return resolved


def get_tracks_from_results(step_results: Dict[str, Any]) -> List[Dict]:
    """Extract all tracks from step results."""
    all_tracks = []

    for key, result in step_results.items():
        if isinstance(result, dict) and "tracks" in result:
            tracks = result["tracks"]
            if isinstance(tracks, list):
                all_tracks.extend(tracks)

    # Remove duplicates by URI
    seen_uris = set()
    unique_tracks = []
    for track in all_tracks:
        uri = track.get("uri", "")
        if uri and uri not in seen_uris:
            seen_uris.add(uri)
            unique_tracks.append(track)

    return unique_tracks


async def executor_node(state: PlanningAgentState) -> Dict[str, Any]:
    """
    Execute the current step in the plan.

    The executor:
    1. Gets the current step from the plan
    2. Resolves argument placeholders
    3. Checks for approval requirements
    4. Invokes the tool
    5. Stores the result and advances to the next step
    """
    plan = state.get("plan", [])
    current_step = state.get("current_step", 0)
    step_results = state.get("step_results", {}).copy()

    # Check if we've completed all steps
    if current_step >= len(plan):
        logger.info("Execution complete - all steps finished")
        return {
            "execution_complete": True,
            "step_results": step_results
        }

    step = plan[current_step]
    tool_name = step.get("tool", "")
    raw_args = step.get("args", {})

    logger.info(f"Executing step {current_step + 1}/{len(plan)}: {tool_name}")

    # Resolve argument placeholders
    resolved_args = resolve_args(raw_args, step_results, state)

    # Check for approval requirement BEFORE execution
    if tool_name == "save_playlist_to_spotify":
        if not state.get("user_approved"):
            # Need to pause for approval
            track_count = len(resolved_args.get("tracks", []))
            playlist_name = resolved_args.get("playlist_name", "playlist")

            logger.info(f"Pausing for approval: {playlist_name} with {track_count} tracks")

            return {
                "awaiting_approval": True,
                "pending_action": {
                    "tool": tool_name,
                    "args": resolved_args,
                    "step_index": current_step,
                    "description": f"Create '{playlist_name}' ({track_count} tracks) on your Spotify"
                },
                "formatted_response": f"I'm ready to create '{playlist_name}' with {track_count} tracks on your Spotify account. Want me to go ahead?"
            }

    # Get the tool from registry
    tool = TOOL_REGISTRY.get(tool_name)

    if not tool:
        logger.error(f"Unknown tool: {tool_name}")
        return {
            "error": f"Unknown tool: {tool_name}",
            "needs_replan": True,
            "replan_reason": f"Tool '{tool_name}' not found"
        }

    # Execute the tool
    try:
        # Filter args to only include what the tool accepts
        # (remove session_id for tools that don't need it)
        tool_args = resolved_args.copy()

        result = tool.invoke(tool_args)

        logger.info(f"Step {current_step + 1} result: success={result.get('success', False)}")

        # Check for tool failure
        if isinstance(result, dict) and not result.get("success", True):
            error_msg = result.get("error", "Tool execution failed")
            logger.warning(f"Tool {tool_name} failed: {error_msg}")

            return {
                "step_results": step_results,
                "last_tool_result": result,
                "needs_replan": True,
                "replan_reason": f"Step {current_step + 1} ({tool_name}) failed: {error_msg}"
            }

        # Store the result
        step_results[f"step_{current_step + 1}"] = result

        # Advance to next step
        return {
            "step_results": step_results,
            "last_tool_result": result,
            "current_step": current_step + 1
        }

    except Exception as e:
        logger.error(f"Error executing {tool_name}: {e}")
        return {
            "step_results": step_results,
            "needs_replan": True,
            "replan_reason": f"Step {current_step + 1} ({tool_name}) error: {str(e)}"
        }


APPROVAL_DECISION_PROMPT = """You asked the user for permission to perform this action:
{pending_action}

The user replied: "{user_reply}"

Based on this reply, determine if the user:
- APPROVES the action (they said yes, sure, do it, go ahead, ok, sounds good, etc.)
- REJECTS the action (they said no, don't, cancel, stop, nah, never mind, etc.)
- Said something ELSE that needs clarification (asked a question, changed topic, unclear response)

Return your decision as JSON:
{{"decision": "approve" | "reject" | "other", "reason": "brief explanation"}}

Output ONLY the JSON, nothing else."""


async def approval_handler_node(state: PlanningAgentState) -> Dict[str, Any]:
    """
    Handle user approval response using LLM to interpret natural language.

    This node uses an LLM to understand whether the user approved, rejected,
    or said something else that needs clarification.
    """
    user_reply = state.get("query", "")
    pending_action = state.get("pending_action", {})
    action_description = pending_action.get("description", "create a playlist on Spotify")

    logger.info(f"Processing approval response: '{user_reply[:50]}...'")

    # Use LLM to interpret the user's response
    try:
        model_client = get_model_client()

        prompt = APPROVAL_DECISION_PROMPT.format(
            pending_action=action_description,
            user_reply=user_reply
        )

        response = await model_client.ainvoke([
            {"role": "user", "content": prompt}
        ])

        # Parse the LLM response
        parsed = extract_json_from_llm_response(response.content)

        if not parsed:
            # Fallback: try to detect simple yes/no
            reply_lower = user_reply.lower().strip()
            if any(word in reply_lower for word in ["yes", "yeah", "sure", "ok", "do it", "go ahead"]):
                parsed = {"decision": "approve", "reason": "Detected affirmative response"}
            elif any(word in reply_lower for word in ["no", "nope", "don't", "cancel", "stop"]):
                parsed = {"decision": "reject", "reason": "Detected negative response"}
            else:
                parsed = {"decision": "other", "reason": "Could not parse LLM response"}

        decision = parsed.get("decision", "other")
        reason = parsed.get("reason", "")

        logger.info(f"Approval decision: {decision} - {reason}")

        if decision == "approve":
            # User approved - continue execution
            logger.info("User approved, continuing execution")
            return {
                "user_approved": True,
                "awaiting_approval": False,
                "pending_action": None,
                "formatted_response": ""  # Clear so format_assistant generates new response
            }

        elif decision == "reject":
            # User declined
            logger.info("User declined, execution cancelled")
            return {
                "user_approved": False,
                "awaiting_approval": False,
                "pending_action": None,
                "execution_complete": True,
                "formatted_response": "No problem! Your playlist is still saved in memory if you change your mind."
            }

        else:
            # User said something else - ask for clarification
            logger.info("User response unclear, asking for clarification")
            return {
                "awaiting_approval": True,
                "formatted_response": f"Before I create the playlist on your Spotify, can you confirm you want me to proceed? Just say 'yes' or 'no'."
            }

    except Exception as e:
        logger.error(f"Error in approval handler: {e}")
        # On error, ask for clarification rather than making assumptions
        return {
            "awaiting_approval": True,
            "formatted_response": "I didn't quite catch that. Would you like me to create the playlist on your Spotify? (yes/no)"
        }
