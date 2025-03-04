"""
Class to handle Spotify Agentic Tasks
"""
from typing import Dict, List, Tuple, Union,Optional,List,Dict
from autogen import ConversableAgent,AssistantAgent,Agent
import json
from tools.spotify_tools import search_tracks, create_playlist,create_spotify_client
class SpotifyAgent(ConversableAgent):
    """
    Class to handle Spotify Agentic Tasks
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, llm_config=False, **kwargs)
        self.spotify_client = create_spotify_client()
        self.register_reply(Agent, SpotifyAgent.search_tracks)
        # self.register_reply(Agent, SpotifyAgent.create_playlist)

    async def search_tracks(
        self,
        messages: List[Dict] = [],
        sender=None,
        config=None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        """
        Helper to call the Spotify API for searching keyword
        based tracks
        """
        last_message = messages[-1]["content"]
        result = search_tracks(client =  self.spotify_client,keyword= last_message)
        print('result of search_tracks',result)
        return True,  {"content": json.dumps(result), "type": "text", "raw_response": result}
    
    async def create_playlist(
        self,
        messages: List[Dict] = [],
        sender=None,
        config=None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        """
        Helper to call the Spotify API to create the playlist
        """
        last_message = messages[-1]["content"]
        result = create_playlist(client =  self.spotify_client,tracks=last_message,name="My Playlist") #NEED TO CUSTOMIZE THIS PUPPY
        return True, {"content": result}
