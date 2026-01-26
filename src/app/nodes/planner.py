"""
Planner node for the Planning Agent workflow.

The planner analyzes the user's query and creates a multi-step plan
using the available tools.
"""
import json
import logging
from typing import Dict, Any, List

from state import PlanningAgentState
from core.prompt import PromptManager
from config.llm_config import get_model_client
from tools.llm_tools import extract_json_from_llm_response

logger = logging.getLogger(__name__)


def format_history(history: List[Dict]) -> str:
    """Format conversation history for the prompt."""
    if not history:
        return "No previous conversation."

    formatted = []
    for msg in history[-10:]:  # Last 10 messages for context
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        formatted.append(f"{role}: {content}")

    return "\n".join(formatted)


def format_saved_playlists(session_id: str) -> str:
    """Get list of saved playlists for the session."""
    try:
        from firebase_admin import firestore
        db = firestore.client()

        collection_ref = db.collection('playlists').document(session_id).collection('saved_playlists')
        docs = collection_ref.stream()

        playlists = []
        for doc in docs:
            data = doc.to_dict()
            playlists.append(f"- {data.get('name', doc.id)} ({data.get('track_count', 0)} tracks)")

        if playlists:
            return "\n".join(playlists)
        return "No saved playlists yet."
    except Exception as e:
        logger.warning(f"Could not fetch saved playlists: {e}")
        return "Unable to fetch saved playlists."


def parse_plan(response_content: str) -> Dict[str, Any]:
    """Parse the LLM response to extract the plan."""
    # Try to extract JSON from the response
    result = extract_json_from_llm_response(response_content)

    if result and isinstance(result, dict) and "plan" in result:
        return result

    # If extraction failed, try direct JSON parse
    try:
        # Clean up common issues
        content = response_content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        parsed = json.loads(content.strip())
        if isinstance(parsed, dict) and "plan" in parsed:
            return parsed
    except json.JSONDecodeError:
        pass

    # Return error structure if parsing failed
    return {
        "error": "Failed to parse plan from LLM response",
        "raw_response": response_content[:500]
    }


async def planner_node(state: PlanningAgentState) -> Dict[str, Any]:
    """
    Generate a plan based on the user's query.

    The planner uses an LLM to create a multi-step plan that will be
    executed by the executor node.
    """
    logger.info(f"Planner processing query: {state['query']}")

    prompt_manager = PromptManager()

    # Format context for the prompt
    history_str = format_history(state.get("history", []))
    saved_playlists_str = format_saved_playlists(state.get("session_id", ""))

    # Get the planner prompt
    system_prompt = prompt_manager.get_prompt(
        "planner_prompt",
        history=history_str,
        saved_playlists=saved_playlists_str,
        query=state["query"]
    )

    model_client = get_model_client()

    try:
        response = await model_client.ainvoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": state["query"]}
        ])

        logger.debug(f"Planner raw response: {response.content[:500]}")

        # Parse the plan
        parsed = parse_plan(response.content)

        if "error" in parsed:
            logger.error(f"Failed to parse plan: {parsed['error']}")
            return {
                "error": parsed["error"],
                "plan_string": response.content
            }

        plan = parsed.get("plan", [])
        requires_approval = parsed.get("requires_approval", False)
        approval_message = parsed.get("approval_message", "")

        logger.info(f"Planner created {len(plan)} step plan, requires_approval={requires_approval}")

        # If the plan requires approval, set up the pending action
        if requires_approval:
            # Find the save_playlist_to_spotify step
            for i, step in enumerate(plan):
                if step.get("tool") == "save_playlist_to_spotify":
                    return {
                        "plan": plan,
                        "plan_string": response.content,
                        "awaiting_approval": True,
                        "pending_action": {
                            "tool": "save_playlist_to_spotify",
                            "args": step.get("args", {}),
                            "step_index": i,
                            "description": approval_message
                        },
                        "formatted_response": approval_message
                    }

        return {
            "plan": plan,
            "plan_string": response.content,
            "current_step": 0,
            "step_results": {},
            "execution_complete": False
        }

    except Exception as e:
        logger.error(f"Planner error: {e}")
        return {
            "error": f"Planner failed: {str(e)}"
        }
