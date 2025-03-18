import { useState, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import './App.css';

function App() {
  // State initialization
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [sessionId, setSessionId] = useState(uuidv4());
  const [isLoading, setIsLoading] = useState(false);

  // API URL
  const API_URL = "http://127.0.0.1:8080/query";

  // Welcome message
  const WELCOME_MESSAGE = `Hi there! I'm Sporky 😄

I'm here to help you create the perfect playlist for any mood. Let's make some musical magic together!`;

  // Suggestion chips
  const suggestions = [
    "Workout music",
    "Stuff to listen while working",
    "Sleep music",
    "something completely random"
  ];

  // Initialize chat with welcome message
  useEffect(() => {
    setMessages([{
      role: "assistant",
      content: WELCOME_MESSAGE
    }]);
  }, []);

  // Send message to API
  const sendMessage = async (message) => {
    // Add user message to chat
    setMessages(prevMessages => [...prevMessages, { role: "user", content: message }]);
    setShowSuggestions(false);
    setInput('');
    setIsLoading(true);

    // Prepare API request
    try {
      const payload = {
        query: message,
        session_id: sessionId
      };

      // Try POST request first
      try {
        const response = await fetch(API_URL, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: JSON.stringify(payload)
        });

        if (response.ok) {
          const responseData = await response.json();
          
          if (responseData) {
            const botResponse = responseData.response || "I didn't get a response. Please try again.";
            setMessages(prevMessages => [...prevMessages, { role: "assistant", content: botResponse }]);
          } else {
            throw new Error("Empty response received");
          }
          setIsLoading(false);
          return;
        }
        
        // If POST fails with 405, try GET as fallback
        if (response.status === 405) {
          throw new Error("POST method not allowed, trying GET");
        } else {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
      } catch (postError) {
        console.log("POST request failed:", postError.message);
        
        // Try GET request with query parameters
        const queryParams = new URLSearchParams({
          query: message,
          session_id: sessionId
        }).toString();
        
        const getResponse = await fetch(`${API_URL}?${queryParams}`, {
          method: 'GET',
          headers: { 
            'Accept': 'application/json'
          }
        });

        if (!getResponse.ok) {
          throw new Error(`GET request also failed with status: ${getResponse.status}`);
        }

        const responseData = await getResponse.json();
        
        if (responseData) {
          const botResponse = responseData.response || "I didn't get a response. Please try again.";
          setMessages(prevMessages => [...prevMessages, { role: "assistant", content: botResponse }]);
        } else {
          throw new Error("Empty response received from GET request");
        }
      }
    } catch (error) {
      setMessages(prevMessages => [...prevMessages, { 
        role: "assistant", 
        content: `I apologize, but I encountered an error: ${error.message}. Please check your server configuration.` 
      }]);
      console.error("API request failed:", error);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim()) {
      sendMessage(input);
    }
  };

  // Start new chat
  const startNewChat = () => {
    setMessages([{
      role: "assistant",
      content: WELCOME_MESSAGE
    }]);
    setShowSuggestions(true);
    setSessionId(uuidv4());
  };

  return (
    <div className="app-container">
      <div className="sidebar">
        <h1>Sporky AI</h1>
        <button className="new-chat-btn" onClick={startNewChat}>New Chat</button>
      </div>
      
      <div className="main-content">
        <div className="chat-container">
          {messages.map((message, index) => (
            <div key={index} className={`message ${message.role}`}>
              <div className="message-content">{message.content}</div>
              
              {/* Show suggestions only after welcome message */}
              {index === 0 && message.role === "assistant" && showSuggestions && (
                <div className="suggestion-chips">
                  {suggestions.map((suggestion) => (
                    <button
                      key={suggestion}
                      className="suggestion-chip"
                      onClick={() => sendMessage(suggestion)}
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
          {isLoading && (
            <div className="message assistant">
              <div className="message-content">Loading...</div>
            </div>
          )}
        </div>
        
        <form className="input-form" onSubmit={handleSubmit}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask Sporky for music recommendations..."
            className="chat-input"
            disabled={isLoading}
          />
          <button type="submit" className="send-button" disabled={isLoading}>
            {isLoading ? "Sending..." : "Send"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default App;