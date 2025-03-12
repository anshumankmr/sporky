"""
LLM Config
"""
import os
from autogen_core.models import ChatCompletionClient

openai_config = {
    "provider": "OpenAIChatCompletionClient",
    "config": {
        "model": "gpt-4o",
        "api_key": os.getenv("OPENAI_API_KEY")
    }
}

groq_config = {
    "provider": "autogen_ext.models.openai.OpenAIChatCompletionClient",
    "component_type": "model",
    "version": 1,
    "component_version": 1,
    "description": "Chat completion client for Groq models",
    "label": "GroqChatCompletionClient",
    "config": {
        "model": "llama-3.3-70b-versatile",
        "model_info": {
            "vision": False,
            "function_calling": True,
            "json_output": False,
            "family": "llama"
        },
        "base_url": "https://api.groq.com/openai/v1",
        "api_key": os.getenv("GROQ_API_KEY")
    }
}

openai_client = ChatCompletionClient.load_component(openai_config)
groq_client = ChatCompletionClient.load_component(groq_config)