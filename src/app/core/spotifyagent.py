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
from tools.llm_tools import extract_json_from_llm_response
from tools.spotify_tools import search_tracks, create_playlist, create_spotify_client

logger = logging.getLogger(__name__)


class SpotifyAgent(AssistantAgent):
    """
    An agent that interfaces with the Spotify API to perform agentic tasks.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name, "An agent that interfaces with Spotify API")
        self.spotify_client = create_spotify_client()
        self.playlist = None
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
        router_action = self._extract_message_from_source(messages, "router_agent")
        print(search_keyword, router_action)
        if search_keyword:
            try:
                # Parse the JSON format from Sporky
                keywords_data = json.loads(search_keyword.replace("search:", "", 1).strip())
                all_results = {}
                
                for item in keywords_data:
                    keyword = item.get("keyword", "").strip()
                    num_results = item.get("results", 10)# Default to 3 if not specified
                    
                    if keyword:
                        try:
                            result = search_tracks(
                                client=self.spotify_client,
                                keyword=keyword,
                                limit=num_results  # Pass the requested number of results
                            )
                            all_results[keyword] = result
                        except ConnectionError as err:
                            logger.error("Error searching tracks for '%s': %s", keyword, err)
                            all_results[keyword] = "Error searching tracks"
                
                response_content = json.dumps(all_results)
                yield Response(
                    chat_message=TextMessage(
                        content=response_content,
                        source=self.name
                    ),
                    inner_messages=[],
                )
            except json.JSONDecodeError as err:
                logger.error("Error parsing JSON from search assistant: %s", err)
                yield Response(
                    chat_message=TextMessage(
                        content="Error parsing search keywords. Expected valid JSON format.",
                        source=self.name
                    ),
                    inner_messages=[],
                )
        elif router_action and json.loads(router_action).get("action") == "make_playlist":
            try:
                details = extract_json_from_llm_response(messages[-1].content)
                result = create_playlist(
                    client=self.spotify_client,
                    tracks=self.playlist,
                    name=details.get("name","My Playlist")
                )
                yield Response(
                    chat_message=TextMessage(
                         content="Playlist created",
                        source=self.name
                    ),
                    inner_messages=[],
                )
            except (ConnectionError, ValueError) as err:
                logger.error("Error creating playlist: %s", err)
                yield Response(
                    chat_message=TextMessage(
                        content="Error creating playlist",
                        source=self.name
                    ),
                    inner_messages=[],
                )
        else:
            yield Response(
                chat_message=TextMessage(
                    content="No valid action message detected.",
                    source=self.name
                ),
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
        del cancellation_token
