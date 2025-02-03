# agent.py
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
from typing import List, Dict, Optional
from config.llm_config import openai_config
from tools.spotify_tools import search_tracks, create_playlist

class ResumableGroupChatManager(GroupChatManager):
    """
    A GroupChatManager that can resume conversations from previous history.
    """
    def __init__(self, groupchat: GroupChat, history: Optional[List[Dict]] = None, **kwargs):
        # First call super().__init__ to properly set up the GroupChatManager
        super().__init__(groupchat=groupchat, **kwargs)
        
        # Then handle the history if provided
        if history:
            groupchat.messages = history
            self.restore_from_history(history)
    
    def restore_from_history(self, history: List[Dict]) -> None:
        """Restore conversation state from history."""
        for message in history:
            # Broadcast the message to all agents except the speaker
            for agent in self._groupchat.agents:
                if agent.name != message.get("name"):
                    self.send(message, agent, request_reply=False, silent=True)

class MusicRecommendationSystem:
    """
    A system for handling music recommendations through API endpoints.
    """
    def __init__(self):
        self.sporky = AssistantAgent(
            name="Sporky",
            llm_config=openai_config,
            system_message="""**You are Sporky, a highly enthusiastic and knowledgeable audiophile.**
        You possess an extensive understanding of music across various genres, with a particular focus on sound quality, 
        production techniques, and current trends. You are passionate about sharing your love of music and helping users 
        discover new artists and tracks that will excite them.

        **Your key characteristics are:**
        * **Expertise:** Deep understanding of music genres, subgenres, production techniques (mixing, mastering, dynamics, etc.), 
          audio formats, and playback equipment. You are up-to-date with the latest music releases, trends, and audio technology.
        * **Personality:** Energetic, enthusiastic, and highly opinionated (in a positive, encouraging way).
        * **Communication Style:** Casual but informed. You use technical terms related to audio and music production but explain them when necessary.
        * **Focus:** Sound quality, current trends, personal recommendations, and the overall listening experience.

        **Your primary task is to provide music recommendations to users based on their requests.**""",
            description="An AI assistant for music recommendations and playlist creation.",
            human_input_mode="NEVER"
        )

        self.user_proxy = UserProxyAgent(
            name="UserAgent",
            llm_config=openai_config,
            description="A human user interacting through the API.",
            code_execution_config=False,
            human_input_mode="NEVER",
            is_termination_msg=lambda message: True
        )

        # Register tools once at initialization
        self.user_proxy.register_for_execution(name="create_playlist")(create_playlist)
        self.user_proxy.register_for_execution(name="search_tracks")(search_tracks)

    def _setup_group_chat(self, history: Optional[List[Dict]] = None) -> tuple[GroupChat, GroupChatManager]:
        """Set up the group chat with optional history."""
        # Create group chat first
        group_chat = GroupChat(
            agents=[self.user_proxy, self.sporky],
            messages=[] if history is None else history,
            max_round=5
        )

        # Create manager with the group chat
        manager = ResumableGroupChatManager(
            groupchat=group_chat,
            llm_config=openai_config,
            human_input_mode="NEVER"
        )

        return group_chat, manager

    async def get_recommendation(self, query: str, history: Optional[List[Dict]] = None) -> Dict:
        """Process a music recommendation request."""
        group_chat, manager = self._setup_group_chat(history)
        
        # Initiate chat and wait for response
        await self.user_proxy.a_initiate_chat(
            manager,
            message=query,
            clear_history=False
        )

        # Get the last message and all history
        last_message = group_chat.messages[-1]["content"] if group_chat.messages else ""
        
        return {
            "response": last_message,
            "history": group_chat.messages
        }

# Create singleton instance
music_system = MusicRecommendationSystem()

async def get_music_recommendations(query: str, history: Optional[List[Dict]] = None) -> Dict:
    """Get music recommendations via the API."""
    return await music_system.get_recommendation(query, history)