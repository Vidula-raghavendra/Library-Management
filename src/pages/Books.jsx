import { useState, useEffect } from 'react';
import { supabase } from '../services/supabase';
import { useAuth } from '../hooks/useAuth';

export default function Books() {
  const { profile } = useAuth();
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingBook, setEditingBook] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [formData, setFormData] = useState({
    title: '',
    author: '',
    isbn: '',
    category: '',
    shelf_location: '',
    total_copies: 1,
    available_copies: 1,
    description: '',
  });

  useEffect(() => {
    fetchBooks();
  }, []);

  const fetchBooks = async () => {
    try {
      const { data, error } = await supabase
        .from('books')
        .select('*')
        .order('title');

      if (error) throw error;
      setBooks(data || []);
    } catch (error) {
      console.error('Error fetching books:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      if (editingBook) {
        const { error } = await supabase
          .from('books')
          .update(formData)
          .eq('id', editingBook.id);

        if (error) throw error;
      } else {
        const { error } = await supabase
          .from('books')
          .insert([formData]);

        if (error) throw error;
      }

      setShowModal(false);
      setEditingBook(null);
      setFormData({
        title: '',
        author: '',
        isbn: '',
        category: '',
        shelf_location: '',
        total_copies: 1,
        available_copies: 1,
        description: '',
      });
      fetchBooks();
    } catch (error) {
      console.error('Error saving book:', error);
      alert('Error saving book: ' + error.message);
    }
  };

  const handleEdit = (book) => {
    setEditingBook(book);
    setFormData({
      title: book.title,
      author: book.author,
      isbn: book.isbn || '',
      category: book.category || '',
      shelf_location: book.shelf_location || '',
      total_copies: book.total_copies,
      available_copies: book.available_copies,
      description: book.description || '',
    });
    setShowModal(true);
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this book?')) return;

    try {
      const { error } = await supabase
        .from('books')
        .delete()
        .eq('id', id);

      if (error) throw error;
      fetchBooks();
    } catch (error) {
      console.error('Error deleting book:', error);
      alert('Error deleting book: ' + error.message);
    }
  };

  const filteredBooks = books.filter(book =>
    book.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    book.author.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (book.isbn && book.isbn.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  if (loading) {
    return <div className="loading">Loading books...</div>;
  }

  return (
    <div className="container">
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h1>Books Collection</h1>
          {profile?.role === 'librarian' && (
            <button
              onClick={() => {
                setEditingBook(null);
                setShowModal(true);
              }}
              className="btn btn-primary"
            >
              Add New Book
            </button>
          )}
        </div>

        <div className="input-group">
          <input
            type="text"
            placeholder="Search by title, author, or ISBN..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {filteredBooks.length === 0 ? (
          <p style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
            No books found
          </p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Author</th>
                <th>ISBN</th>
                <th>Category</th>
                <th>Shelf</th>
                <th>Available</th>
                <th>Total</th>
                {profile?.role === 'librarian' && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {filteredBooks.map((book) => (
                <tr key={book.id}>
                  <td>{book.title}</td>
                  <td>{book.author}</td>
                  <td>{book.isbn || '-'}</td>
                  <td>{book.category || '-'}</td>
                  <td>{book.shelf_location || '-'}</td>
                  <td>
                    <span className={`badge ${book.available_copies > 0 ? 'badge-success' : 'badge-danger'}`}>
                      {book.available_copies}
                    </span>
                  </td>
                  <td>{book.total_copies}</td>
                  {profile?.role === 'librarian' && (
                    <td>
                      <button
                        onClick={() => handleEdit(book)}
                        className="btn btn-secondary"
                        style={{ marginRight: '8px', padding: '6px 12px', fontSize: '14px' }}
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(book.id)}
                        className="btn btn-danger"
                        style={{ padding: '6px 12px', fontSize: '14px' }}
                      >
                        Delete
                      </button>
                    </td>
                  )}
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
              <h2>{editingBook ? 'Edit Book' : 'Add New Book'}</h2>
              <button onClick={() => setShowModal(false)} className="close-btn">&times;</button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="input-group">
                <label>Title *</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  required
                />
              </div>

              <div className="input-group">
                <label>Author *</label>
                <input
                  type="text"
                  value={formData.author}
                  onChange={(e) => setFormData({ ...formData, author: e.target.value })}
                  required
                />
              </div>

              <div className="input-group">
                <label>ISBN</label>
                <input
                  type="text"
                  value={formData.isbn}
                  onChange={(e) => setFormData({ ...formData, isbn: e.target.value })}
                />
              </div>

              <div className="input-group">
                <label>Category</label>
                <input
                  type="text"
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  placeholder="e.g., Fiction, Science, History"
                />
              </div>

              <div className="input-group">
                <label>Shelf Location</label>
                <input
                  type="text"
                  value={formData.shelf_location}
                  onChange={(e) => setFormData({ ...formData, shelf_location: e.target.value })}
                  placeholder="e.g., A1, B2, C3"
                />
              </div>

              <div className="input-group">
                <label>Total Copies</label>
                <input
                  type="number"
                  min="1"
                  value={formData.total_copies}
                  onChange={(e) => setFormData({ ...formData, total_copies: parseInt(e.target.value) })}
                  required
                />
              </div>

              <div className="input-group">
                <label>Available Copies</label>
                <input
                  type="number"
                  min="0"
                  max={formData.total_copies}
                  value={formData.available_copies}
                  onChange={(e) => setFormData({ ...formData, available_copies: parseInt(e.target.value) })}
                  required
                />
              </div>

              <div className="input-group">
                <label>Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows="3"
                />
              </div>

              <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
                <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>
                  {editingBook ? 'Update' : 'Add'} Book
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
