import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function CallbackPage() {
  const { storeTokens } = useAuth();
  const navigate = useNavigate();
  const handled = useRef(false);

  useEffect(() => {
    if (handled.current) return;
    handled.current = true;

    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const error = params.get('error');

    if (error || !code) {
      console.error('Spotify auth error:', error);
      navigate('/login', { replace: true });
      return;
    }

    const verifier = sessionStorage.getItem('pkce_verifier');
    if (!verifier) {
      console.error('PKCE verifier missing');
      navigate('/login', { replace: true });
      return;
    }

    const clientId = import.meta.env.VITE_SPOTIFY_CLIENT_ID;
    const redirectUri = 'http://127.0.0.1:5173/login';

    const body = new URLSearchParams({
      grant_type: 'authorization_code',
      code,
      redirect_uri: redirectUri,
      client_id: clientId,
      code_verifier: verifier,
    });

    fetch('https://accounts.spotify.com/api/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString(),
    })
      .then((res) => {
        if (!res.ok) throw new Error(`Token exchange failed: ${res.status}`);
        return res.json();
      })
      .then(async (data) => {
        sessionStorage.removeItem('pkce_verifier');
        await storeTokens(data);

        const onboardingDone = localStorage.getItem('onboarding_complete');
        navigate(onboardingDone ? '/chat' : '/onboarding', { replace: true });
      })
      .catch((err) => {
        console.error('Token exchange error:', err);
        navigate('/login', { replace: true });
      });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#121212', color: '#fff' }}>
      <p>Connecting to Spotify...</p>
    </div>
  );
}
