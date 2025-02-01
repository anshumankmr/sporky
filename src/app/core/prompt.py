"""Module for managing prompts in the YouTube Buddy application.

This module provides functionality to store and retrieve various prompts used
throughout the application for consistent user interaction.
"""

class PromptManager:
    """Manages a collection of predefined prompts for the application."""

    def __init__(self):
        """Initialize the PromptManager with default prompts."""
        self.prompts = {
            'greeting': "Hello! How can I assist you with your playlist today?",
            'system': """You are an AI music expert with extensive knowledge of various genres, artists, and music history.
You can provide recommendations, analyze music, discuss music theory, and help users discover new music based on their preferences.
Your expertise covers classical, jazz, rock, pop, electronic, hip-hop, and world music.
Keep responses friendly, informative, and focused on music-related topics."""
        }

    def get_prompt(self, prompt_name, **kwargs):
        """Retrieve and format a prompt by its name.
        
        Args:
            prompt_name (str): The name of the prompt to retrieve
            **kwargs: Format parameters for the prompt
            
        Returns:
            str: The formatted prompt string
        """
        prompt = self.prompts.get(prompt_name, "")
        return prompt.format(**kwargs)