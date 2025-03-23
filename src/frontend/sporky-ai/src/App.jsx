import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useState } from 'react';
import { v4 as uuidv4 } from 'uuid';
import './App.css';
import ChatApp from './components/chatapp/chatapp';
import SignupForm from './components/signupform/signupform';
import Sidebar from './components/sidebar/sidebar';

function App() {
  // Global state that might be needed across components
  const [sessionId, setSessionId] = useState(uuidv4());
  
  // Start new chat - can be passed to components that need it
  const startNewChat = () => {
    setSessionId(uuidv4());
  };

  return (
    <Router>
      <div className="app-container">
        <Sidebar startNewChat={startNewChat} />
        
        <div className="main-content">
          <Routes>
            <Route path="/chat" element={<ChatApp sessionId={sessionId} />} />
            <Route path="/signup" element={<SignupForm />} />
            {/* Redirect to chat by default */}
            <Route path="*" element={<Navigate to="/chat" replace />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;