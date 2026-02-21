import { useState } from 'react';
import './CookieBanner.css';

export default function CookieBanner() {
  const [visible, setVisible] = useState(() => {
    return localStorage.getItem('cookie_consent') === null;
  });

  if (!visible) return null;

  const handleDecision = (decision) => {
    localStorage.setItem('cookie_consent', decision);
    setVisible(false);
  };

  return (
    <div className="cookie-banner">
      <p className="cookie-banner__text">
        We use cookies to keep you logged in and remember your preferences.
      </p>
      <div className="cookie-banner__actions">
        <button className="cookie-banner__btn cookie-banner__btn--accept" onClick={() => handleDecision('accepted')}>
          Accept
        </button>
        <button className="cookie-banner__btn cookie-banner__btn--decline" onClick={() => handleDecision('declined')}>
          Decline
        </button>
      </div>
    </div>
  );
}
