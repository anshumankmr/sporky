import traceback
import os
from functools import wraps
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
from agent import get_music_recommendations
import firebase_admin
from firebase_admin import credentials, firestore
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify your frontend's URL
    allow_credentials=True,
    allow_methods=["*"],  # This allows POST, GET, OPTIONS, etc.
    allow_headers=["*"],
)

class QueryText(BaseModel):
    """
    Data model for incoming query text.
    """
    query: str
    history: list = []
    session_id: str
    playlist: str = ""

# Initialize Firestore
if not firebase_admin._apps:
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if cred_path:
        firebase_admin.initialize_app(options={
            'databaseURL': os.getenv('FIREBASE_DB_URL')
        })
    else:
        cred = credentials.Certificate(os.getenv('FIREBASE_CREDENTIALS_PATH'))
        firebase_admin.initialize_app(cred, {
            'databaseURL': os.getenv('FIREBASE_DB_URL')
        })

db = firestore.client()

def fetch_hist():
    """
    fetch hist as pre-hook, response as post-hook
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(query_text: QueryText):
            # Fetch history before execution
            doc_ref = db.collection('chat_history').document(query_text.session_id)
            doc = doc_ref.get()
            if doc.exists:
                query_text.history = doc.to_dict().get('history', [])
                print(query_text.history)
            
            # Fetch playlist before execution
            playlist_doc_ref = db.collection('playlists').document(query_text.session_id)
            playlist_doc = playlist_doc_ref.get()
            if playlist_doc.exists:
                query_text.playlist = playlist_doc.to_dict().get('playlist', '')

            # Execute the original function
            result = await func(query_text)

            # Clean up response if needed
            if isinstance(result, dict) and "response" in result:
                result["response"] = result["response"].replace(
                    "<END_CONVERSATION>", ""
                )

            # Optionally, update playlist in Firestore if it was modified in the response
            if isinstance(result, dict) and "playlist" in result:
                playlist = result["playlist"]
                playlist_doc_ref = db.collection('playlists').document(query_text.session_id)
                playlist_doc_ref.set({'playlist': playlist}, merge=True)
                # Attaching playlist information to query_text for further processing.
                query_text.__setattr__('playlist', playlist)

            # Save updated history after execution
            doc_ref.set({
                'history': result["state"]
            })
            return result
        return wrapper
    return decorator

@app.post("/query")
@fetch_hist()
async def handle_query(query_text: QueryText):
    """
    Handles incoming POST requests with query text and returns music recommendations.

    Args:
        query_text (QueryText): The incoming query containing the search text and session ID

    Returns:
        dict: Music recommendations and conversation results
    """
    try:
        result = await get_music_recommendations(
            query=query_text.query,
            history=query_text.history,
            playlist=query_text.playlist
        )
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))