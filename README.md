# Sporky: Planning Agent-Based Music Recommendation System

## What This Is

Sporky is a conversational AI system that generates personalized Spotify playlists through natural language interaction. Unlike typical chatbots that simply answer questions, Sporky uses a **Planning Agent architecture** to break down complex music requests into executable steps, search Spotify, manage playlists in memory, and optionally export them to your Spotify account.

**In one sentence:** A stateful, multi-step orchestration system that translates natural language music requests into concrete Spotify playlists via LLM-powered planning and execution.

## Why This Exists

### Problem Statement
1. Users want personalized music recommendations but don't want to manually search Spotify
2. Complex requests ("workout music but not too aggressive, with some 80s vibes") require multiple searches and filtering
3. Users want to build playlists incrementally over conversations
4. Exporting to Spotify should feel natural, not mechanical

### Solution Approach
Rather than a single LLM call that returns search keywords, Sporky:
- **Plans** multi-step workflows dynamically based on user intent
- **Executes** those plans using discrete tools (search, save, recall)
- **Maintains state** across conversation turns via Firebase
- **Handles failures** by replanning when tools fail
- **Protects user accounts** by requiring explicit approval for Spotify modifications

## Who This Is For

- **End users:** Anyone who wants AI-powered music curation without leaving a chat interface
- **Developers:** Engineers learning LangGraph, planning agents, or tool-based LLM architectures
- **Music enthusiasts:** People who want opinionated recommendations (Sporky has personality)

## System Architecture

### High-Level Component Map

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│  - Streamlit (chat.py) OR React app (src/frontend/sporky-ai)   │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP POST /query
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND (app.py)                   │
│  - Session management                                           │
│  - Firebase history fetch/save                                  │
│  - Approval state persistence                                   │
└────────────────────────┬────────────────────────────────────────┘
                         │ Calls agent.py
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PLANNING AGENT (agent.py)                    │
│  - Entry point: get_music_recommendations()                     │
│  - Creates initial state                                        │
│  - Invokes LangGraph workflow                                   │
└────────────────────────┬────────────────────────────────────────┘
                         │ Runs graph
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                 LANGGRAPH WORKFLOW (graph.py)                   │
│                                                                  │
│  START → planner_node → executor_node (loop) → format_assistant │
│              ↓              ↓                         ↓          │
│              └──────→ replanner_node ←───────────────┘          │
│              └──────→ approval_handler_node                     │
│                                                                  │
│  State flows through nodes, each updates PlanningAgentState     │
└────────────────────────┬────────────────────────────────────────┘
                         │ Nodes call tools
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  TOOLS (tools/planning_tools.py)                │
│  - search_spotify: Query Spotify API                            │
│  - commit_playlist_to_memory: Save to Firebase                  │
│  - read_playlist_from_memory: Recall from Firebase              │
│  - save_playlist_to_spotify: Create real Spotify playlist       │
└────────────────────────┬────────────────────────────────────────┘
                         │ Integrates with
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                            │
│  - Spotify API (via spotipy)                                    │
│  - Firebase Firestore (session storage, playlists, approval)    │
│  - LLM Providers (OpenAI, Groq, Gemini via LangChain)           │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

#### 1. Frontend Layer
- **Streamlit (chat.py):** Quick prototype UI, Spotify-themed chat interface
- **React (src/frontend/sporky-ai):** Modern, planned frontend (currently basic)
- **Responsibilities:** Display messages, send user queries, show suggestion chips

#### 2. FastAPI Backend (app.py)
- **Primary role:** Orchestrate request lifecycle
- **Key functions:**
  - Fetch conversation history from Firebase before processing
  - Check for pending approval state (did user leave mid-approval?)
  - Call agent.py to generate response
  - Save updated history and approval state back to Firebase
  - Clean up response artifacts (e.g., `<END_CONVERSATION>` tags)
- **Critical detail:** The `@fetch_hist()` decorator wraps `/query` to handle Firebase I/O automatically

#### 3. Planning Agent (agent.py)
- **Purpose:** Interface between FastAPI and LangGraph
- **Key function:** `get_music_recommendations(query, session_id, history, pending_state)`
  - If `pending_state` exists → resume from approval pause
  - Otherwise → create fresh state and run main graph
