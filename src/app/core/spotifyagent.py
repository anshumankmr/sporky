"""
Class to handle Spotify Agentic Tasks
"""
from typing import AsyncGenerator, List, Sequence, Dict
import json
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import AgentEvent, ChatMessage, TextMessage
from autogen_core import CancellationToken
from tools.spotify_tools import search_tracks, create_playlist,create_spotify_client

class SpotifyAgent(AssistantAgent):
    """
    Class to handle Spotify Agentic Tasks
    """
    def __init__(self, name: str):
        super().__init__(name, "An agent that interfaces with Spotify API")
        self.spotify_client = create_spotify_client()

    @property
    def produced_message_types(self) -> Sequence[type[ChatMessage]]:
        return (TextMessage,)

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        response: Response | None = None
        async for message in self.on_messages_stream(messages, cancellation_token):
            if isinstance(message, Response):
                response = message
        assert response is not None
        return response

    async def on_messages_stream(
        self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken
    ) -> AsyncGenerator[AgentEvent | ChatMessage | Response, None]:
        if not messages:
            yield Response(chat_message=TextMessage(content="No messages received", source=self.name))
            return

        def find_message(messages: Sequence[ChatMessage], source: str = "user") -> str | None:
            for message in messages:
                if message.source == source:
                    return message.content
            return None

        last_message = find_message(messages,source='search_assistant')
        
        # Handle search tracks
        if last_message:
            keyword = last_message.replace("search:", "").strip()
            result = search_tracks(client=self.spotify_client, keyword=keyword)
            response_content = json.dumps(result)
            # yield TextMessage(content=response_content, source=self.name)
            yield Response(
                chat_message=TextMessage(content=response_content, source=self.name),
                inner_messages=[]
            )

        # # Handle playlist creation
        # elif "create_playlist:" in last_message:
        #     tracks = last_message.replace("create_playlist:", "").strip()
        #     result = create_playlist(client=self.spotify_client, tracks=tracks, name="My Playlist")
        #     yield TextMessage(content=result, source=self.name)
        #     yield Response(
        #         chat_message=TextMessage(content="Playlist created", source=self.name),
        #         inner_messages=[]
        #     )

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        pass
