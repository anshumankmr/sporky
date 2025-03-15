"""
SpotifyAgent module

This module defines the SpotifyAgent class which interfaced with the Spotify API.
"""

import json
import logging
from typing import AsyncGenerator, Sequence, Optional, Type

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import AgentEvent, ChatMessage, TextMessage
from autogen_core import CancellationToken
from tools.spotify_tools import search_tracks, create_playlist, create_spotify_client

logger = logging.getLogger(__name__)


class SpotifyAgent(AssistantAgent):
    """
    An agent that interfaces with the Spotify API to perform agentic tasks.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name, "An agent that interfaces with Spotify API")
        self.spotify_client = create_spotify_client()

    @property
    def produced_message_types(self) -> Sequence[Type[ChatMessage]]:
        return (TextMessage,)

    async def on_messages(
        self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken
    ) -> Response:
        async for response in self.on_messages_stream(messages, cancellation_token):
            if isinstance(response, Response):
                return response

        raise RuntimeError("No valid response was generated from messages.")

    async def on_messages_stream(
        self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken
    ) -> AsyncGenerator[AgentEvent | ChatMessage | Response, None]:
        if not messages:
            yield Response(
                chat_message=TextMessage(content="No messages received", source=self.name),
                inner_messages=[],
            )
            return

        search_keyword = self._extract_message_from_source(messages, "search_assistant")
        router_agent = self._extract_message_from_source(messages, "router_agent")
        if search_keyword:
            keyword = search_keyword.replace("search:", "", 1).strip()
            # Split the keyword by comma to search with multiple keywords if provided
            keywords = [k.strip() for k in keyword.split(",") if k.strip()]
            all_results = {}
            for k in keywords:
                try:
                    result = search_tracks(client=self.spotify_client, keyword=k)
                    all_results[k] = result
                except Exception as err:
                    logger.error("Error searching tracks for '%s': %s", k, err)
                    all_results[k] = "Error searching tracks"
            response_content = json.dumps(all_results)
            yield Response(
                chat_message=TextMessage(content=response_content, source=self.name),
                inner_messages=[],
            )
        # Uncomment the block below to handle playlist creation logic.
        # elif search_keyword and "create_playlist:" in search_keyword:
        #     tracks = search_keyword.replace("create_playlist:", "", 1).strip()
        #     try:
        #         result = create_playlist(client=self.spotify_client, tracks=tracks, name="My Playlist")
        #         yield TextMessage(content=result, source=self.name)
        #         yield Response(
        #             chat_message=TextMessage(content="Playlist created", source=self.name),
        #             inner_messages=[],
        #         )
        #     except Exception as err:
        #         logger.error("Error creating playlist: %s", err)
        #         yield Response(
        #             chat_message=TextMessage(content="Error creating playlist", source=self.name),
        #             inner_messages=[],
        #         )
        else:
            yield Response(
                chat_message=TextMessage(content="No valid action message detected.", source=self.name),
                inner_messages=[],
            )

    def _extract_message_from_source(
        self, messages: Sequence[ChatMessage], source: str
    ) -> Optional[str]:
        """
        Extracts and returns the content of the first message from the given source.
        """
        for message in messages:
            if message.source == source:
                return message.content
        return None

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        """
        Resets any stateful components if necessary.
        No specific reset actions are required for this agent.
        """
        pass
