"""
Core Wrapper for all the fun stuff
"""
from typing import List, Dict, Optional
from autogen import AssistantAgent, UserProxyAgent, GroupChat#, GroupChatManager
from core.resumablegroupchatmanager import ResumableGroupChatManager
from core.spotifyagent import SpotifyAgent
from core.prompt import PromptManager
from config.llm_config import groq_config



async def get_music_recommendations(query: str, history: Optional[List[Dict]] = None) -> Dict:
    """Get music recommendations via the API."""
    prompt = PromptManager().get_prompt("spotify")  
    user_proxy = UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        code_execution_config=False,
        is_termination_msg=lambda _: True # Always True
    )
    spotify_assistant = SpotifyAgent(
        name="spotify_assistant",
        system_message=prompt,
        max_consecutive_auto_reply=1
        # llm_config=groq_config
    )

    groupchat = GroupChat(
        agents=[user_proxy, spotify_assistant],
        messages= history or [],allow_repeat_speaker=False
    )
    manager = ResumableGroupChatManager(
        name="Manager",
        groupchat=groupchat,
        llm_config=groq_config,
    )

    await user_proxy.a_initiate_chat(manager, message=query,clear_history=False) #https://github.com/microsoft/autogen/issues/837

    return {
        "response": groupchat.messages[-1],
        "history": groupchat.messages,
    }
