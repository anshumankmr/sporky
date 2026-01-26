"""
Replanner node for the Planning Agent workflow.

The replanner is invoked when a step fails or needs adjustment.
It analyzes what went wrong and creates a modified plan.
"""
import json
import logging
from typing import Dict, Any

from state import PlanningAgentState
from config.llm_config import get_model_client
from tools.llm_tools import extract_json_from_llm_response

logger = logging.getLogger(__name__)

REPLANNER_PROMPT = """You are Sporky's replanning agent. A step in the plan failed and you need to adjust.

## Context
**Original Query:** {query}
**Original Plan:** {original_plan}
**Completed Steps:** {completed_steps}
**Failed Step:** {failed_step}
**Error:** {error}

## Your Task
Create a modified plan that:
1. Works around the failure
2. Still achieves the user's goal
3. Uses the successful results from completed steps

## Available Tools
- search_spotify: Search for tracks
- commit_playlist_to_memory: Save playlist to memory
- read_playlist_from_memory: Retrieve saved playlist
- save_playlist_to_spotify: Create Spotify playlist (requires approval)

## Output Format
Output a JSON object:
```json
{{
  "plan": [
    {{"step": 1, "tool": "tool_name", "args": {{}}, "reasoning": "why"}}
  ],
  "message": "Brief explanation of the adjusted plan"
}}
```

If the goal cannot be achieved, output:
```json
{{
  "plan": [],
  "message": "Explanation of why the request cannot be fulfilled",
  "cannot_fulfill": true
}}
```

Output ONLY valid JSON.
"""


async def replanner_node(state: PlanningAgentState) -> Dict[str, Any]:
    """
    Create a modified plan when execution fails.

    The replanner:
    1. Analyzes what failed and why
    2. Considers what steps already succeeded
    3. Creates an adjusted plan to achieve the goal
    """
    logger.info(f"Replanner invoked: {state.get('replan_reason', 'Unknown reason')}")

    original_plan = state.get("plan", [])
    current_step = state.get("current_step", 0)
    step_results = state.get("step_results", {})
    replan_reason = state.get("replan_reason", "Unknown error")

    # Get completed steps info
    completed_steps = []
    for i in range(current_step):
        step = original_plan[i] if i < len(original_plan) else {}
        result_key = f"step_{i + 1}"
        result = step_results.get(result_key, {})
        completed_steps.append({
            "step": i + 1,
            "tool": step.get("tool", ""),
            "success": result.get("success", False) if isinstance(result, dict) else True
        })

    # Get the failed step info
    failed_step = original_plan[current_step] if current_step < len(original_plan) else {}

    prompt = REPLANNER_PROMPT.format(
        query=state.get("query", ""),
        original_plan=json.dumps(original_plan, indent=2),
        completed_steps=json.dumps(completed_steps, indent=2),
        failed_step=json.dumps(failed_step, indent=2),
        error=replan_reason
    )

    model_client = get_model_client()

    try:
        response = await model_client.ainvoke([
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Replan to handle the failure: {replan_reason}"}
        ])

        # Parse the response
        result = extract_json_from_llm_response(response.content)

        if not result:
            # Try direct JSON parse
            try:
                content = response.content.strip()
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                result = json.loads(content.strip())
            except json.JSONDecodeError:
                pass

        if not result:
            logger.error("Failed to parse replanner response")
            return {
                "error": f"Could not recover from error: {replan_reason}",
                "execution_complete": True,
                "formatted_response": f"Sorry, I ran into an issue: {replan_reason}. Please try rephrasing your request."
            }

        # Check if the goal cannot be fulfilled
        if result.get("cannot_fulfill"):
            message = result.get("message", "Unable to fulfill the request")
            logger.info(f"Replanner determined goal cannot be fulfilled: {message}")
            return {
                "execution_complete": True,
                "formatted_response": message,
                "needs_replan": False
            }

        new_plan = result.get("plan", [])
        message = result.get("message", "Plan adjusted")

        logger.info(f"Replanner created new {len(new_plan)} step plan: {message}")

        # Replace remaining plan with new plan
        return {
            "plan": new_plan,
            "current_step": 0,
            "needs_replan": False,
            "replan_reason": None
        }

    except Exception as e:
        logger.error(f"Replanner error: {e}")
        return {
            "error": f"Replanning failed: {str(e)}",
            "execution_complete": True,
            "formatted_response": f"Sorry, I encountered an error and couldn't recover. Please try again."
        }
