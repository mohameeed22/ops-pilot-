import React, { useState } from 'react';
import { login } from '../api';

export default function Login({ onLoginSuccess }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.append('username', email);
      params.append('password', password);
      
      const data = await login(params);
      localStorage.setItem('opspilot_token', data.access_token);
      onLoginSuccess(data.user);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', alignItems: 'center', justifyContent: 'center', background: 'var(--clr-bg)' }}>
      <div className="card" style={{ width: 400, padding: 30 }}>
        <div style={{ textAlign: 'center', marginBottom: 30 }}>
          <div style={{ fontSize: '2rem', marginBottom: 10 }}>⚡</div>
          <h2 style={{ fontSize: '1.5rem', color: 'var(--clr-fg)' }}>Ops-Pilot</h2>
          <p style={{ color: 'var(--clr-muted)' }}>Sign in to continue</p>
        </div>
        
        {error && <div className="error-box" style={{ marginBottom: 20 }}>{error}</div>}
        
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 15 }}>
          <div>
            <label style={{ display: 'block', marginBottom: 5, fontSize: '0.85rem', color: 'var(--clr-muted)' }}>Email</label>
            <input 
              type="email" 
              className="search-input" 
              style={{ width: '100%' }}
              value={email} 
              onChange={e => setEmail(e.target.value)} 
              required 
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: 5, fontSize: '0.85rem', color: 'var(--clr-muted)' }}>Password</label>
            <input 
              type="password" 
              className="search-input" 
              style={{ width: '100%' }}
              value={password} 
              onChange={e => setPassword(e.target.value)} 
              required 
            />
          </div>
          <button 
            type="submit" 
            style={{ 
              marginTop: 10, 
              padding: '10px', 
              background: 'var(--clr-primary)', 
              color: 'white', 
              border: 'none', 
              borderRadius: 6, 
              cursor: 'pointer',
              fontWeight: 600
            }}
            disabled={loading}
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}
