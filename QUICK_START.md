# Quick Start Guide

## 1. Run the Database Setup (5 minutes)

Open your Supabase project at https://supabase.com/dashboard

1. Click on "SQL Editor" in the left sidebar
2. Click "New Query"
3. Open `setup-database.sql` from this project
4. Copy ALL the content
5. Paste into Supabase SQL Editor
6. Click "Run" button

This creates all tables, sample books, and security policies.

## 2. Start the App (1 minute)

```bash
npm install  # If you haven't already
npm run dev
```

Open http://localhost:3000

## 3. Create Your First Account (2 minutes)

1. Click "Sign Up" on the login page
2. Enter:
   - Full Name: Your Name
   - Email: your@email.com
   - Password: (choose a password)
3. Click "Sign Up"

## 4. Make Yourself a Librarian (1 minute)

Go back to Supabase SQL Editor and run:

```sql
UPDATE users
SET role = 'librarian'
WHERE email = 'your@email.com';
```

Replace `your@email.com` with the email you used.

## 5. Login and Explore

1. Refresh the app
2. You now have full librarian access!

### What You Can Do Now:

**Dashboard**
- See library statistics
- View recent activity

**Books**
- Browse the 5 sample books
- Add new books manually
- Edit or delete books
- Search books

**OCR Scan**
- Get Gemini API key: https://makersuite.google.com/app/apikey
- Upload image of book spines
- Auto-detect books with AI
- Add detected books to library

**Transactions**
- Create borrow transactions
- Mark books as returned
- Track due dates

**Users**
- View all members
- Change roles
- Manage accounts

## Sample Books Included

The setup script adds these books automatically:
1. The Great Gatsby - Fiction (Shelf A1)
2. To Kill a Mockingbird - Fiction (Shelf A2)
3. 1984 - Fiction (Shelf A3)
4. Database System Concepts - Computer Science (Shelf B1)
5. Introduction to Algorithms - Computer Science (Shelf B2)

## Try These First Tasks

1. **Browse Books**: Go to Books page and see the sample books
2. **Add a Book**: Click "Add New Book" and create one
3. **Get Gemini Key**: Visit https://makersuite.google.com/app/apikey
4. **Test OCR**: Upload a book shelf image and scan it
5. **Create Transaction**: Borrow a book (you'll need to create another user first)

## Need More Help?

- Full setup details: See `SETUP_GUIDE.md`
- Gemini API help: See `GEMINI_API_INSTRUCTIONS.md`
- General info: See `README.md`

## Troubleshooting

**Can't see books?**
- Make sure you ran the SQL setup script completely
- Check Supabase Tables to verify data exists

**Permission errors?**
- Verify you updated your role to 'librarian'
- Check the users table in Supabase

**Build fails?**
- Run `npm install` again
- Delete `node_modules` and `package-lock.json`, then `npm install`

That's it! You're ready to manage your library.
