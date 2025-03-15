# Sporky: AI-Powered Spotify Music Recommendation System

Sporky is an intelligent music recommendation system that leverages AI agents to provide personalized music suggestions through natural language conversations. Using AutoGen's agent-based architecture, Sporky understands your music preferences and delivers curated Spotify recommendations.

## Features

- **Natural Language Interface**: Describe your music preferences or mood in natural language
- **Multi-Agent System**: Leverages AutoGen to create a conversation flow between specialized agents
- **Spotify Integration**: Searches and recommends tracks directly from Spotify's extensive catalog
- **Conversation History**: Maintains context across sessions for personalized recommendations
- **Firebase Backend**: Stores conversation history and playlist data securely

## Architecture

The system is built on a multi-agent architecture:

- **Router Agent**: Analyzes user input and determines the appropriate action
- **Search Assistant**: Formulates search queries based on user preferences
- **Spotify Search Agent**: Interfaces with the Spotify API to find matching tracks
- **Format Assistant**: Structures recommendations in a user-friendly format

## Tech Stack

- **Backend**: FastAPI
- **Frontend**: Streamlit (current), ShadCDN (planned)
- **Database**: Firebase Firestore
- **AI Framework**: AutoGen
- **LLM Providers**: OpenAI, Groq
- **Music API**: Spotify

## Prerequisites

- Python 3.9+
- Spotify Developer Account
- Firebase Project
- OpenAI API Key or Groq API Key

## Installation

1. Clone the repository
```bash
git clone https://github.com/yourusername/sporky.git
cd sporky
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Configure environment variables in `launch.json`

```json
{
    "configurations": [
        {
            "name": "Python: FastAPI",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "app:app",
                "--reload"
            ],
            "env": {
                "OPENAI_API_KEY": "your_openai_api_key",
                "GROQ_API_KEY": "your_groq_api_key",
                "SPOTIFY_CLIENT_ID": "your_spotify_client_id",
                "SPOTIFY_CLIENT_SECRET": "your_spotify_client_secret",
                "FIREBASE_CREDENTIALS_PATH": "path/to/firebase-credentials.json",
                "FIREBASE_DB_URL": "your_firebase_database_url"
            }
        }
    ]
}
```

## Running the Application

### Backend
```bash
uvicorn app:app --reload
```

### Frontend
```bash
streamlit run chat.py
```

## API Endpoints

- `POST /query`: Submit a music recommendation query

**Request Body:**
```json
{
  "query": "I need upbeat songs for my morning workout",
  "session_id": "user123",
  "history": [],
  "playlist": ""
}
```

## Project Structure

```
sporky/
├── app.py                  # FastAPI application entry point
├── agent.py                # Core agent wrapper and orchestration
├── core/
│   ├── prompt.py           # Prompt management
│   ├── spotifyagent.py     # Spotify API agent
│   └── prompts/            # Directory containing prompt templates
├── config/
│   └── llm_config.py       # LLM configuration
├── tools/
│   ├── spotify_tools.py    # Spotify API utilities
│   └── llm_tools.py        # LLM response processing utilities
└── chat.py                 # Streamlit frontend
```

## Planned Updates

- ShadCDN frontend implementation
- Improved playlist generation features
- User authentication
- More sophisticated recommendation algorithms

## License

This project is licensed under the [GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.en.html) - see the [LICENSE](LICENSE) file for details.

This license:
- Requires anyone who distributes this code or a derivative work to make the source available
- Requires modifications to be released under the same license
- Applies even when the software is used as a service over a network

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

