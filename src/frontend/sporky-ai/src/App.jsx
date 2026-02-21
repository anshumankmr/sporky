import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useState } from 'react';
import { v4 as uuidv4 } from 'uuid';
import './App.css';

import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import CookieBanner from './components/CookieBanner';
import ChatApp from './components/chatapp/chatapp';
import Sidebar from './components/sidebar/sidebar';
import LoginPage from './pages/LoginPage';
import CallbackPage from './pages/CallbackPage';
import OnboardingPage from './pages/OnboardingPage';

function LoginOrCallback() {
  const { search } = useLocation();
  return new URLSearchParams(search).has('code') ? <CallbackPage /> : <LoginPage />;
}

function App() {
  const [sessionId, setSessionId] = useState(uuidv4());

  const startNewChat = () => {
    setSessionId(uuidv4());
  };

  return (
    <AuthProvider>
      <CookieBanner />
      <Router>
        <Routes>
          <Route path="/login" element={<LoginOrCallback />} />
          <Route path="/callback" element={<CallbackPage />} />
          <Route path="/onboarding" element={<OnboardingPage />} />
          <Route
            path="/chat"
            element={
              <ProtectedRoute>
                <div className="app-container">
                  <Sidebar startNewChat={startNewChat} />
                  <div className="main-content">
                    <ChatApp sessionId={sessionId} />
                  </div>
                </div>
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/chat" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
