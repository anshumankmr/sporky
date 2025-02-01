"""
Main application entry point for the YouTube Buddy service.
This module serves as the entry point for running the FastAPI application.
It configures the server to run on the specified port (default 8080) and host (0.0.0.0).
Environment Variables:
    PORT (optional): The port number to run the server on. Defaults to 8080.
"""
import os
import uvicorn
from app import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="127.0.0.1", port=port)
