"""
LLM Config for LangChain/LangGraph models.
"""
import os
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI


def get_model_client():
    """
    Returns the appropriate LangChain chat model based on environment.
    """
    is_local = os.getenv('LOCAL', 'false').lower() == 'true'

    if is_local:
        return get_gemini_client()
    else:
        return get_openai_client()


def get_openai_client():
    """Returns OpenAI client."""
    return ChatOpenAI(
        model="o3-mini",
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=1  # o3-mini requires temperature=1
    )


def get_groq_client():
    """Returns Groq client."""
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0
    )


def get_gemini_client():
    """Returns Gemini client."""
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0
    )
