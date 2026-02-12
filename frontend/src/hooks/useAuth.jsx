import { createContext, useContext, useState, useEffect } from 'react';
import { authService } from '../services/auth';

const AuthContext = createContext();
const RETRY_DELAYS_MS = [250, 500];

const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms));

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const login = async (email, otp) => {
    await authService.login(email, otp);
    const userData = await refreshUser();
    return userData;
  };

  const logout = async () => {
    await authService.logout();
    setUser(null);
  };

  const refreshUser = async () => {
    for (let attempt = 0; attempt <= RETRY_DELAYS_MS.length; attempt += 1) {
      try {
        const userData = await authService.getCurrentUser();
        setUser(userData);
        return userData;
      } catch (error) {
        if (attempt >= RETRY_DELAYS_MS.length) {
          setUser(null);
          return null;
        }
        await wait(RETRY_DELAYS_MS[attempt]);
      }
    }

    setUser(null);
    return null;
  };

  useEffect(() => {
    const init = async () => {
      if (typeof window !== 'undefined' && window.location.pathname === '/login') {
        setLoading(false);
        return;
      }

      await refreshUser();
      setLoading(false);
    };
    init();
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
