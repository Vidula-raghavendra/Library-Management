import { useState, useEffect } from 'react';
import { supabase } from '../services/supabase';
import { useAuth } from '../hooks/useAuth';

export default function Dashboard() {
  const { profile } = useAuth();
  const [stats, setStats] = useState({
    totalBooks: 0,
    availableBooks: 0,
    borrowedBooks: 0,
    totalUsers: 0,
    activeTransactions: 0,
    overdueBooks: 0,
  });
  const [recentTransactions, setRecentTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const { data: books } = await supabase.from('books').select('*');
      const totalBooks = books?.length || 0;
      const availableBooks = books?.reduce((sum, book) => sum + (book.available_copies || 0), 0) || 0;
      const borrowedBooks = books?.reduce((sum, book) => sum + (book.total_copies - book.available_copies), 0) || 0;

      let totalUsers = 0;
      let activeTransactions = 0;
      let overdueBooks = 0;

      if (profile?.role === 'librarian') {
        const { data: users } = await supabase.from('users').select('*');
        totalUsers = users?.length || 0;

        const { data: transactions } = await supabase
          .from('transactions')
          .select('*, books(*), users(*)')
          .order('created_at', { ascending: false })
          .limit(10);

        setRecentTransactions(transactions || []);

        activeTransactions = transactions?.filter(t => t.status === 'active').length || 0;

        const now = new Date();
        overdueBooks = transactions?.filter(t =>
          t.status === 'active' && new Date(t.due_date) < now
        ).length || 0;
      } else {
        const { data: transactions } = await supabase
          .from('transactions')
          .select('*, books(*)')
          .eq('user_id', profile?.id)
          .order('created_at', { ascending: false })
          .limit(10);

        setRecentTransactions(transactions || []);
        activeTransactions = transactions?.filter(t => t.status === 'active').length || 0;
      }

      setStats({
        totalBooks,
        availableBooks,
        borrowedBooks,
        totalUsers,
        activeTransactions,
        overdueBooks,
      });
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading">Loading dashboard...</div>;
  }

  return (
    <div className="container">
      <h1 style={{ color: 'white', marginBottom: '30px' }}>
        Welcome, {profile?.full_name}!
      </h1>

      <div className="stats-grid">
        <div className="stat-card">
          <h3>Total Books</h3>
          <div className="value">{stats.totalBooks}</div>
        </div>
        <div className="stat-card">
          <h3>Available</h3>
          <div className="value" style={{ color: '#4caf50' }}>{stats.availableBooks}</div>
        </div>
        <div className="stat-card">
          <h3>Borrowed</h3>
          <div className="value" style={{ color: '#ff9800' }}>{stats.borrowedBooks}</div>
        </div>
        {profile?.role === 'librarian' && (
          <>
            <div className="stat-card">
              <h3>Total Users</h3>
              <div className="value">{stats.totalUsers}</div>
            </div>
            <div className="stat-card">
              <h3>Overdue Books</h3>
              <div className="value" style={{ color: '#f44336' }}>{stats.overdueBooks}</div>
            </div>
          </>
        )}
        <div className="stat-card">
          <h3>Active Transactions</h3>
          <div className="value">{stats.activeTransactions}</div>
        </div>
      </div>

      <div className="card">
        <h2>Recent Transactions</h2>
        {recentTransactions.length === 0 ? (
          <p style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
            No transactions found
          </p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Book</th>
                {profile?.role === 'librarian' && <th>User</th>}
                <th>Type</th>
                <th>Date</th>
                <th>Due Date</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {recentTransactions.map((transaction) => (
                <tr key={transaction.id}>
                  <td>{transaction.books?.title || 'Unknown'}</td>
                  {profile?.role === 'librarian' && (
                    <td>{transaction.users?.full_name || 'Unknown'}</td>
                  )}
                  <td>
                    <span className={`badge badge-${transaction.transaction_type === 'borrow' ? 'info' : 'success'}`}>
                      {transaction.transaction_type}
                    </span>
                  </td>
                  <td>{new Date(transaction.borrow_date).toLocaleDateString()}</td>
                  <td>{new Date(transaction.due_date).toLocaleDateString()}</td>
                  <td>
                    <span className={`badge badge-${
                      transaction.status === 'active' ? 'warning' :
                      transaction.status === 'completed' ? 'success' :
                      'danger'
                    }`}>
                      {transaction.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
