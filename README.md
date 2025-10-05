# Library Book Management System with OCR

A complete library management system built with React, Vite, Supabase, and Google Gemini AI for OCR book scanning.

## Features

- **Book Management**: Add, edit, delete, and search books
- **OCR Scanning**: Scan book shelves using Gemini AI to automatically detect book titles
- **User Management**: Manage library members and librarians
- **Transaction Tracking**: Borrow, return, and track book transactions
- **Role-Based Access**: Different permissions for librarians and members
- **Dashboard**: Real-time statistics and recent activity
- **Authentication**: Secure email/password authentication with Supabase

## Technology Stack

- **Frontend**: React + Vite
- **Backend**: Supabase (PostgreSQL database, Authentication, RLS)
- **OCR**: Google Gemini 1.5 Flash API
- **Styling**: Custom CSS

## Setup Instructions

### 1. Database Setup

1. Go to your Supabase project dashboard
2. Navigate to the SQL Editor
3. Copy and paste the contents of `setup-database.sql`
4. Run the script to create all tables, indexes, and policies

### 2. Install Dependencies

```bash
npm install
```

### 3. Run Development Server

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

### 4. Get Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Use this key in the OCR Scan page

## Usage Guide

### For Librarians

1. **Dashboard**: View overall library statistics
2. **Books**: Add, edit, delete, search books
3. **OCR Scan**: Upload shelf images, detect books, add to library
4. **Transactions**: Create and manage borrowing transactions
5. **Users**: Manage members and roles

### For Members

1. **Dashboard**: View your borrowing statistics
2. **Books**: Browse and search available books
3. **OCR Scan**: Scan book shelves (view only)

## Build for Production

```bash
npm run build
```
