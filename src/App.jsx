import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import Header from './components/Header';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Books from './pages/Books';
import OCRScan from './pages/OCRScan';
import Transactions from './pages/Transactions';
import Users from './pages/Users';
import './styles/global.css';

function PrivateRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  return user ? children : <Navigate to="/login" />;
}

function LibrarianRoute({ children }) {
  const { user, profile, loading } = useAuth();

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/login" />;
  }

  return profile?.role === 'librarian' ? children : <Navigate to="/" />;
}

export default function App() {
  return (
    <Router>
      <Header />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <PrivateRoute>
              <Dashboard />
            </PrivateRoute>
          }
        />
        <Route
          path="/books"
          element={
            <PrivateRoute>
              <Books />
            </PrivateRoute>
          }
        />
        <Route
          path="/scan"
          element={
            <PrivateRoute>
              <OCRScan />
            </PrivateRoute>
          }
        />
        <Route
          path="/transactions"
          element={
            <LibrarianRoute>
              <Transactions />
            </LibrarianRoute>
          }
        />
        <Route
          path="/users"
          element={
            <LibrarianRoute>
              <Users />
            </LibrarianRoute>
          }
        />
      </Routes>
    </Router>
  );
}
