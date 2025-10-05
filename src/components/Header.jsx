import { Link, useNavigate } from 'react-router-dom';
import { supabase } from '../services/supabase';
import { useAuth } from '../hooks/useAuth';

export default function Header() {
  const { user, profile } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await supabase.auth.signOut();
    navigate('/login');
  };

  return (
    <header style={styles.header}>
      <div style={styles.container}>
        <Link to="/" style={styles.logo}>
          <span style={styles.icon}>📚</span>
          Library Management
        </Link>

        <nav style={styles.nav}>
          {user ? (
            <>
              <Link to="/" style={styles.link}>Dashboard</Link>
              <Link to="/books" style={styles.link}>Books</Link>
              <Link to="/scan" style={styles.link}>OCR Scan</Link>
              {profile?.role === 'librarian' && (
                <>
                  <Link to="/transactions" style={styles.link}>Transactions</Link>
                  <Link to="/users" style={styles.link}>Users</Link>
                </>
              )}
              <div style={styles.userInfo}>
                <span style={styles.userName}>{profile?.full_name}</span>
                <button onClick={handleLogout} className="btn btn-secondary" style={styles.logoutBtn}>
                  Logout
                </button>
              </div>
            </>
          ) : (
            <Link to="/login" style={styles.link}>Login</Link>
          )}
        </nav>
      </div>
    </header>
  );
}

const styles = {
  header: {
    background: 'white',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    marginBottom: '30px',
  },
  container: {
    maxWidth: '1400px',
    margin: '0 auto',
    padding: '16px 20px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  logo: {
    fontSize: '24px',
    fontWeight: '700',
    color: '#667eea',
    textDecoration: 'none',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  icon: {
    fontSize: '32px',
  },
  nav: {
    display: 'flex',
    alignItems: 'center',
    gap: '24px',
  },
  link: {
    color: '#333',
    textDecoration: 'none',
    fontWeight: '600',
    transition: 'color 0.3s',
  },
  userInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginLeft: '12px',
    paddingLeft: '12px',
    borderLeft: '2px solid #e0e0e0',
  },
  userName: {
    fontWeight: '600',
    color: '#667eea',
  },
  logoutBtn: {
    padding: '8px 16px',
    fontSize: '14px',
  },
};
