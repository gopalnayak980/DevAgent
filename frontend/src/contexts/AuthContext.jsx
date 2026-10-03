import { createContext, useContext, useState, useCallback, useEffect } from 'react';

const AuthContext = createContext();

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => sessionStorage.getItem('token'));
  const [isLoading, setIsLoading] = useState(true);
  const [authError, setAuthError] = useState(null);

  useEffect(() => {
    if (token) {
      sessionStorage.setItem('token', token);
    } else {
      sessionStorage.removeItem('token');
    }
  }, [token]);

  const fetchProfile = useCallback(async () => {
    if (!token) {
      setIsLoading(false);
      return;
    }
    
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setUser(data);
      } else {
        setToken(null);
        setUser(null);
      }
    } catch (err) {
      console.error("Failed to fetch profile", err);
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const login = async (email, password) => {
    setAuthError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Login failed');
      }
      
      // Write to sessionStorage IMMEDIATELY so authFetch reads the correct
      // token before React's useEffect runs after the re-render.
      sessionStorage.setItem('token', data.access_token);
      setToken(data.access_token);
      setUser(data.user);
      return true;
    } catch (err) {
      setAuthError(err.message);
      return false;
    }
  };

  const register = async (name, email, password, confirmPassword) => {
    setAuthError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          name, 
          email, 
          password, 
          confirm_password: confirmPassword 
        })
      });
      
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Registration failed');
      }
      
      // Write to sessionStorage IMMEDIATELY so authFetch reads the correct
      // token before React's useEffect runs after the re-render.
      sessionStorage.setItem('token', data.access_token);
      setToken(data.access_token);
      setUser(data.user);
      return true;
    } catch (err) {
      setAuthError(err.message);
      return false;
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
  };

  // Helper for authenticated requests.
  // Reads the token from sessionStorage at call time to avoid stale closure bugs.
  //
  // NOTE: authFetch does NOT call logout() on 401. A 401 from any individual
  // endpoint may be transient (race condition, expired mid-session, etc.).
  // The ONLY authoritative session-clearing path is fetchProfile() via
  // /api/auth/me, which explicitly validates the current token.
  const authFetch = useCallback(async (url, options = {}) => {
    const currentToken = sessionStorage.getItem('token');
    const headers = {
      ...options.headers,
      'Authorization': `Bearer ${currentToken}`
    };
    if (!options.headers?.['Content-Type'] && !(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }
    
    const response = await fetch(`${API_BASE_URL}${url}`, {
      ...options,
      headers
    });
    
    // Return the response as-is. Do not auto-logout on 401 here.
    return response;
  }, []);

  return (
    <AuthContext.Provider value={{ 
      user, 
      token, 
      isLoading, 
      authError, 
      login, 
      register, 
      logout,
      authFetch
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
