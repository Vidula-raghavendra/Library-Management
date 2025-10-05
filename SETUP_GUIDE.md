# Library Management System - Quick Setup Guide

## Step 1: Database Setup

Copy and run this SQL script in your Supabase SQL Editor to set up the database:

1. Open your Supabase project: https://supabase.com/dashboard
2. Go to SQL Editor (left sidebar)
3. Click "New Query"
4. Copy the entire contents of `setup-database.sql`
5. Paste and click "Run"

This will create:
- `books` table for book catalog
- `users` table for library members
- `transactions` table for borrowing records
- `ocr_scans` table for scan history
- All necessary indexes and security policies

## Step 2: Create Your First Librarian Account

### Option A: Using the App
1. Start the development server: `npm run dev`
2. Go to http://localhost:3000
3. Click "Sign Up"
4. Create an account with your email
5. Then run this SQL in Supabase to make yourself a librarian:

```sql
UPDATE users
SET role = 'librarian'
WHERE email = 'your-email@example.com';
```

### Option B: Using Supabase Auth Dashboard
1. Go to Authentication > Users in Supabase
2. Click "Add user"
3. Email: `librarian@library.com`
4. Password: `password123`
5. Click "Create user"
6. Copy the user ID
7. Run this SQL:

```sql
INSERT INTO users (id, email, full_name, role, membership_id)
VALUES (
  'paste-user-id-here',
  'librarian@library.com',
  'Library Admin',
  'librarian',
  'LIB001'
);
```

## Step 3: Get Gemini API Key

1. Visit https://makersuite.google.com/app/apikey
2. Sign in with Google account
3. Click "Create API Key"
4. Copy the key
5. You'll enter this key in the OCR Scan page when using the app

## Step 4: Run the Application

```bash
npm run dev
```

The app will open at http://localhost:3000

## Step 5: Test the Features

### Login
- Use the account you created above
- Email: librarian@library.com
- Password: password123

### Add Books Manually
1. Go to "Books" page
2. Click "Add New Book"
3. Fill in book details
4. Click "Add Book"

### Test OCR Scanning
1. Go to "OCR Scan" page
2. Enter your Gemini API key
3. Upload an image of book spines
4. Click "Scan Image"
5. Review detected books
6. Click "Add to Library" for any book

### Create a Transaction
1. Go to "Transactions" page
2. Click "New Transaction"
3. Select a book and user
4. Set due date
5. Click "Create Transaction"

### Manage Users
1. Go to "Users" page
2. View all registered users
3. Change roles or activate/deactivate accounts

## Common Issues

### "No books found"
- Make sure you ran the setup SQL script
- The script includes sample books

### "Permission denied"
- Check that RLS policies were created
- Verify user role in users table

### OCR not working
- Verify Gemini API key is valid
- Check image quality
- Ensure book spines are clearly visible

### Authentication fails
- Make sure email/password are correct
- Check that user exists in both auth.users AND users table

## Sample Test Data

The setup script includes these sample books:
- The Great Gatsby by F. Scott Fitzgerald
- To Kill a Mockingbird by Harper Lee
- 1984 by George Orwell
- Database System Concepts by Abraham Silberschatz
- Introduction to Algorithms by Thomas H. Cormen

## Next Steps

1. Create additional member accounts for testing
2. Try borrowing and returning books
3. Upload shelf images and test OCR
4. Customize the system to your needs

## Need Help?

Check these resources:
- Supabase Docs: https://supabase.com/docs
- Gemini API Docs: https://ai.google.dev/docs
- React Docs: https://react.dev

Enjoy your new Library Management System!