- **Outputs:** Dict with `response`, `state`, `playlist`, `awaiting_approval`, `pending_state`

#### 4. LangGraph Workflow (graph.py)
Defines two graphs:

**Main Graph (build_planning_agent_graph):**
```
START → planner → [executor loop or END] → format_assistant → END
            ↓
      (may set awaiting_approval=True, pausing at END)
```

**Approval Continuation Graph (build_approval_continuation_graph):**
```
START → approval_handler → [executor or END] → format_assistant → END
```

**Routing logic:**
- After planner: If requires approval → END (pause)
- After executor: If needs_replan → replanner, else continue or format
- Executor can also set awaiting_approval=True mid-execution

#### 5. Nodes (nodes/)

**planner_node (nodes/planner.py):**
- **Input:** User query, conversation history, saved playlists
- **Process:** 
  1. Format context (history, playlists) into prompt
  2. Call LLM with planner_prompt.md
  3. Parse JSON plan from LLM response
- **Output:** Plan as list of `{"step": N, "tool": "...", "args": {...}, "reasoning": "..."}`
- **Special:** If plan includes `save_playlist_to_spotify`, sets `awaiting_approval=True`

**executor_node (nodes/executor.py):**
- **Input:** Current step index, plan, step_results
- **Process:**
  1. Get current step from plan
  2. Resolve argument placeholders (e.g., `RESULT_STEP_1` → actual tracks from step 1)
  3. Check if tool is `save_playlist_to_spotify` and approval not granted → pause
  4. Invoke tool from TOOL_REGISTRY
  5. Store result, advance step counter
- **Output:** Updated `step_results`, incremented `current_step`, or `needs_replan=True` on failure

**approval_handler_node (nodes/executor.py):**
- **Input:** User's reply to approval prompt
- **Process:**
  1. Use LLM to interpret reply (approve/reject/other)
  2. If approved → clear `awaiting_approval`, continue execution
  3. If rejected → end gracefully
  4. If unclear → ask again
- **Critical:** Uses APPROVAL_DECISION_PROMPT to parse natural language ("yeah sure" → approve)

**replanner_node (nodes/replanner.py):**
- **Input:** Original plan, completed steps, failed step, error reason
- **Process:**
  1. Use LLM to create adjusted plan
  2. Option A: New plan to work around failure
  3. Option B: Admit defeat, set `cannot_fulfill=True`
- **Output:** New plan or error message

**format_assistant_node (nodes/format_assistant.py):**
- **Input:** All step_results
- **Process:**
  1. Extract tracks/playlists from results
  2. Create summary string
  3. Use LLM with FORMAT_PROMPT to generate friendly response
- **Output:** `formatted_response` string

#### 6. Tools (tools/planning_tools.py)

**search_spotify:**
- Calls `spotify_tools.search_tracks()`
- Returns `{"success": True, "tracks": [...], "count": N}`

**commit_playlist_to_memory:**
- Saves playlist to Firebase under `playlists/{session_id}/saved_playlists/{playlist_name}`
- Session-scoped (each user has their own saved playlists)

**read_playlist_from_memory:**
- Retrieves specific playlist or lists all saved playlists
- Used when user says "recall my workout playlist"

**save_playlist_to_spotify:**
- Creates actual Spotify playlist via `spotify_tools.create_playlist()`
- **Requires approval** - executor pauses before calling this

#### 7. State Management (state.py)

**PlanningAgentState (TypedDict):**
```python
{
    # Input
    "query": str,
    "history": List[Dict],
    "session_id": str,
    
    # Planning
    "plan": List[PlanStep],
    "plan_string": str,  # Raw LLM output for debugging
    
    # Execution
    "current_step": int,
    "step_results": Dict[str, Any],  # {"step_1": {...}, "step_2": {...}}
    "execution_complete": bool,
    
    # Approval
    "awaiting_approval": bool,
    "pending_action": Dict,
    "user_approved": bool,
    
    # Re-planning
    "needs_replan": bool,
    "replan_reason": str,
    
    # Output
    "formatted_response": str,
    "error": str
}
```

**State flow:** Each node receives state, updates it, returns delta. LangGraph merges updates.

