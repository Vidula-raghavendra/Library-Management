-- Library Management System Database Setup
-- Run this script in your Supabase SQL editor

-- Create books table
CREATE TABLE IF NOT EXISTS books (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text NOT NULL,
  author text NOT NULL,
  isbn text UNIQUE,
  category text DEFAULT '',
  shelf_location text DEFAULT '',
  total_copies integer DEFAULT 1,
  available_copies integer DEFAULT 1,
  cover_image_url text DEFAULT '',
  description text DEFAULT '',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create users table
CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email text NOT NULL,
  full_name text NOT NULL,
  role text DEFAULT 'member' CHECK (role IN ('librarian', 'member')),
  membership_id text UNIQUE NOT NULL,
  phone text DEFAULT '',
  address text DEFAULT '',
  created_at timestamptz DEFAULT now(),
  is_active boolean DEFAULT true
);

-- Create transactions table
CREATE TABLE IF NOT EXISTS transactions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  book_id uuid NOT NULL REFERENCES books(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  transaction_type text NOT NULL CHECK (transaction_type IN ('borrow', 'return', 'reserve')),
  borrow_date timestamptz DEFAULT now(),
  due_date timestamptz NOT NULL,
  return_date timestamptz,
  status text DEFAULT 'active' CHECK (status IN ('active', 'completed', 'overdue')),
  fine_amount numeric DEFAULT 0,
  notes text DEFAULT '',
  created_at timestamptz DEFAULT now()
);

-- Create ocr_scans table
CREATE TABLE IF NOT EXISTS ocr_scans (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  image_url text NOT NULL,
  detected_books jsonb DEFAULT '[]'::jsonb,
  scan_date timestamptz DEFAULT now(),
  scanned_by uuid REFERENCES users(id) ON DELETE SET NULL,
  shelf_location text DEFAULT '',
  status text DEFAULT 'pending' CHECK (status IN ('pending', 'processed', 'verified'))
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_books_title ON books(title);
CREATE INDEX IF NOT EXISTS idx_books_isbn ON books(isbn);
CREATE INDEX IF NOT EXISTS idx_books_shelf_location ON books(shelf_location);
CREATE INDEX IF NOT EXISTS idx_transactions_book_id ON transactions(book_id);
CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);
CREATE INDEX IF NOT EXISTS idx_ocr_scans_shelf_location ON ocr_scans(shelf_location);

-- Enable Row Level Security
ALTER TABLE books ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_scans ENABLE ROW LEVEL SECURITY;

-- RLS Policies for books table
DROP POLICY IF EXISTS "Anyone can view books" ON books;
CREATE POLICY "Anyone can view books" ON books FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "Librarians can insert books" ON books;
CREATE POLICY "Librarians can insert books" ON books FOR INSERT TO authenticated
WITH CHECK (
  EXISTS (
    SELECT 1 FROM users WHERE users.id = auth.uid() AND users.role = 'librarian' AND users.is_active = true
  )
);

DROP POLICY IF EXISTS "Librarians can update books" ON books;
CREATE POLICY "Librarians can update books" ON books FOR UPDATE TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM users WHERE users.id = auth.uid() AND users.role = 'librarian' AND users.is_active = true
  )
)
WITH CHECK (
  EXISTS (
    SELECT 1 FROM users WHERE users.id = auth.uid() AND users.role = 'librarian' AND users.is_active = true
  )
);

DROP POLICY IF EXISTS "Librarians can delete books" ON books;
CREATE POLICY "Librarians can delete books" ON books FOR DELETE TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM users WHERE users.id = auth.uid() AND users.role = 'librarian' AND users.is_active = true
  )
);

-- RLS Policies for users table
DROP POLICY IF EXISTS "Users can view own profile" ON users;
CREATE POLICY "Users can view own profile" ON users FOR SELECT TO authenticated USING (auth.uid() = id);

DROP POLICY IF EXISTS "Librarians can view all users" ON users;
CREATE POLICY "Librarians can view all users" ON users FOR SELECT TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM users u WHERE u.id = auth.uid() AND u.role = 'librarian' AND u.is_active = true
  )
);

DROP POLICY IF EXISTS "Users can update own profile" ON users;
CREATE POLICY "Users can update own profile" ON users FOR UPDATE TO authenticated
USING (auth.uid() = id)
WITH CHECK (auth.uid() = id AND role = (SELECT role FROM users WHERE id = auth.uid()));

