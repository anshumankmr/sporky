import { Link, useNavigate } from 'react-router-dom';
// import './Sidebar.css'; // You'll need to create this CSS file

function Sidebar({ startNewChat }) {
  const navigate = useNavigate();
  
  const handleNewChat = () => {
    startNewChat();
    navigate('/chat'); // Navigate to chat view
  };

  return (
    <div className="sidebar">
      <h1>Sporky AI</h1>
      <button className="new-chat-btn" onClick={handleNewChat}>New Chat</button>
      
      <nav className="sidebar-nav">
        <ul>
          <li>
            <Link to="/chat">Chat</Link>
          </li>
          <li>
            <Link to="/signup">Sign Up</Link>
          </li>
          {/* More nav links can be added here as new components are created */}
        </ul>
      </nav>
    </div>
  );
}

export default Sidebar;