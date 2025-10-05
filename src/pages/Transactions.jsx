import { useState, useEffect } from 'react';
import { supabase } from '../services/supabase';

export default function Transactions() {
  const [transactions, setTransactions] = useState([]);
  const [books, setBooks] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    book_id: '',
    user_id: '',
    transaction_type: 'borrow',
    due_date: '',
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [transactionsRes, booksRes, usersRes] = await Promise.all([
        supabase.from('transactions').select('*, books(*), users(*)').order('created_at', { ascending: false }),
        supabase.from('books').select('*').order('title'),
        supabase.from('users').select('*').order('full_name'),
      ]);

      setTransactions(transactionsRes.data || []);
      setBooks(booksRes.data || []);
      setUsers(usersRes.data || []);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const { data: book } = await supabase
        .from('books')
        .select('available_copies')
        .eq('id', formData.book_id)
        .single();

      if (formData.transaction_type === 'borrow' && book.available_copies <= 0) {
        alert('This book is not available for borrowing');
        return;
      }

      const { error: transactionError } = await supabase.from('transactions').insert([
        {
          ...formData,
          status: 'active',
        },
      ]);

      if (transactionError) throw transactionError;

      if (formData.transaction_type === 'borrow') {
        const { error: updateError } = await supabase
          .from('books')
          .update({ available_copies: book.available_copies - 1 })
          .eq('id', formData.book_id);

        if (updateError) throw updateError;
      }

      setShowModal(false);
      setFormData({
        book_id: '',
        user_id: '',
        transaction_type: 'borrow',
        due_date: '',
      });
      fetchData();
    } catch (error) {
      console.error('Error creating transaction:', error);
      alert('Error creating transaction: ' + error.message);
    }
  };

  const handleReturn = async (transaction) => {
    if (!confirm('Mark this book as returned?')) return;

    try {
      const { error: transactionError } = await supabase
        .from('transactions')
        .update({
          status: 'completed',
          return_date: new Date().toISOString(),
        })
        .eq('id', transaction.id);

      if (transactionError) throw transactionError;

      const { data: book } = await supabase
        .from('books')
        .select('available_copies')
        .eq('id', transaction.book_id)
        .single();

      const { error: updateError } = await supabase
        .from('books')
        .update({ available_copies: book.available_copies + 1 })
        .eq('id', transaction.book_id);

      if (updateError) throw updateError;

      fetchData();
    } catch (error) {
      console.error('Error returning book:', error);
      alert('Error returning book: ' + error.message);
    }
  };

  if (loading) {
    return <div className="loading">Loading transactions...</div>;
  }

  return (
    <div className="container">
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h1>Transactions</h1>
          <button onClick={() => setShowModal(true)} className="btn btn-primary">
            New Transaction
          </button>
        </div>

        {transactions.length === 0 ? (
          <p style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
            No transactions found
          </p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Book</th>
                <th>User</th>
                <th>Type</th>
                <th>Borrow Date</th>
                <th>Due Date</th>
                <th>Return Date</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((transaction) => (
                <tr key={transaction.id}>
                  <td>{transaction.books?.title || 'Unknown'}</td>
                  <td>{transaction.users?.full_name || 'Unknown'}</td>
                  <td>
                    <span className={`badge badge-${transaction.transaction_type === 'borrow' ? 'info' : 'success'}`}>
                      {transaction.transaction_type}
                    </span>
                  </td>
                  <td>{new Date(transaction.borrow_date).toLocaleDateString()}</td>
                  <td>{new Date(transaction.due_date).toLocaleDateString()}</td>
                  <td>{transaction.return_date ? new Date(transaction.return_date).toLocaleDateString() : '-'}</td>
                  <td>
                    <span
                      className={`badge badge-${
                        transaction.status === 'active' ? 'warning' :
                        transaction.status === 'completed' ? 'success' : 'danger'
                      }`}
                    >
                      {transaction.status}
                    </span>
                  </td>
                  <td>
                    {transaction.status === 'active' && (
                      <button
                        onClick={() => handleReturn(transaction)}
                        className="btn btn-success"
                        style={{ padding: '6px 12px', fontSize: '14px' }}
                      >
                        Return
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>New Transaction</h2>
              <button onClick={() => setShowModal(false)} className="close-btn">
                &times;
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="input-group">
                <label>Book *</label>
                <select
                  value={formData.book_id}
                  onChange={(e) => setFormData({ ...formData, book_id: e.target.value })}
                  required
                >
                  <option value="">Select a book</option>
                  {books.map((book) => (
                    <option key={book.id} value={book.id}>
                      {book.title} (Available: {book.available_copies})
                    </option>
                  ))}
                </select>
              </div>

              <div className="input-group">
                <label>User *</label>
                <select
                  value={formData.user_id}
                  onChange={(e) => setFormData({ ...formData, user_id: e.target.value })}
                  required
                >
                  <option value="">Select a user</option>
                  {users.map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.full_name} ({user.membership_id})
                    </option>
                  ))}
                </select>
              </div>

              <div className="input-group">
                <label>Transaction Type *</label>
                <select
                  value={formData.transaction_type}
                  onChange={(e) => setFormData({ ...formData, transaction_type: e.target.value })}
                  required
                >
                  <option value="borrow">Borrow</option>
                  <option value="reserve">Reserve</option>
                </select>
              </div>

              <div className="input-group">
                <label>Due Date *</label>
                <input
                  type="date"
                  value={formData.due_date}
                  onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                  required
                  min={new Date().toISOString().split('T')[0]}
                />
              </div>

              <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
                <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>
                  Create Transaction
                </button>
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="btn btn-secondary"
                  style={{ flex: 1 }}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