DROP POLICY IF EXISTS "Librarians can update any user" ON users;
CREATE POLICY "Librarians can update any user" ON users FOR UPDATE TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM users u WHERE u.id = auth.uid() AND u.role = 'librarian' AND u.is_active = true
  )
)
WITH CHECK (
  EXISTS (
    SELECT 1 FROM users u WHERE u.id = auth.uid() AND u.role = 'librarian' AND u.is_active = true
  )
);

DROP POLICY IF EXISTS "New users can insert own profile" ON users;
CREATE POLICY "New users can insert own profile" ON users FOR INSERT TO authenticated
WITH CHECK (auth.uid() = id);

-- RLS Policies for transactions table
DROP POLICY IF EXISTS "Users can view own transactions" ON transactions;
CREATE POLICY "Users can view own transactions" ON transactions FOR SELECT TO authenticated
USING (user_id = auth.uid());

DROP POLICY IF EXISTS "Librarians can view all transactions" ON transactions;
CREATE POLICY "Librarians can view all transactions" ON transactions FOR SELECT TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM users WHERE users.id = auth.uid() AND users.role = 'librarian' AND users.is_active = true
  )
);

DROP POLICY IF EXISTS "Librarians can insert transactions" ON transactions;
CREATE POLICY "Librarians can insert transactions" ON transactions FOR INSERT TO authenticated
WITH CHECK (
  EXISTS (
    SELECT 1 FROM users WHERE users.id = auth.uid() AND users.role = 'librarian' AND users.is_active = true
  )
);

DROP POLICY IF EXISTS "Librarians can update transactions" ON transactions;
CREATE POLICY "Librarians can update transactions" ON transactions FOR UPDATE TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM users WHERE users.id = auth.uid() AND users.role = 'librarian' AND users.is_active = true
  )
)
WITH CHECK (
  EXISTS (
    SELECT 1 FROM users WHERE users.id = auth.uid() AND users.role = 'librarian' AND users.is_active = true
  )
);

-- RLS Policies for ocr_scans table
DROP POLICY IF EXISTS "Librarians can view all scans" ON ocr_scans;
CREATE POLICY "Librarians can view all scans" ON ocr_scans FOR SELECT TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM users WHERE users.id = auth.uid() AND users.role = 'librarian' AND users.is_active = true
  )
);

DROP POLICY IF EXISTS "Librarians can insert scans" ON ocr_scans;
CREATE POLICY "Librarians can insert scans" ON ocr_scans FOR INSERT TO authenticated
WITH CHECK (
  EXISTS (
    SELECT 1 FROM users WHERE users.id = auth.uid() AND users.role = 'librarian' AND users.is_active = true
  )
);

DROP POLICY IF EXISTS "Librarians can update scans" ON ocr_scans;
CREATE POLICY "Librarians can update scans" ON ocr_scans FOR UPDATE TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM users WHERE users.id = auth.uid() AND users.role = 'librarian' AND users.is_active = true
  )
)
WITH CHECK (
  EXISTS (
    SELECT 1 FROM users WHERE users.id = auth.uid() AND users.role = 'librarian' AND users.is_active = true
  )
);

-- Insert sample data
INSERT INTO books (title, author, isbn, category, shelf_location, total_copies, available_copies, description)
VALUES
  ('The Great Gatsby', 'F. Scott Fitzgerald', '9780743273565', 'Fiction', 'A1', 3, 3, 'A classic American novel'),
  ('To Kill a Mockingbird', 'Harper Lee', '9780061120084', 'Fiction', 'A2', 2, 2, 'A gripping tale of racial injustice'),
  ('1984', 'George Orwell', '9780451524935', 'Fiction', 'A3', 4, 4, 'A dystopian social science fiction novel'),
  ('Database System Concepts', 'Abraham Silberschatz', '9780078022159', 'Computer Science', 'B1', 2, 2, 'Comprehensive database systems textbook'),
  ('Introduction to Algorithms', 'Thomas H. Cormen', '9780262033848', 'Computer Science', 'B2', 3, 3, 'Comprehensive textbook on algorithms')
ON CONFLICT (isbn) DO NOTHING;
