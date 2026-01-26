"""
FastAPI application for the Planning Agent music recommendation service.
"""
import traceback
import os
import logging
from functools import wraps
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from agent import get_music_recommendations
import firebase_admin
from firebase_admin import credentials, firestore
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryText(BaseModel):
    """Data model for incoming query text."""
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


def get_pending_state(session_id: str) -> Optional[Dict[str, Any]]:
    """Get pending approval state from Firestore."""
    try:
        doc_ref = db.collection('pending_approvals').document(session_id)
        doc = doc_ref.get()
        if doc.exists:
            state = doc.to_dict().get('state')
            logger.debug(f"Found pending state for {session_id}: keys={list(state.keys()) if state else None}")
            return state
        return None
    except Exception as e:
        logger.error(f"Error getting pending state: {e}")
        return None


def save_pending_state(session_id: str, state: Dict[str, Any]) -> None:
    """Save pending approval state to Firestore."""
    try:
        doc_ref = db.collection('pending_approvals').document(session_id)
        doc_ref.set({'state': state})
        logger.debug(f"Saved pending state for {session_id}")
    except Exception as e:
        logger.error(f"Error saving pending state: {e}")


def clear_pending_state(session_id: str) -> None:
    """Clear pending approval state from Firestore."""
    try:
        doc_ref = db.collection('pending_approvals').document(session_id)
        doc_ref.delete()
        logger.debug(f"Cleared pending state for {session_id}")
    except Exception as e:
        logger.error(f"Error clearing pending state: {e}")


def fetch_hist():
    """
    Decorator to fetch history before execution and save state after.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(query_text: QueryText):
            # Fetch history before execution
            doc_ref = db.collection('chat_history').document(query_text.session_id)
            doc = doc_ref.get()
            if doc.exists:
                query_text.history = doc.to_dict().get('history', [])

            # Execute the original function
            result = await func(query_text)

            # Clean up response if needed
            if isinstance(result, dict) and "response" in result:
                result["response"] = result["response"].replace(
                    "<END_CONVERSATION>", ""
                )

            # Save playlist results if present
            if isinstance(result, dict) and "playlist" in result and result["playlist"]:
                playlist = result["playlist"]
                playlist_doc_ref = db.collection('playlists').document(query_text.session_id)
                playlist_doc_ref.set({'playlist': playlist}, merge=True)

            # Handle pending approval state
            if isinstance(result, dict) and result.get("awaiting_approval"):
                # Save the pending state for later continuation
                if "pending_state" in result:
                    save_pending_state(query_text.session_id, result["pending_state"])
            else:
                # Clear any pending state on successful completion
                clear_pending_state(query_text.session_id)

            # Save updated history after execution
            if isinstance(result, dict) and "state" in result:
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
        # Check if there's a pending approval for this session
        pending_state = get_pending_state(query_text.session_id)

        if pending_state:
            # Always resume agent with the user's reply
            # Let the approval_handler_node interpret the response using LLM
            logger.info(f"Resuming from pending state for session {query_text.session_id}")
            logger.debug(f"User reply: {query_text.query}")

            result = await get_music_recommendations(
                query=query_text.query,  # Pass user's reply for LLM interpretation
                session_id=query_text.session_id,
                history=query_text.history,
                pending_state=pending_state
            )
            return result

        # Normal flow - new query
        result = await get_music_recommendations(
            query=query_text.query,
            session_id=query_text.session_id,
            history=query_text.history
        )
        return result

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
