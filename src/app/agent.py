"""
Core Wrapper for all the fun stuff
"""
from typing import List, Dict, Optional,Sequence
import os
import logging
from autogen_core import TRACE_LOGGER_NAME
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
from core.spotifyagent import SpotifyAgent
from core.detailsagent import PlaylistDetailsAgent
from core.prompt import PromptManager
from config.llm_config import openai_client, gemini_client
from tools.spotify_tools import get_spotify_assistant_message
from tools.llm_tools import extract_json_from_llm_response,merge_json_lists

def log_condition(label: str, fn):
    def wrapper(msg):
        result = fn(msg)
        trace_logger.debug(f"[GRAPH ROUTE] {label} → {result} | Message: {msg.to_model_text()[:100]}")
        return result
    return wrapper

logging.basicConfig(level=logging.WARNING)
trace_logger = logging.getLogger(TRACE_LOGGER_NAME)
trace_logger.addHandler(logging.StreamHandler())
trace_logger.setLevel(logging.DEBUG)

model_client = openai_client
if os.getenv('LOCAL').lower() == 'true':
    model_client = gemini_client
async def get_music_recommendations(query: str, playlist: Optional[str], history: Optional[List[Dict]] = None) -> Dict:
    """Get music recommendations via the API."""
    sporky_system_prompt = PromptManager().get_prompt("sporky_system_prompt",history=[])
    router_agent = AssistantAgent(
        "router_agent",
        model_client=model_client,
        system_message=PromptManager().get_prompt("router_agent", query=query, history=[])
    )

    search_assistant = AssistantAgent(
        "search_assistant",
        model_client=model_client,
        system_message=sporky_system_prompt
    )

    # details_agent = PlaylistDetailsAgent(
    #     "details_agent",
    #     model_client=model_client,
    #     query_text=query
    # )

    # framing_agent = AssistantAgent(
    #     "framing_agent",
    #     model_client=model_client,
    #     system_message=PromptManager().get_prompt("framing_agent", query=query)
    # )

    spotify_agent_assistant = SpotifyAgent("spotify_agent_assistant")

    format_assistant = AssistantAgent(
        "format_assistant",
        model_client=model_client,
        system_message=PromptManager().get_prompt("format_playlist_response")
    )

    # ----- 2. Build the directed graph -----
    builder = DiGraphBuilder()
    agents = [
        router_agent, search_assistant, 
        spotify_agent_assistant, format_assistant
    ]
    # details_agent,
        # not_complete_response_assistant, framing_agent,
    for node in agents:
        builder.add_node(node)

    # router branching
    builder.add_edge(
    router_agent, search_assistant,
    activation_group="route",
    condition=log_condition("router→search if action=='search_tracks'",
        lambda m: '"action": "search_tracks"' in m.to_model_text())
    )


#     builder.add_edge(
#     router_agent, details_agent,
#     activation_group="route",
#     condition=log_condition("router→details if action=='make_playlist'",
#         lambda m: '"action": "make_playlist"' in m.to_model_text())
# )


#     # details path (complete vs incomplete)
#     builder.add_edge(
#     details_agent, not_complete_response_assistant,
#     activation_group="details_path",
#     condition=log_condition("details→not_complete if complete==false or name==''",
#         lambda m: ('"complete": false' in m.to_model_text()) or ('"name": ""' in m.to_model_text()))
# )


#     builder.add_edge(
#     details_agent, framing_agent,
#     activation_group="details_path",
#     condition=log_condition("details→framing if complete==true",
#         lambda m: '"complete": true' in m.to_model_text())
# )



    # straight‑line edges
    builder.add_edge(search_assistant, spotify_agent_assistant)
    # builder.add_edge(framing_agent, spotify_agent_assistant)
    builder.add_edge(spotify_agent_assistant, format_assistant)

    graph = builder.build()

    # ----- 3. Create and run the flow -----
    flow = GraphFlow(participants=builder.get_participants(), graph=graph)

    # Option 1: Collect all messages from the stream
    messages = []
    async for message in flow.run_stream(task=query):
        messages.append(message)
    
    # Get the final result
    result_stream = messages  # or however you want to structure this
    
    # Option 2: Alternative - if you just need the final state
    # You might be able to use flow.run() instead of flow.run_stream()
    # result = await flow.run(task=query)
    
    state = await flow.save_state()

    return {
        "response": dict(dict(result_stream[-1])['messages'][-1])['content'],
        "state": state,
        "playlist": [],
    }