import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

function Sidebar({ startNewChat }) {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const handleNewChat = () => {
    startNewChat();
    navigate('/chat');
  };

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="sidebar">
      <h1>Sporky AI</h1>
      <button className="new-chat-btn" onClick={handleNewChat}>New Chat</button>

      <div style={{ flex: 1 }} />

      {user && (
        <div className="sidebar-user">
          {user.images && user.images[0] && (
            <img
              src={user.images[0].url}
              alt={user.display_name}
              className="sidebar-user__avatar"
            />
          )}
          <span className="sidebar-user__name">{user.display_name}</span>
          <button className="sidebar-logout-btn" onClick={handleLogout}>
            Log out
          </button>
        </div>
      )}
    </div>
  );
}

export default Sidebar;