### Data Flow Example

**User Query:** "Top 5 Queen songs but not Bohemian Rhapsody"

1. **Frontend → Backend:**
   ```json
   POST /query
   {"query": "Top 5 Queen songs but not Bohemian Rhapsody", "session_id": "abc123"}
   ```

2. **Backend → Agent:**
   - Fetch history from Firebase
   - Call `get_music_recommendations(query, session_id, history)`

3. **Agent → LangGraph → Planner:**
   - Planner receives query + history
   - LLM generates plan:
     ```json
     {
       "plan": [
         {"step": 1, "tool": "search_spotify", "args": {"query": "We Will Rock You by Queen", "limit": 1}},
         {"step": 2, "tool": "search_spotify", "args": {"query": "Radio Ga Ga by Queen", "limit": 1}},
         {"step": 3, "tool": "search_spotify", "args": {"query": "We Are The Champions by Queen", "limit": 1}},
         {"step": 4, "tool": "search_spotify", "args": {"query": "Don't Stop Me Now by Queen", "limit": 1}},
         {"step": 5, "tool": "search_spotify", "args": {"query": "Another One Bites The Dust by Queen", "limit": 1}}
       ]
     }
     ```

4. **Executor Loop:**
   - Step 1: Call `search_spotify("We Will Rock You by Queen", 1)` → returns track
   - Step 2: Call `search_spotify("Radio Ga Ga by Queen", 1)` → returns track
   - ... continues for all 5 steps
   - `step_results = {"step_1": {...}, "step_2": {...}, ..., "step_5": {...}}`

5. **Format Assistant:**
   - Extracts all tracks from step_results
   - LLM formats into friendly response:
     ```
     Here are 5 essential Queen tracks (skipping Bohemian Rhapsody):
     
     1. We Will Rock You - Queen (News of the World)
     2. Radio Ga Ga - Queen (The Works)
     3. We Are The Champions - Queen (News of the World)
     4. Don't Stop Me Now - Queen (Jazz)
     5. Another One Bites The Dust - Queen (The Game)
     ```

6. **Backend → Frontend:**
   - Save conversation to Firebase
   - Return `{"response": "...", "playlist": [...]}`

7. **Frontend displays response**

### Approval Flow Example

**User Query:** "Save this to my Spotify"

1. Planner creates plan with `save_playlist_to_spotify` step
2. Sets `requires_approval=True`, `approval_message="Create 'Workout Mix' (15 tracks) on Spotify?"`
3. Executor reaches `save_playlist_to_spotify` step, checks `user_approved` → False
4. Sets `awaiting_approval=True`, `pending_action={...}`, pauses
5. Backend saves `pending_state` to Firebase, returns to user with approval message
6. User replies: "yeah do it"
7. Backend detects `pending_state` exists, calls `get_music_recommendations(query="yeah do it", pending_state=...)`
8. Agent uses approval continuation graph: START → approval_handler
9. Approval handler uses LLM to parse "yeah do it" → decision="approve"
10. Sets `user_approved=True`, `awaiting_approval=False`
11. Executor resumes, actually calls `save_playlist_to_spotify` tool
12. Playlist created, formatted response returned

## Mental Model

### Think of Sporky as a Three-Layer Cake

**Layer 1: The Brain (LLM)**
- Makes decisions: "Given this query, what should I do?"
- Creates plans: "Search for X, then save results as Y"
- Understands intent: "User said 'yeah sure' → they approved"

**Layer 2: The Hands (Tools)**
- Execute concrete actions: search Spotify, save to Firebase, create playlists
- Each tool has a clear contract: inputs → outputs
- Tools don't make decisions, they just do work

**Layer 3: The Memory (State + Firebase)**
- Conversation history: What did we talk about?
- Session playlists: What did I save for this user?
- Approval state: Did user authorize Spotify modification?

### The Planning Agent Pattern

**Traditional chatbot:**
```
User: "Find me workout music"
LLM: "Here are some keywords: high energy, electronic, 130+ BPM"
[End of story - user has to manually search]
```

