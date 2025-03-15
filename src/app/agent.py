"""
Core Wrapper for all the fun stuff
"""
from typing import List, Dict, Optional,Sequence
import os
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import AgentEvent, ChatMessage
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_core import CancellationToken
from autogen_agentchat.messages import TextMessage
from core.spotifyagent import SpotifyAgent
from core.prompt import PromptManager
from config.llm_config import openai_client, groq_client
from tools.spotify_tools import get_spotify_assistant_message
from tools.llm_tools import extract_json_from_llm_response
import logging
from autogen_core import TRACE_LOGGER_NAME

logging.basicConfig(level=logging.WARNING)
trace_logger = logging.getLogger(TRACE_LOGGER_NAME)
trace_logger.addHandler(logging.StreamHandler())
trace_logger.setLevel(logging.DEBUG)

if os.getenv('LOCAL') == 'true':
    openai_client = groq_client

async def get_music_recommendations(query: str, playlist: Optional[str], history: Optional[List[Dict]] = None) -> Dict:
    """Get music recommendations via the API."""
    sporky_system_prompt = PromptManager().get_prompt("sporky_system_prompt",history=[])

    router_agent = AssistantAgent(
        name="router_agent",
        system_message=PromptManager().get_prompt('router_agent',query=query, history=[]),
        model_client=openai_client,
    )
    spotify_search_assistant = SpotifyAgent(
        name="spotify_search_assistant"
    )
    prompt_manager = PromptManager()
    format_assistant = AssistantAgent(
        name="format_assistant",
        model_client=openai_client,
        system_message=prompt_manager.get_prompt("format_playlist_response"),
        # is_termination_msg=lambda msg: "<END_CONVERSATION>" in msg  # Check for <END_CONVERSATION> token
    )
    search_assistant = AssistantAgent(
        name="search_assistant",
        model_client=openai_client,
        system_message=sporky_system_prompt,
    )
    def custom_speaker_selection_func(messages: Sequence[AgentEvent | ChatMessage]) -> str | None:
        """Define the conversation flow between agents.
        Flow: router_agent -> search_assistant -> spotify_search_assistant -> format_assistant
        """
        last_message = messages[-1]
        if last_message.source == 'user':
            return router_agent.name
        if last_message.source == router_agent.name:
            print('last_speaker is router_agent')
            try:
                action = extract_json_from_llm_response(last_message.content)["action"]
                if action == "search_tracks":
                    return search_assistant.name
                # Note: Add playlist agent handling here when implemented
                # elif action == "make_playlist":
                #     return playlist_agent
            except (KeyError, ValueError) as e:
                print("Message appears to be user input, routing to router_agent")
                if last_message.role == "user":
                    return router_agent.name
                print("JSON parsing error:", e)
                return None
        if last_message.source == spotify_search_assistant.name:
            print('last_speaker is spotify_search_assistant')
            return format_assistant.name
        if last_message.source == search_assistant.name:
            print('last_speaker is search_assistant')
            return spotify_search_assistant.name
        return None
    text_mention_termination = TextMentionTermination("<END_CONVERSATION>")
    max_messages_termination = MaxMessageTermination(max_messages=25)
    termination = text_mention_termination | max_messages_termination
    team = SelectorGroupChat(
        [spotify_search_assistant, format_assistant, search_assistant, router_agent],
        selector_func=custom_speaker_selection_func,
        model_client=openai_client,
        termination_condition=termination
    )
    if history:
        await team.load_state(history)
    response = await team.run(task=query)
    state = await team.save_state()

    return {
        "response": response.messages[-1].content,
        "history": state,
        "playlist": [] #get_spotify_assistant_message(groupchat.messages)
    }
