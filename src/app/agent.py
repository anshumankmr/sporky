"""
Core Wrapper for all the fun stuff
"""
from typing import List, Dict, Optional
import os
from autogen import ConversableAgent, UserProxyAgent, GroupChat, Agent
from core.resumablegroupchatmanager import ResumableGroupChatManager
from core.spotifyagent import SpotifyAgent
from core.prompt import PromptManager
from config.llm_config import groq_config,openai_config
from tools.spotify_tools import get_spotify_assistant_message


if os.getenv('Local') == 'true':
    openai_config = groq_config

async def get_music_recommendations(query: str, playlist: Optional[str], history: Optional[List[Dict]] = None) -> Dict:
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
        max_consecutive_auto_reply=1,
        is_termination_msg=lambda msg: "<END_CONVERSATION>" in msg
        # llm_config=groq_config
    )
    assistant = ConversableAgent(
        name="llm_assistant",
        llm_config=openai_config,
        system_message=PromptManager().get_prompt("spotifyagent"),
        is_termination_msg=lambda msg: "<END_CONVERSATION>" in msg  # Check for <END_CONVERSATION> token
    )
    search_asst = ConversableAgent(
        name="search_asst",
        llm_config=openai_config,
        system_message="""You are a helpful assistant. Follow these steps:
1. Analyze the user's query to generate EXACTLY ONE search keyword/phrase for Spotify. You will not generate any songs yourself. Only keywords to find songs.
2. Send the keyword/phrase to the Spotify Assistant to search for songs.""",
        is_termination_msg=lambda msg: "<END_CONVERSATION>" in msg  # Check for <END_CONVERSATION> token
    )
    def custom_speaker_selection_func(last_speaker: Agent, groupchat: GroupChat):
        """Define a customized speaker selection function.
        A recommended way is to define a transition for each speaker in the groupchat.

        Returns:
            Return an `Agent` class or a string from ['auto', 'manual', 'random', 'round_robin'] to select a default method to use.
        """
        messages = groupchat.messages
        if last_speaker is spotify_assistant:
            return assistant
        if last_speaker is user_proxy:
            if "<END_CONVERSATION>" in messages[-1]["content"]:
                return None
            return search_asst
        elif last_speaker is search_asst:
            return spotify_assistant
        return None
    groupchat = GroupChat(
        agents=[user_proxy, spotify_assistant,assistant,search_asst],
        messages= history or [],allow_repeat_speaker=False,
        max_round=4,speaker_selection_method=custom_speaker_selection_func
    )
    manager = ResumableGroupChatManager(
        name="Manager",
        groupchat=groupchat,
        history=history,
        llm_config=openai_config,
        max_consecutive_auto_reply=1,
        is_termination_msg=lambda msg: "<END_CONVERSATION>" in msg
    )

    await user_proxy.a_initiate_chat(manager, message=query,clear_history=False) #https://github.com/microsoft/autogen/issues/837


    return {
        "response": groupchat.messages[-1],
        "history": groupchat.messages,
        "playlist": get_spotify_assistant_message(groupchat.messages)
    }