**Planning Agent:**
```
User: "Find me workout music"
Planner: "I will: (1) search 'high energy workout', (2) search 'electronic gym music', (3) combine results"
Executor: [Runs step 1] [Runs step 2] [Runs step 3]
Formatter: "Here are 20 tracks for your workout: ..."
```

**Why this matters:**
- LLM makes strategic decisions (what to search, how many results)
- Tools make no decisions (just execute)
- System can self-correct (replanner on failure)
- User gets finished product, not instructions

### Key Abstractions

1. **Plan:** List of steps, each step is `{tool, args, reasoning}`
2. **State:** Snapshot of everything the system knows at a given moment
3. **Node:** Pure function that receives state, returns state updates
4. **Tool:** Function that does real-world action (API call, database write)
5. **Graph:** State machine that routes between nodes based on conditions

## Goals and Non-Goals

### Goals
- ✅ Translate natural language → actionable Spotify playlists
- ✅ Handle complex, multi-part requests ("workout music but mellow, save it, then find similar")
- ✅ Maintain conversation context across turns
- ✅ Protect user Spotify accounts (approval required for writes)
- ✅ Recover gracefully from tool failures (replanner)
- ✅ Demonstrate production-grade planning agent architecture
- Real-time music playback (just creates playlists)
- User authentication system (assumes Spotify OAuth handled externally)

