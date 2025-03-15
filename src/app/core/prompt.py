"""
Module for managing prompts in the YouTube Buddy application.
This module provides functionality to store and retrieve various prompts used
throughout the application for consistent user interaction.
"""
import os

class PromptManager:
    """Manages a collection of predefined prompts for the application."""

    def __init__(self):
        """Initialize the PromptManager with default prompts."""
        # Read the spotify prompt from the sporky.md file
        prompts_dir = os.path.join(os.path.dirname(__file__), 'prompts')
        self.prompts = {}
        prompt_files = [f for f in os.listdir(prompts_dir)
                if os.path.isfile(os.path.join(prompts_dir, f)) and f.endswith('.md')]
        for prompt_file in prompt_files:
            prompt_name = os.path.splitext(prompt_file)[0]
            with open(os.path.join(prompts_dir, prompt_file), 'r',encoding='utf-8') as file:
                self.prompts[prompt_name] = file.read().strip()

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