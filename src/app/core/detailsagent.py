import logging
from typing import AsyncGenerator, Sequence, Optional, Type

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import AgentEvent, ChatMessage, TextMessage
from autogen_core import CancellationToken
from .prompt import PromptManager
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.model_context import BufferedChatCompletionContext
        

logger = logging.getLogger(__name__)

class PlaylistDetailsAgent(AssistantAgent):
    def __init__(self, name: str, query_text: str, model_client=None) -> None:
        prompt = PromptManager().get_prompt("details_agent_prompt", query=query_text)
        context = BufferedChatCompletionContext(buffer_size=1)  # <-- Only last message
        
        super().__init__(
            name=name,
            system_message=prompt,
            model_client=model_client,
            # output_content_type=str,
            model_context=BufferedChatCompletionContext(buffer_size=1),
        )