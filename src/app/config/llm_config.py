"""
LLM Config
"""
import os
openai_config = {
    "config_list": [
        {
            "model": "gpt-4",
            "api_key": os.getenv("OPENAI_API_KEY")
        }
    ]
}

