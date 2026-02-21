import { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import PlaylistCard from '../PlaylistCard';
import './ChatApp.css';

const API_URL = 'http://127.0.0.1:8080/query';

const WELCOME_MESSAGE = `Hi there! I'm Sporky 😄

I'm here to help you create the perfect playlist for any mood. Let's make some musical magic together!`;

const suggestions = [
  "Workout music",
  "Stuff to listen while working",
  "Sleep music",
  "something completely random"
];

function ChatApp({ sessionId }) {
  const { accessToken } = useAuth();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [pendingApproval, setPendingApproval] = useState(false);

  useEffect(() => {
    setMessages([{ role: 'assistant', content: WELCOME_MESSAGE, playlist: null }]);
    setShowSuggestions(true);
    setPendingApproval(false);
  }, [sessionId]);

  const sendMessage = async (message) => {
    setMessages(prev => [...prev, { role: 'user', content: message, playlist: null }]);
    setShowSuggestions(false);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          ...(accessToken ? { 'X-Spotify-Token': accessToken } : {}),
        },
        body: JSON.stringify({ query: message, session_id: sessionId }),
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data = await response.json();
      const botContent = data.response || "I didn't get a response. Please try again.";
      const playlist = Array.isArray(data.playlist) ? data.playlist : null;
      const awaitingApproval = Boolean(data.awaiting_approval);

      setPendingApproval(awaitingApproval);
      setMessages(prev => [...prev, { role: 'assistant', content: botContent, playlist }]);
    } catch (error) {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: `Sorry, I hit an error: ${error.message}. Please try again.`, playlist: null }
      ]);
      console.error('API error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      sendMessage(input.trim());
    }
  };

  const placeholder = pendingApproval
    ? 'Type yes or no...'
    : 'Ask Sporky for music recommendations...';

  return (
    <div className="chat-component">
      <div className="chat-container">
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.role}`}>
            <div className="message-content">{message.content}</div>

            {message.playlist && <PlaylistCard tracks={message.playlist} />}

            {index === 0 && message.role === 'assistant' && showSuggestions && (
              <div className="suggestion-chips">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    className="suggestion-chip"
                    onClick={() => sendMessage(s)}
                  >
                    {s}
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
          placeholder={placeholder}
          className={`chat-input${pendingApproval ? ' chat-input--approval' : ''}`}
          disabled={isLoading}
        />
        <button type="submit" className="send-button" disabled={isLoading || !input.trim()}>
          {isLoading ? '...' : 'Send'}
        </button>
      </form>
    </div>
  );
}

export default ChatApp;