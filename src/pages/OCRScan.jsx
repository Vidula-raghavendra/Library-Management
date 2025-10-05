import { useState } from 'react';
import { analyzeBookImage } from '../services/gemini';
import { supabase } from '../services/supabase';
import { useAuth } from '../hooks/useAuth';

export default function OCRScan() {
  const { profile } = useAuth();
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [geminiApiKey, setGeminiApiKey] = useState('');
  const [detectedBooks, setDetectedBooks] = useState([]);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState('');
  const [shelfLocation, setShelfLocation] = useState('');

  const handleImageSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedImage(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result);
      };
      reader.readAsDataURL(file);
      setDetectedBooks([]);
      setError('');
    }
  };

  const handleScan = async () => {
    if (!selectedImage) {
      setError('Please select an image first');
      return;
    }

    if (!geminiApiKey) {
      setError('Please enter your Gemini API key');
      return;
    }

    setScanning(true);
    setError('');

    try {
      const books = await analyzeBookImage(selectedImage, geminiApiKey);

      if (books.length === 0) {
        setError('No books detected in the image. Please try a clearer image.');
        setDetectedBooks([]);
        return;
      }

      setDetectedBooks(books);

      if (profile?.role === 'librarian') {
        await supabase.from('ocr_scans').insert([
          {
            image_url: imagePreview,
            detected_books: books,
            scanned_by: profile.id,
            shelf_location: shelfLocation,
            status: 'processed',
          },
        ]);
      }
    } catch (err) {
      setError(`Scanning error: ${err.message}`);
      console.error(err);
    } finally {
      setScanning(false);
    }
  };

  const addBookToLibrary = async (book) => {
    if (!confirm(`Add "${book.title}" to the library?`)) return;

    try {
      const { data: existingBook } = await supabase
        .from('books')
        .select('*')
        .ilike('title', book.title)
        .maybeSingle();

      if (existingBook) {
        const { error } = await supabase
          .from('books')
          .update({
            total_copies: existingBook.total_copies + 1,
            available_copies: existingBook.available_copies + 1,
          })
          .eq('id', existingBook.id);

        if (error) throw error;
        alert('Book copy added to existing entry!');
      } else {
        const { error } = await supabase.from('books').insert([
          {
            title: book.title,
            author: 'Unknown',
            shelf_location: shelfLocation || `R${book.row}C${book.col}`,
            total_copies: 1,
            available_copies: 1,
          },
        ]);

        if (error) throw error;
        alert('New book added to library!');
      }
    } catch (err) {
      console.error('Error adding book:', err);
      alert('Error adding book: ' + err.message);
    }
  };

  return (
    <div className="container">
      <div className="card">
        <h1>OCR Book Scanner</h1>
        <p style={{ color: '#666', marginBottom: '24px' }}>
          Upload an image of book spines to automatically detect and catalog books
        </p>

        <div className="input-group">
          <label>Gemini API Key *</label>
          <input
            type="password"
            value={geminiApiKey}
            onChange={(e) => setGeminiApiKey(e.target.value)}
            placeholder="Enter your Gemini API key"
          />
          <small style={{ color: '#666', fontSize: '14px' }}>
            Get your free API key from{' '}
            <a
              href="https://makersuite.google.com/app/apikey"
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: '#667eea' }}
            >
              Google AI Studio
            </a>
          </small>
        </div>

        <div className="input-group">
          <label>Shelf Location (optional)</label>
          <input
            type="text"
            value={shelfLocation}
            onChange={(e) => setShelfLocation(e.target.value)}
            placeholder="e.g., A1, Section B, Row 3"
          />
        </div>

        <div className="input-group">
          <label>Select Image</label>
          <input
            type="file"
            accept="image/*"
            onChange={handleImageSelect}
            style={{ padding: '8px' }}
          />
        </div>

        {imagePreview && (
          <div style={{ textAlign: 'center', marginBottom: '20px' }}>
            <img
              src={imagePreview}
              alt="Selected shelf"
              className="image-preview"
              style={{ maxHeight: '400px', border: '2px solid #e0e0e0' }}
            />
          </div>
        )}

        {error && <div className="error">{error}</div>}

        <button
          onClick={handleScan}
          className="btn btn-primary"
          disabled={scanning || !selectedImage || !geminiApiKey}
          style={{ width: '100%' }}
        >
          {scanning ? 'Scanning with AI...' : 'Scan Image'}
        </button>
      </div>

      {detectedBooks.length > 0 && (
        <div className="card">
          <h2>Detected Books ({detectedBooks.length})</h2>
          <table className="table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Row</th>
                <th>Column</th>
                <th>Position</th>
                {profile?.role === 'librarian' && <th>Action</th>}
              </tr>
            </thead>
            <tbody>
              {detectedBooks.map((book, index) => (
                <tr key={index}>
                  <td style={{ fontWeight: '600' }}>{book.title}</td>
                  <td>{book.row}</td>
                  <td>{book.col}</td>
                  <td>
                    <span className="badge badge-info">
                      R{book.row}C{book.col}
                    </span>
                  </td>
                  {profile?.role === 'librarian' && (
                    <td>
                      <button
                        onClick={() => addBookToLibrary(book)}
                        className="btn btn-success"
                        style={{ padding: '6px 12px', fontSize: '14px' }}
                      >
                        Add to Library
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>

          <div
            style={{
              marginTop: '20px',
              padding: '16px',
              background: '#f5f5f5',
              borderRadius: '8px',
            }}
          >
            <h3 style={{ marginBottom: '12px', fontSize: '16px' }}>Summary</h3>
            <p>
              <strong>Total books detected:</strong> {detectedBooks.length}
            </p>
            <p>
              <strong>Shelf location:</strong> {shelfLocation || 'Not specified'}
            </p>
          </div>
        </div>
      )}

      <div className="card" style={{ background: '#f9f9f9' }}>
        <h3>Tips for Best Results</h3>
        <ul style={{ paddingLeft: '20px', lineHeight: '1.8' }}>
          <li>Ensure book spines are clearly visible and well-lit</li>
          <li>Take photos straight-on to avoid distortion</li>
          <li>Avoid shadows and glare on the book spines</li>
          <li>Higher resolution images produce better results</li>
          <li>Make sure text on spines is readable</li>
        </ul>
      </div>
    </div>
  );
}
