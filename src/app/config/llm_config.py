"""
LLM Config
"""
import os
from autogen_core.models import ChatCompletionClient, ModelFamily
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.models.ollama import OllamaChatCompletionClient
from autogen_core.models import ModelInfo

openai_config = {
    "provider": "OpenAIChatCompletionClient",
    "config": {
        "model": "o3-mini",
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
        # "model": "deepseek-r1-distill-llama-70b",
                "model": "llama-3.3-70b-versatile",

        # "model": "llama-3.1-8b-instant",
        "model_info": {
            "vision": False,
            "function_calling": True,
            "json_output": False,
            "family": "llama",
            "structured_output": False

        },
        "base_url": "https://api.groq.com/openai/v1",
        "api_key": os.getenv("GROQ_API_KEY")
    }
}

openai_client = ChatCompletionClient.load_component(openai_config)
groq_client = ChatCompletionClient.load_component(groq_config)


# gemini_config = {
#     "provider": "autogen_ext.models.openai.OpenAIChatCompletionClient",
#     "component_type": "model",
#     "version": 1,
#     "component_version": 1,
#     "description": "Gemini 2.5 Flash client",
#     "label": "GeminiFlashClient",
#     "config": {
#         "model": ModelFamily.GEMINI_2_5_FLASH,
#         # ensure you’re authenticated via GOOGLE_API_KEY + GCP env vars
#     }
# }
gemini_client = OpenAIChatCompletionClient(
    model="gemini-2.5-pro",
    api_key=os.getenv("GOOGLE_API_KEY"),
    model_info=ModelInfo(

        max_tokens=8192,  # or actual context window
        input_cost_per_token=0.0,
        output_cost_per_token=0.0,
        json_output=False,
        function_calling=False,
        structured_output=True,
        vision= False, 
        family="ollama" # <-- this avoids the crash
    )
)


ollama_model_client = OllamaChatCompletionClient(
    model="mistral:7b-instruct",
    model_info=ModelInfo(
        name="deepseek-r1:8b",
        max_tokens=8192,  # or actual context window
        input_cost_per_token=0.0,
        output_cost_per_token=0.0,
        json_output=False,
        function_calling=False,
        structured_output=True,
        vision= False, 
        family="ollama" # <-- this avoids the crash
    )
)