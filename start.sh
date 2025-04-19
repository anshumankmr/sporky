#!/bin/sh

# Start nginx
nginx

# Start FastAPI in the background
uvicorn src.app.main:app --host 0.0.0.0 --port 8080 &

# Start Streamlit with the correct base URL path
streamlit run chat.py --server.port 8501 --server.baseUrlPath=/chat --server.address 0.0.0.0 &

# Wait for all processes to complete
wait