import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './OnboardingPage.css';

export default function OnboardingPage() {
  const [tasteConsent, setTasteConsent] = useState(true);
  const navigate = useNavigate();

  const handleLetsGo = () => {
    localStorage.setItem('onboarding_complete', 'true');
    localStorage.setItem('taste_profile_consent', tasteConsent ? 'true' : 'false');
    navigate('/chat', { replace: true });
  };

  return (
    <div className="onboarding-page">
      <div className="onboarding-card">
        <h1 className="onboarding-title">Before we start...</h1>
        <p className="onboarding-subtitle">
          Just a couple of things to know about how Sporky works.
        </p>

        <div className="onboarding-items">
          <label className="onboarding-item">
            <input
              type="checkbox"
              className="onboarding-checkbox"
              checked={tasteConsent}
              onChange={(e) => setTasteConsent(e.target.checked)}
            />
            <div className="onboarding-item__text">
              <span className="onboarding-item__title">Taste profile analysis</span>
              <span className="onboarding-item__desc">
                Allow Sporky to analyse your listening preferences to improve recommendations.
              </span>
            </div>
          </label>
        </div>

        <button className="onboarding-btn" onClick={handleLetsGo}>
          Let's go!
        </button>
      </div>
    </div>
  );
}
