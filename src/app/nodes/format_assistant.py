"""
Format assistant node for formatting results into user-friendly responses.
"""
import json
import logging
from typing import Dict, Any, List

from state import PlanningAgentState
from core.prompt import PromptManager
from config.llm_config import get_model_client

logger = logging.getLogger(__name__)


FORMAT_PROMPT = """You are Sporky, an enthusiastic audiophile assistant. Format the execution results into a friendly, conversational response.

## Your Personality
- Energetic and passionate about music
- Knowledgeable but approachable
- Use casual language, occasional exclamations

## Task
Convert the raw results below into a natural response for the user.

## Guidelines
1. For track searches: List tracks with artist and album
2. For playlist saves: Confirm what was saved and how many tracks
3. For errors: Apologize briefly and explain what went wrong
4. Keep responses concise but informative
5. Add your personal touch - brief opinions on the music if relevant

## Original Query
{query}

## Execution Results
{results}

Write your response now. Be conversational, not robotic.
"""


def extract_all_tracks(step_results: Dict[str, Any]) -> List[Dict]:
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


def format_results_summary(step_results: Dict[str, Any]) -> str:
    """Create a summary of the execution results for the LLM."""
    summary_parts = []

    for key, result in sorted(step_results.items()):
        if isinstance(result, dict):
            if "tracks" in result:
                # Search result
                tracks = result["tracks"]
                query = result.get("query", "search")
                summary_parts.append(f"Search for '{query}': Found {len(tracks)} tracks")
                for i, track in enumerate(tracks[:15], 1):  # Limit to 15 for prompt
                    summary_parts.append(
                        f"  {i}. {track.get('name', 'Unknown')} - {track.get('artist', 'Unknown')} "
                        f"({track.get('album', 'Unknown Album')})"
                    )
            elif "playlists" in result:
                # List playlists result
                playlists = result["playlists"]
                summary_parts.append(f"Saved playlists: {len(playlists)} found")
                for pl in playlists:
                    summary_parts.append(f"  - {pl.get('name', 'Unnamed')} ({pl.get('track_count', 0)} tracks)")
            elif "playlist_name" in result and "track_count" in result:
                # Commit or save result
                action = "Saved to Spotify" if "spotify_url" in result else "Saved to memory"
                summary_parts.append(
                    f"{action}: '{result['playlist_name']}' with {result['track_count']} tracks"
                )
                if "spotify_url" in result:
                    summary_parts.append(f"  URL: {result['spotify_url']}")
            elif "error" in result:
                summary_parts.append(f"Error: {result['error']}")
            elif "message" in result:
                summary_parts.append(result["message"])

    return "\n".join(summary_parts) if summary_parts else "No results to display."


async def format_assistant_node(state: PlanningAgentState) -> Dict[str, Any]:
    """
    Formats the execution results into a user-friendly response.

    Handles:
    - Error states
    - Step results from execution
    """
    # Only skip formatting if execution_complete is True AND we have a formatted_response
    # (This means a node like approval_handler already set the final response)
    if state.get("execution_complete") and state.get("formatted_response"):
        return {}

    # Handle errors
    if state.get("error"):
        error_msg = state["error"]
        logger.warning(f"Formatting error response: {error_msg}")
        return {
            "formatted_response": f"Oops! I ran into a problem: {error_msg}. Want to try again?"
        }

    # Get step results
    step_results = state.get("step_results", {})

    if not step_results:
        # No results to format
        return {
            "formatted_response": "Hmm, I didn't find anything. Could you try rephrasing your request?"
        }

    # Create results summary
    results_summary = format_results_summary(step_results)

    # Use LLM to format the response
    prompt_manager = PromptManager()
    model_client = get_model_client()

    format_prompt = FORMAT_PROMPT.format(
        query=state.get("query", ""),
        results=results_summary
    )

    try:
        response = await model_client.ainvoke([
            {"role": "system", "content": format_prompt},
            {"role": "user", "content": "Format the results above into a friendly response."}
        ])

        formatted = response.content.strip()
        # Clean up any special tokens
        formatted = formatted.replace("<END_CONVERSATION>", "")

        logger.debug(f"Formatted response: {formatted[:200]}...")

        return {"formatted_response": formatted}

    except Exception as e:
        logger.error(f"Error formatting response: {e}")
        # Fallback to basic formatting
        return {
            "formatted_response": f"Here's what I found:\n\n{results_summary}"
        }
