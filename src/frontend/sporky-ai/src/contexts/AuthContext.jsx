import { createContext, useContext, useState, useEffect, useCallback } from 'react';

const AuthContext = createContext(null);

const STORAGE_KEYS = {
  ACCESS_TOKEN: 'sporky_access_token',
  REFRESH_TOKEN: 'sporky_refresh_token',
  EXPIRES_AT: 'sporky_expires_at',
  USER: 'sporky_user',
};

function loadFromStorage() {
  try {
    return {
      accessToken: localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN),
      refreshToken: localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN),
      expiresAt: parseInt(localStorage.getItem(STORAGE_KEYS.EXPIRES_AT) || '0', 10),
      user: JSON.parse(localStorage.getItem(STORAGE_KEYS.USER) || 'null'),
    };
  } catch {
    return { accessToken: null, refreshToken: null, expiresAt: 0, user: null };
  }
}

function saveToStorage({ accessToken, refreshToken, expiresAt, user }) {
  localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, accessToken || '');
  if (refreshToken) localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refreshToken);
  localStorage.setItem(STORAGE_KEYS.EXPIRES_AT, String(expiresAt || 0));
  if (user) localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user));
}

function clearStorage() {
  Object.values(STORAGE_KEYS).forEach(k => localStorage.removeItem(k));
}

async function fetchUserProfile(accessToken) {
  const res = await fetch('https://api.spotify.com/v1/me', {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) throw new Error('Failed to fetch user profile');
  return res.json();
}

async function refreshAccessToken(refreshToken) {
  const clientId = import.meta.env.VITE_SPOTIFY_CLIENT_ID;
  const body = new URLSearchParams({
    grant_type: 'refresh_token',
    refresh_token: refreshToken,
    client_id: clientId,
  });

  const res = await fetch('https://accounts.spotify.com/api/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  });

  if (!res.ok) throw new Error('Token refresh failed');
  return res.json();
}

export function AuthProvider({ children }) {
  const stored = loadFromStorage();
  const [accessToken, setAccessToken] = useState(stored.accessToken);
  const [refreshToken, setRefreshToken] = useState(stored.refreshToken);
  const [expiresAt, setExpiresAt] = useState(stored.expiresAt);
  const [user, setUser] = useState(stored.user);
  const [loading, setLoading] = useState(true);

  const isAuthenticated = Boolean(accessToken) && Date.now() < expiresAt;

  const storeTokens = useCallback(async ({ access_token, refresh_token, expires_in }) => {
    const newExpiresAt = Date.now() + expires_in * 1000 - 60_000; // 1 min buffer
    setAccessToken(access_token);
    if (refresh_token) setRefreshToken(refresh_token);
    setExpiresAt(newExpiresAt);

    const profile = await fetchUserProfile(access_token);
    setUser(profile);

    saveToStorage({
      accessToken: access_token,
      refreshToken: refresh_token || refreshToken,
      expiresAt: newExpiresAt,
      user: profile,
    });
  }, [refreshToken]);

  const logout = useCallback(() => {
    setAccessToken(null);
    setRefreshToken(null);
    setExpiresAt(0);
    setUser(null);
    clearStorage();
  }, []);

  // On mount: check if token needs refresh
  useEffect(() => {
    async function init() {
      const { accessToken: at, refreshToken: rt, expiresAt: exp } = loadFromStorage();
      if (at && rt && Date.now() >= exp) {
        // Token expired — try to refresh
        try {
          const data = await refreshAccessToken(rt);
          await storeTokens(data);
        } catch {
          logout();
        }
      }
      setLoading(false);
    }
    init();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const value = {
    accessToken,
    refreshToken,
    user,
    isAuthenticated,
    loading,
    storeTokens,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
