from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
from autogen import ConversableAgent
from fastapi import FastAPI
from pydantic import BaseModel
from config.llm_config import openai_config
from tools.spotify_tools import search_tracks, create_playlist
from agent import get_music_recommendations
app = FastAPI()

class QueryText(BaseModel):
    """
    Data model for incoming query text.
    """
    query: str
    history: list = []


@app.post("/query")
async def handle_query(query_text: QueryText):
    """
    Handle incoming query text and return the response.
    """
    result = await get_music_recommendations(query_text.query, query_text.history)
    return result
