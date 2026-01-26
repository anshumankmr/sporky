"""
Core agent for music recommendations using the Planning Agent architecture.
"""
from typing import List, Dict, Optional, Any
import logging
import json

from graph import get_graph, get_approval_graph
from state import create_initial_state

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def extract_tracks_from_results(step_results: Dict[str, Any]) -> List[Dict]:
    """Extract all tracks from step results for playlist storage."""
    all_tracks = []

    for result in step_results.values():
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


async def get_music_recommendations(
    query: str,
    session_id: str,
    history: Optional[List[Dict]] = None,
    pending_state: Optional[Dict] = None
) -> Dict:
    """
    Get music recommendations via the Planning Agent workflow.

    Args:
        query: User's search query (or reply to approval prompt)
        session_id: Session identifier for memory operations
        history: Optional conversation history
        pending_state: State from a paused approval flow (for continuation)

    Returns:
        Dict with 'response', 'state', 'playlist', and 'awaiting_approval' keys
    """
    try:
        # Check if this is a continuation from approval pause
        if pending_state is not None:
            logger.info(f"Continuing from approval for session {session_id}")
            return await _continue_from_approval(query, pending_state, session_id)

        # Create initial state for new request
        initial_state = create_initial_state(
            query=query,
            session_id=session_id,
            history=history
        )

        # Run the planning agent graph
        graph = get_graph()
        final_state = await graph.ainvoke(initial_state)

        # Check if we're pausing for approval
        if final_state.get("awaiting_approval"):
            logger.info(f"Pausing for approval - session {session_id}")
            return {
                "response": final_state.get("formatted_response", ""),
                "state": _serialize_state(final_state),
                "playlist": extract_tracks_from_results(final_state.get("step_results", {})),
                "awaiting_approval": True,
                "pending_state": _serialize_state(final_state)
            }

        return {
            "response": final_state.get("formatted_response", ""),
            "state": _serialize_state(final_state),
            "playlist": extract_tracks_from_results(final_state.get("step_results", {})),
            "awaiting_approval": False
        }

    except Exception as e:
        logger.error(f"Error in music recommendations: {e}", exc_info=True)
        return {
            "response": f"Sorry, I encountered an error: {str(e)}",
            "state": {},
            "playlist": [],
            "awaiting_approval": False
        }


async def _continue_from_approval(
    user_reply: str,
    pending_state: Dict,
    session_id: str
) -> Dict:
    """
    Continue execution after user responds to approval prompt.

    The approval_handler_node will use LLM to interpret the user's reply
    and decide whether to approve, reject, or ask for clarification.

    Args:
        user_reply: The user's response to the approval prompt
        pending_state: The state from when we paused for approval
        session_id: Session identifier

    Returns:
        Dict with results
    """
    try:
        # Reconstruct the state with the user's reply
        state = pending_state.copy()
        state["query"] = user_reply  # Pass user reply for LLM interpretation
        state["session_id"] = session_id

        logger.debug(f"Continuing approval flow with user reply: {user_reply[:100]}")

        # Run the approval continuation graph
        # approval_handler_node will interpret the reply and decide
        graph = get_approval_graph()
        final_state = await graph.ainvoke(state)

        logger.debug(f"Continuation result: awaiting_approval={final_state.get('awaiting_approval')}")

        # Safety net: if we still have awaiting_approval=True and it's the same prompt,
        # something went wrong - but let's respect what the graph decided
        if final_state.get("awaiting_approval"):
            logger.warning(f"Continuation still awaiting approval for session {session_id}")
            return {
                "response": final_state.get("formatted_response", ""),
                "state": _serialize_state(final_state),
                "playlist": extract_tracks_from_results(final_state.get("step_results", {})),
                "awaiting_approval": True,
                "pending_state": _serialize_state(final_state)
            }

        return {
            "response": final_state.get("formatted_response", ""),
            "state": _serialize_state(final_state),
            "playlist": extract_tracks_from_results(final_state.get("step_results", {})),
            "awaiting_approval": False
        }

    except Exception as e:
        logger.error(f"Error continuing from approval: {e}", exc_info=True)
        return {
            "response": f"Sorry, I encountered an error: {str(e)}",
            "state": {},
            "playlist": [],
            "awaiting_approval": False
        }


def _serialize_state(state: dict) -> dict:
    """
    Serialize state for storage in Firestore.
    """
    serializable = {}
    for key, value in state.items():
        try:
            json.dumps(value)
            serializable[key] = value
        except (TypeError, ValueError):
            serializable[key] = str(value)
    return serializable