### Non-Goals
- ❌ Recommendation algorithm improvements (uses Spotify's search as-is)
- ❌ Multi-user collaboration on playlists
- ❌ Mobile app (web interface only)

### Design Trade-offs

**Chose LangGraph over raw LLM calls:**
- **Pro:** Explicit state management, replayability, easier debugging
- **Con:** More boilerplate, steeper learning curve

**Chose Firebase over SQL:**
- **Pro:** Easy document storage, fast setup, free tier
- **Con:** Limited querying, vendor lock-in

**Chose approval flow over blind execution:**
- **Pro:** User safety, no accidental playlist overwrites
- **Con:** Extra conversation turn, interrupts flow

**Chose session-scoped memory over user accounts:**
- **Pro:** No auth complexity, works immediately
- **Con:** Playlists lost if session ID changes

## Setup & Usage

### Prerequisites
```bash
Python 3.9+
Node.js 16+ (for React frontend)
Spotify Developer Account
Firebase Project
OpenAI/Groq/Google API Key
```

### Backend Setup

1. **Clone repository**
   ```bash
   git clone https://github.com/anshumankmr/sporky
   cd sporky
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment** (create `launch.json` or `.env`)
   ```json
   {
     "OPENAI_API_KEY": "sk-...",
     "GROQ_API_KEY": "...",
     "GOOGLE_API_KEY": "...",
     "SPOTIFY_CLIENT_ID": "...",
     "SPOTIFY_CLIENT_SECRET": "...",
     "SPOTIFY_REDIRECT_URI": "http://localhost:8080/callback",
     "GOOGLE_APPLICATION_CREDENTIALS": "path/to/firebase-key.json",
     "FIREBASE_DB_URL": "https://your-project.firebaseio.com",
     "LOCAL": "false"
   }
   ```

4. **Firebase setup**
   - Create Firestore collections: `chat_history`, `playlists`, `pending_approvals`
   - Download service account key, set path in env vars

5. **Spotify OAuth**
   - Create app at https://developer.spotify.com/dashboard
   - Add redirect URI: `http://localhost:8080/callback`
   - Get client ID/secret

6. **Run backend**
   ```bash
   cd src/app
   uvicorn app:app --reload --port 8080
   ```

### Frontend Setup (Streamlit)

```bash
streamlit run chat.py
```

### Frontend Setup (React)

```bash
cd src/frontend/sporky-ai
npm install
npm run dev
# Open http://localhost:5173
```

### API Endpoints

**POST /query**
```json
Request:
{
  "query": "Find me chill lo-fi beats",
  "session_id": "user-123",
  "history": [...],
  "playlist": ""
}

Response:
{
  "response": "Here are 10 chill lo-fi tracks: ...",
  "state": {...},
  "playlist": [{name, artist, uri, album}, ...],
  "awaiting_approval": false
}
```

**GET /health**
```json
{"status": "healthy"}
```

## How to Extend

### Add a New Tool

1. **Define tool in `tools/planning_tools.py`:**
   ```python
   from langchain_core.tools import tool
   from pydantic import BaseModel, Field
   
   class MyToolInput(BaseModel):
       param: str = Field(description="What this param does")
   
   @tool(args_schema=MyToolInput)
   def my_new_tool(param: str) -> Dict[str, Any]:
       """Description of what this tool does."""
       # Implementation
       return {"success": True, "result": "..."}
   ```

2. **Register tool:**
   ```python
   TOOL_REGISTRY["my_new_tool"] = my_new_tool
   TOOLS.append(my_new_tool)
   ```

3. **Update planner prompt (`core/prompts/planner_prompt.md`):**
   ```markdown
   ## Available Tools
   
   4. **my_new_tool** - What it does
      - Args: `param` (string)
      - Use for: When to use this tool
   ```

4. **LLM will now include your tool in plans**

### Add a New Node

1. **Create node in `nodes/my_node.py`:**
   ```python
   from state import PlanningAgentState
   
   async def my_node(state: PlanningAgentState) -> Dict[str, Any]:
       # Process state
       return {"some_field": "updated_value"}
   ```

2. **Register in graph (`graph.py`):**
   ```python
   workflow.add_node("my_node", my_node)
   workflow.add_edge("some_node", "my_node")
   ```

3. **Update routing logic if needed**

### Add a New Prompt

1. **Create `core/prompts/my_prompt.md`:**
   ```markdown
   You are an assistant that does X.
   
   Given: {input_var}
   
   Do Y.
   ```

2. **PromptManager auto-loads it:**
   ```python
   prompt_manager = PromptManager()
   prompt = prompt_manager.get_prompt("my_prompt", input_var="value")
   ```

### Change LLM Provider

Edit `config/llm_config.py`:
```python
def get_model_client():
    # Switch between OpenAI, Groq, Gemini
    return get_groq_client()  # or get_openai_client() or get_gemini_client()
```

## Design Philosophy

### 1. Separation of Concerns
- **LLM = Brain:** Makes decisions, creates plans
- **Tools = Hands:** Execute concrete actions
- **State = Memory:** Stores what happened
- **Nodes = Nervous System:** Routes information

### 2. Explicit Over Implicit
- State updates are explicit (return dict of changes)
- Tool arguments are typed (Pydantic schemas)
- Routing logic is visible (conditional edges in graph)
- No hidden magic, no spooky action at a distance

### 3. Fail Gracefully
- Tools return `{"success": False, "error": "..."}` not exceptions
- Replanner adjusts plans when tools fail
- Approval handler asks for clarification on ambiguous input
- Format assistant provides fallback on LLM errors

### 4. User Safety First
- Approval required for Spotify writes
- LLM interprets natural language approval (not brittle string matching)
- Pending state persisted to Firebase (survives crashes)

### 5. Opinionated Agent
- Sporky has personality ("enthusiastic audiophile")
- Makes specific recommendations, not generic keywords
- Example: "Top 5 Queen songs" → actual song names, not "popular Queen tracks"

### 6. Session-Scoped Memory
- Each session has independent saved playlists
- Conversation history per session
- Trade-off: Simple implementation, no cross-session recall

## Current State vs. Roadmap

### Implemented 
- Planning agent workflow (planner → executor → formatter)
- Replanning on failure
- Approval flow for Spotify saves
- Session memory (playlists, history)
- Spotify search & playlist creation
- Multiple LLM providers (OpenAI, Groq, Gemini)
- Streamlit UI
- Basic React UI
- Firebase persistence

### In Progress 🚧
- ShadCDN frontend (mentioned in README but not implemented)
- User authentication (OAuth is mentioned but not integrated)

### Future Roadmap 🔮
- **User accounts:** Persistent playlists across sessions
- **Playlist editing:** Add/remove tracks from existing playlists
- **Collaborative playlists:** Share and co-create with others
- **Advanced filtering:** Tempo, energy, key, danceability
- **Multi-language support:** Non-English queries
- **Voice interface:** Speak your music requests
- **Analytics:** Track usage patterns, popular searches

## Technical Details

### LangGraph Specifics

**State updates are merged:**
```python
# Node returns delta
return {"current_step": state["current_step"] + 1}

# LangGraph merges into state
new_state = {**old_state, "current_step": old_state["current_step"] + 1}
```

**Conditional edges:**
```python
workflow.add_conditional_edges(
    "executor",
    should_continue,  # Function that returns next node name
    {
        "executor": "executor",      # Loop
        "replanner": "replanner",    # Adjust plan
        "format_assistant": "format_assistant",  # Done
        END: END                     # Pause
    }
)
```

**Two graphs:**
1. Main graph: For new queries
2. Approval graph: For resuming after approval pause

### Firebase Schema

```
chat_history/
  {session_id}/
    history: [...]
    
playlists/
  {session_id}/
    playlist: [...]  # Legacy
    saved_playlists/
      {playlist_name}/
        name: str
        tracks: [...]
        description: str
        track_count: int

pending_approvals/
  {session_id}/
    state: {...}  # Full PlanningAgentState
```

### Prompt Engineering

**Planner prompt:** Generates JSON plan
- Few-shot examples of good plans
- Emphasizes specific songs over generic searches
- Handles exclusion criteria ("not X")

**Approval decision prompt:** Interprets natural language
- Few-shot: "yeah sure" → approve, "nah" → reject
- Returns structured JSON: `{decision, reason}`

**Format prompt:** Friendly response generation
- Takes raw step results
- Converts to conversational response
- Maintains Sporky's personality

### Error Handling Strategy

**Level 1: Tool failure**
```python
try:
    result = tool.invoke(args)
except Exception as e:
    return {"success": False, "error": str(e)}
```

**Level 2: Executor detects failure**
```python
if not result.get("success"):
    return {"needs_replan": True, "replan_reason": error}
```

**Level 3: Replanner creates adjusted plan**
```python
# LLM analyzes what failed, creates new plan
# If cannot fix, sets cannot_fulfill=True
```

**Level 4: Format assistant shows error message**
```python
if state.get("error"):
    return {"formatted_response": f"Sorry, {error}"}
```

## Where to Start as a New Contributor

### Understanding the System (30 min)
1. Read this README fully
2. Examine `state.py` - understand what data flows through the system
3. Look at `graph.py` - see how nodes connect
4. Read one prompt file (`core/prompts/planner_prompt.md`)

### Running Locally (15 min)
1. Set up Firebase (or mock it with in-memory dict for testing)
2. Get Spotify API credentials
3. Add one LLM API key (OpenAI or Groq)
4. Run backend: `uvicorn src.app.app:app --reload`
5. Run Streamlit: `streamlit run chat.py`
6. Send a test query: "Find me 5 workout songs"

### Making Your First Change (1 hour)
**Easy wins:**
- Add a suggestion chip to `chat.py`
- Modify Sporky's personality in `core/prompts/sporky_system_prompt.md`
- Add a new tool (e.g., `filter_by_year` that removes tracks older than N)

**Medium challenges:**
- Add a new node (e.g., `deduplication_node` that removes duplicate tracks)
- Implement a new approval type (e.g., require approval for playlists > 50 tracks)
- Add playlist editing (remove track from saved playlist)

**Deep dives:**
- Optimize the replanner (currently uses full history, could be smarter)
- Add streaming responses (format_assistant streams as it generates)
- Implement multi-turn playlist refinement ("make it more upbeat")

## License

Apache License 2.0 - See LICENSE file.

**Note:** AGPL-3.0 mentioned in README.md is outdated. Current LICENSE file is Apache 2.0.

---

## Final Mental Model

**Sporky is a state machine.**

- **Input:** Natural language query + conversation history
- **State:** 12-field TypedDict tracking plan, execution, approval
- **Nodes:** Pure functions that update state
- **Tools:** Side-effecting functions (Spotify, Firebase)
- **Output:** Formatted response + updated state

**The graph is a compiler.**

- **Source code:** User's natural language
- **Compilation:** Planner generates execution plan (AST)
- **Execution:** Executor runs plan (interpreter)
- **Output:** Formatted response (compiled artifact)

**The whole system is a loop-closer.**

Traditional chatbots open loops: "Here's what you should search for."  
Sporky closes loops: "Here's your playlist, ready to play."

That's the entire architecture in three sentences.