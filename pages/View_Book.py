# Search bar for finding books
import streamlit as st
book_search = st.text_input("Search for a book")

if book_search:
    # Read the CSV and search
    books_df = pd.read_csv("books_positions.csv")
    search_results = books_df[books_df['Book Name'].str.contains(book_search, case=False)]
    if not search_results.empty:
        st.write("Search Results:")
        st.write(search_results)
    else:
        st.write("No books found with that name.")
