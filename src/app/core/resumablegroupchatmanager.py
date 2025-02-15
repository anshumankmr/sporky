"""
Manager of Conversation Stater
"""
from typing import Dict, List, Tuple, Union,Optional,List,Dict
from autogen import GroupChat, GroupChatManager

class ResumableGroupChatManager(GroupChatManager):
    """
    A GroupChatManager that can resume conversations from previous history.
    """
    def __init__(self, groupchat: GroupChat, history: Optional[List[Dict]] = None, **kwargs):
        # First call super().__init__ to properly set up the GroupChatManager
        super().__init__(groupchat=groupchat, **kwargs)
        
        # Then handle the history if provided
        if history:
            groupchat.messages = history
            self.restore_from_history(history)
    
    def restore_from_history(self, history: List[Dict]) -> None:
        """Restore conversation state from history."""
        for message in history:
            # Broadcast the message to all agents except the speaker
            for agent in self._groupchat.agents:
                if agent.name != message.get("name"):
                    self.send(message, agent, request_reply=False, silent=True)

