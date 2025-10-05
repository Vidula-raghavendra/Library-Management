import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../services/supabase';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isSignup, setIsSignup] = useState(false);
  const [fullName, setFullName] = useState('');
  const [membershipId, setMembershipId] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) throw error;

      navigate('/');
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const { data: authData, error: authError } = await supabase.auth.signUp({
        email,
        password,
      });

      if (authError) throw authError;

      if (authData.user) {
        const { error: profileError } = await supabase
          .from('users')
          .insert([
            {
              id: authData.user.id,
              email,
              full_name: fullName,
              membership_id: membershipId || `MEM${Date.now()}`,
              role: 'member',
            },
          ]);

        if (profileError) throw profileError;

        navigate('/');
      }
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>
          <span style={styles.icon}>📚</span>
          Library Management System
        </h1>

        {error && <div className="error">{error}</div>}

        <form onSubmit={isSignup ? handleSignup : handleLogin}>
          {isSignup && (
            <>
              <div className="input-group">
                <label>Full Name</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                  placeholder="Enter your full name"
                />
              </div>

              <div className="input-group">
                <label>Membership ID (optional)</label>
                <input
                  type="text"
                  value={membershipId}
                  onChange={(e) => setMembershipId(e.target.value)}
                  placeholder="Leave blank for auto-generation"
                />
              </div>
            </>
          )}

          <div className="input-group">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="Enter your email"
            />
          </div>

          <div className="input-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="Enter your password"
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
            style={styles.submitBtn}
          >
            {loading ? 'Processing...' : isSignup ? 'Sign Up' : 'Login'}
          </button>
        </form>

        <div style={styles.toggle}>
          <button
            onClick={() => setIsSignup(!isSignup)}
            style={styles.toggleBtn}
          >
            {isSignup
              ? 'Already have an account? Login'
              : "Don't have an account? Sign Up"}
          </button>
        </div>

        <div style={styles.demoInfo}>
          <p style={styles.demoTitle}>Demo Credentials:</p>
          <p>Librarian: librarian@library.com / password123</p>
          <p>Member: member@library.com / password123</p>
        </div>
      </div>
    </div>
  );
}

const styles = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    padding: '20px',
  },
  card: {
    background: 'white',
    borderRadius: '16px',
    padding: '40px',
    maxWidth: '500px',
    width: '100%',
    boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
  },
  title: {
    textAlign: 'center',
    color: '#333',
    marginBottom: '30px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
  },
  icon: {
    fontSize: '40px',
  },
  submitBtn: {
    width: '100%',
    marginTop: '8px',
  },
  toggle: {
    textAlign: 'center',
    marginTop: '20px',
  },
  toggleBtn: {
    background: 'none',
    border: 'none',
    color: '#667eea',
    cursor: 'pointer',
    fontSize: '16px',
    fontWeight: '600',
  },
  demoInfo: {
    marginTop: '30px',
    padding: '16px',
    background: '#f5f5f5',
    borderRadius: '8px',
    textAlign: 'center',
    fontSize: '14px',
  },
  demoTitle: {
    fontWeight: '700',
    marginBottom: '8px',
    color: '#667eea',
  },
};
