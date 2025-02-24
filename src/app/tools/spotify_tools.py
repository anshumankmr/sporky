"""
spotify_tools.py - Functional approach
"""
import os
from typing import List, Dict, Optional, Callable
from functools import partial
import spotipy
from spotipy.oauth2 import SpotifyOAuth

def get_spotify_assistant_message(messages: List[Dict]) -> str:
    """Extracts the content of the most recent message from the 'spotify_assistant'.
        Args:
            messages (List[Dict]): A list of messages, where each message is a dictionary.
        Returns:
            str: The content of the most recent message with the name 'spotify_assistant', 
                 or an empty string if no such message is found.
    """
    for message in reversed(messages):
        if message.get("name") == "spotify_assistant":
            return message.get("content", "")
    return ""
def create_spotify_client() -> spotipy.Spotify:
    """Create and return a Spotify client."""
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.getenv('SPOTIFY_CLIENT_ID'),
        client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
        redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI'),
        scope='playlist-modify-public'
    ))

def extract_track_info(track_item: Dict) -> Dict:
    """Extract relevant track information from Spotify track item."""
    return {
        'name': track_item['name'],
        'uri': track_item['uri'],
        'artist': track_item['artists'][0]['name'],
        'album': track_item['album']['name'],
        'release_date': track_item['album']['release_date']
    }

def filter_by_year(tracks: List[Dict], max_year: int) -> List[Dict]:
    """Filter tracks by release year."""
    return list(filter(
        lambda track: int(track['release_date'][:4]) <= max_year,
        tracks
    ))

def search_tracks(
    client: spotipy.Spotify,
    keyword: str,
    limit: int = 10,
    max_year: Optional[int] = None
) -> List[Dict]:
    """Search for tracks based on a keyword."""
    print(f"Searching for tracks with keyword: {keyword}")
    results = client.search(q=keyword, type='track', limit=limit * 2)
    tracks = list(map(extract_track_info, results['tracks']['items']))
    
    if max_year:
        tracks = filter_by_year(tracks, max_year)
    
    return tracks[:limit]

def format_track_display(track: Dict, index: int) -> str:
    """Format track information for display."""
    return f"{index}. {track['name']} - {track['artist']} ({track['album']})"

def display_tracks(tracks: List[Dict]) -> None:
    """Display track list."""
    print("\nProposed playlist tracks:")
    for idx, track in enumerate(tracks, 1):
        print(format_track_display(track, idx))

def create_playlist(
    client: spotipy.Spotify,
    tracks: List[Dict],
    name: str,
    description: str = ""
) -> Optional[Dict]:
    """Create a playlist with the given tracks."""
    user_id = client.me()['id']
    playlist = client.user_playlist_create(
        user=user_id,
        name=name,
        description=description
    )
    track_uris = list(map(lambda t: t['uri'], tracks))
    client.playlist_add_items(playlist['id'], track_uris)
    return playlist


# Create partial functions with client for easier usage
def create_spotify_tools(client: spotipy.Spotify = None) -> Dict[str, Callable]:
    """Create a collection of spotify tools with bound client."""
    client = client or create_spotify_client()
    return {
        'search_tracks': partial(search_tracks, client),
        'create_playlist': partial(create_playlist, client)
    }

# Usage example:
    # if __name__ == "__main__":
    #     spotify = create_spotify_tools()
    #     tracks = spotify['search_tracks']("Elton John", limit=5)
    #     spotify['create_playlist'](tracks, "Elton John Playlist")