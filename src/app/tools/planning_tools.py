"""
planning_tools.py - Tool definitions for the Planning Agent

These tools are used by the executor to perform actions based on the planner's decisions.
"""
import os
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from langchain_core.tools import tool
import firebase_admin
from firebase_admin import firestore

from .spotify_tools import create_spotify_client, search_tracks as spotify_search, create_playlist as spotify_create_playlist


# ============================================================================
# Tool Input Schemas
# ============================================================================

class SearchSpotifyInput(BaseModel):
    """Input schema for Spotify search."""
    query: str = Field(description="Search query - can be artist name, song title, genre, mood, or any combination")
    limit: int = Field(default=10, description="Maximum number of tracks to return (1-50)")
    max_year: Optional[int] = Field(default=None, description="Only return tracks released before this year")


class CommitPlaylistInput(BaseModel):
    """Input schema for committing playlist to memory."""
    playlist_name: str = Field(description="Name for the playlist")
    tracks: List[Dict[str, Any]] = Field(description="List of track objects to save")
    description: Optional[str] = Field(default="", description="Optional playlist description")


class ReadPlaylistInput(BaseModel):
    """Input schema for reading playlist from memory."""
    playlist_name: Optional[str] = Field(default=None, description="Name of specific playlist to retrieve")
    list_all: bool = Field(default=False, description="If true, list all saved playlists instead of retrieving one")


class SaveToSpotifyInput(BaseModel):
    """Input schema for saving playlist to Spotify."""
    playlist_name: str = Field(description="Name for the Spotify playlist")
    tracks: List[Dict[str, Any]] = Field(description="List of track objects with URIs")
    description: Optional[str] = Field(default="", description="Playlist description")


# ============================================================================
# Tool Implementations
# ============================================================================

@tool(args_schema=SearchSpotifyInput)
def search_spotify(query: str, limit: int = 10, max_year: Optional[int] = None) -> Dict[str, Any]:
    """
    Search Spotify for tracks matching the query.

    Use this tool when the user wants to:
    - Find songs by a specific artist
    - Discover tracks matching a genre or mood
    - Get song recommendations based on criteria
    - Search for specific songs by name

    Returns a dictionary with track information including name, artist, album, and URI.
    """
    try:
        client = create_spotify_client()
        tracks = spotify_search(client, query, limit, max_year)
        return {
            "success": True,
            "query": query,
            "tracks": tracks,
            "count": len(tracks)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "tracks": []
        }


@tool(args_schema=CommitPlaylistInput)
def commit_playlist_to_memory(
    playlist_name: str,
    tracks: List[Dict[str, Any]],
    description: str = "",
    session_id: str = ""
) -> Dict[str, Any]:
    """
    Save a playlist to Firebase memory for later reference.

    Use this tool when:
    - The user wants to save their current selection for later
    - Building a playlist incrementally across multiple interactions
    - Creating a named collection without pushing to Spotify yet

    Returns confirmation with the saved playlist details.
    """
    try:
        if not session_id:
            return {
                "success": False,
                "error": "Session ID is required to save playlist to memory"
            }

        db = firestore.client()

        # Store in playlists collection under session_id
        doc_ref = db.collection('playlists').document(session_id).collection('saved_playlists').document(playlist_name)

        playlist_data = {
            "name": playlist_name,
            "tracks": tracks,
            "description": description,
            "track_count": len(tracks)
        }

        doc_ref.set(playlist_data)

        return {
            "success": True,
            "playlist_name": playlist_name,
            "track_count": len(tracks),
            "message": f"Playlist '{playlist_name}' saved with {len(tracks)} tracks"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@tool(args_schema=ReadPlaylistInput)
def read_playlist_from_memory(
    playlist_name: Optional[str] = None,
    list_all: bool = False,
    session_id: str = ""
) -> Dict[str, Any]:
    """
    Read a previously saved playlist from Firebase memory.

    Use this tool when:
    - User asks to recall a previously saved playlist
    - User wants to see their saved playlists
    - Need to retrieve tracks for modification or export to Spotify

    Returns the playlist tracks or a list of available playlists.
    """
    try:
        if not session_id:
            return {
                "success": False,
                "error": "Session ID is required to read playlists from memory"
            }

        db = firestore.client()
        collection_ref = db.collection('playlists').document(session_id).collection('saved_playlists')

        if list_all:
            # List all saved playlists
            docs = collection_ref.stream()
            playlists = []
            for doc in docs:
                data = doc.to_dict()
                playlists.append({
                    "name": data.get("name", doc.id),
                    "track_count": data.get("track_count", 0),
                    "description": data.get("description", "")
                })

            return {
                "success": True,
                "playlists": playlists,
                "count": len(playlists)
            }
        else:
            # Get specific playlist
            if not playlist_name:
                return {
                    "success": False,
                    "error": "Please provide a playlist name or set list_all=True"
                }

            doc_ref = collection_ref.document(playlist_name)
            doc = doc_ref.get()

            if not doc.exists:
                return {
                    "success": False,
                    "error": f"Playlist '{playlist_name}' not found"
                }

            data = doc.to_dict()
            return {
                "success": True,
                "playlist_name": playlist_name,
                "tracks": data.get("tracks", []),
                "description": data.get("description", ""),
                "track_count": data.get("track_count", 0)
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@tool(args_schema=SaveToSpotifyInput)
def save_playlist_to_spotify(
    playlist_name: str,
    tracks: List[Dict[str, Any]],
    description: str = ""
) -> Dict[str, Any]:
    """
    Save a playlist directly to the user's Spotify account.

    IMPORTANT: This action creates a real playlist in the user's Spotify library.
    This tool should only be used after receiving user approval.

    Use this tool when:
    - User explicitly requests to save/export to their Spotify account
    - User has confirmed they want to create a Spotify playlist

    Returns success confirmation with Spotify playlist URL.
    """
    try:
        client = create_spotify_client()

        # Create playlist on Spotify
        result = spotify_create_playlist(
            client=client,
            tracks=tracks,
            name=playlist_name,
            description=description
        )

        # Get the playlist URL
        user_id = client.me()['id']
        playlists = client.user_playlists(user_id, limit=1)
        playlist_url = playlists['items'][0]['external_urls']['spotify'] if playlists['items'] else None

        return {
            "success": True,
            "playlist_name": playlist_name,
            "track_count": len(tracks) if isinstance(tracks, list) else sum(len(t) for t in tracks.values()),
            "spotify_url": playlist_url,
            "message": f"Playlist '{playlist_name}' created on Spotify!"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# Tool Registry
# ============================================================================

TOOL_REGISTRY = {
    "search_spotify": search_spotify,
    "commit_playlist_to_memory": commit_playlist_to_memory,
    "read_playlist_from_memory": read_playlist_from_memory,
    "save_playlist_to_spotify": save_playlist_to_spotify,
}

# List of tools for LangChain agent
TOOLS = [
    search_spotify,
    commit_playlist_to_memory,
    read_playlist_from_memory,
    save_playlist_to_spotify,
]


def get_tool_descriptions() -> str:
    """Generate tool descriptions for the planner prompt."""
    descriptions = []
    for tool in TOOLS:
        descriptions.append(f"- **{tool.name}**: {tool.description}")
    return "\n".join(descriptions)
