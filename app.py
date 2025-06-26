from datetime import datetime
from werkzeug.security import generate_password_hash
from collections import deque
from flask import Flask, jsonify, render_template, request, redirect, session, url_for,flash, get_flashed_messages, session
import pyodbc

from book import BookLinkedList, BookQueue
app = Flask(__name__)
app.secret_key = 'your_secret_key'

book_queue = BookQueue()
# Use a stack to track new user registrations (DSA logic)
registration_stack = deque()
@app.route('/')
def home():
    # If logged in, show home page
    if 'librarian_logged_in' in session or 'user_logged_in' in session:
        return render_template('index.html')
    else:
        return redirect(url_for('login'))

@app.before_request
def require_login():
    allowed_routes = [
        'login', 'signup', 'static', 'logout'  # add 'logout' so logged-in users can logout
    ]

    # If trying to access a route not in allowed_routes
    # AND user not logged in as librarian or user
    if request.endpoint not in allowed_routes:
        if 'librarian_logged_in' not in session and 'user_logged_in' not in session:
            return redirect(url_for('login'))



def get_db_connection():
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=DESKTOP-RAG9V1T\\SQLEXPRESS;'
        'DATABASE=LMS;'
        'Trusted_Connection=yes;'
    )
    return conn
# Global linked list instance
book_list = BookLinkedList()

def load_books_from_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, author, copies FROM books")
    rows = cursor.fetchall()
    conn.close()
    # Clear linked list
    book_list.head = None
    for row in rows:
        book_list.add_book(row[0], row[1], row[2], row[3])

@app.route('/books/add', methods=['GET', 'POST'])
def add_book():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        copies = int(request.form['copies'])

        # Insert into DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO books (title, author, copies) VALUES (?, ?, ?)",
            (title, author, copies)
        )
        conn.commit()
        conn.close()

        # Reload linked list from DB to sync
        load_books_from_db()

        flash('Book added successfully!', 'success')
        return redirect(url_for('add_book'))

    return render_template('add_book.html')

def load_books_from_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, author, copies FROM books")
    rows = cursor.fetchall()
    conn.close()
    book_list.head = None
    for row in rows:
        book_list.add_book(row[0], row[1], row[2], row[3])

@app.route('/books/update', methods=['GET', 'POST'])
def update_book():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM books")
    books = cursor.fetchall()
    conn.close()

    book = None
    selected_book_id = request.args.get('book_id')

    if selected_book_id:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, author, copies FROM books WHERE id = ?", (selected_book_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            book = {
                'id': row[0],
                'title': row[1],
                'author': row[2],
                'copies': row[3]
            }

    if request.method == 'POST':
        book_id = int(request.form['id'])
        title = request.form['title']
        author = request.form['author']
        copies = int(request.form['copies'])

        # Update DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE books SET title = ?, author = ?, copies = ? WHERE id = ?",
            (title, author, copies, book_id)
        )
        conn.commit()
        conn.close()

        # Update linked list in-memory structure
        updated = book_list.update_book(book_id, title=title, author=author, copies=copies)
        # If not found in linked list (unlikely), reload from DB to resync
        if not updated:
            load_books_from_db()

        flash(f'Book "{title}" updated successfully!', 'success')
        return redirect(url_for('update_book', book_id=book_id))

    return render_template('update_book.html', books=books, book=book)

@app.route('/books/delete', methods=['GET', 'POST'])
def delete_book():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM books")
    books = cursor.fetchall()
    conn.close()

    selected_book = None
    selected_book_id = request.args.get('book_id')

    if selected_book_id:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, author, copies FROM books WHERE id = ?", (selected_book_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            selected_book = {
                'id': row[0],
                'title': row[1],
                'author': row[2],
                'copies': row[3]
            }

    if request.method == 'POST':
        book_id = int(request.form['id'])

        # Delete from DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
        conn.close()

        # Delete from linked list DSA
        deleted = book_list.delete_book(book_id)
        if not deleted:
            # Reload linked list if inconsistent
            load_books_from_db()

        flash(f'Book with ID {book_id} deleted successfully!', 'success')
        return redirect(url_for('delete_book'))

    return render_template('delete_book.html', books=books, selected_book=selected_book)

@app.route('/books/view', methods=['GET', 'POST'])
def view_books():
    load_books_from_db()  # 👈 ensure linked list is up to date

    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip()
        if keyword:
            results = book_list.search_books(keyword)
        else:
            results = book_list.to_list()
    else:
        results = book_list.to_list()

    return render_template('view_books.html', books=results)



@app.route('/books/cart/add/<int:book_id>', methods=['POST'])
def add_to_cart(book_id):
    load_books_from_db()
    cart = session.get('cart', [])

    current = book_list.head
    while current:
        if current.book_id == book_id:
            if not any(item['id'] == book_id for item in cart):
                book = {
                    'id': current.book_id,
                    'title': current.title,
                    'author': current.author,
                    'copies': current.copies
                }
                cart.append(book)
                session['cart'] = cart
                session.modified = True
                return jsonify({
                    'success': True,
                    'message': f'"{current.title}" added to cart.',
                    'cart_count': len(cart)
                })
            else:
                return jsonify({
                    'success': False,
                    'message': f'"{current.title}" is already in cart.'
                })
        current = current.next

    return jsonify({
        'success': False,
        'message': 'Book not found.'
    })

@app.route('/books/cart/remove/<int:book_id>', methods=['POST'])
def remove_from_cart(book_id):
    cart = session.get('cart', [])
    removed_book = None
    
    for book in cart:
        if book['id'] == book_id:
            removed_book = book
            break
            
    if removed_book:
        cart = [book for book in cart if book['id'] != book_id]
        session['cart'] = cart
        session.modified = True
        return jsonify({
            'success': True,
            'message': f'"{removed_book["title"]}" removed from cart.',
            'cart_count': len(cart)
        })
    
    return jsonify({
        'success': False,
        'message': 'Book not found in cart.'
    })

@app.route('/sync-cart', methods=['POST'])
def sync_cart():
    client_cart = request.json.get('cart', [])
    server_cart = session.get('cart', [])
    
    # Merge carts (simple implementation)
    merged_cart = server_cart.copy()
    for item in client_cart:
        if not any(book['id'] == item['id'] for book in merged_cart):
            # You might want to fetch full book details from DB here
            merged_cart.append(item)
    
    session['cart'] = merged_cart
    session.modified = True
    return jsonify({'success': True})


@app.route('/books/cart/issue', methods=['GET', 'POST'])
def cart_issue_books():
    if 'user_logged_in' not in session:
        flash('Please log in to issue books.', 'warning')
        return redirect(url_for('login'))
    
    user_id = session.get('user_id')  # Use logged-in user's id
    
    if request.method == 'POST':
        issued = session.get('cart', [])
        
        if not issued:
            flash('No books in cart to issue.', 'error')
            return redirect(url_for('view_books'))
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check book availability
            for book in issued:
                cursor.execute("SELECT copies FROM books WHERE id = ?", (book['id'],))
                result = cursor.fetchone()
                if not result or result[0] < 1:
                    flash(f'Book "{book["title"]}" is not available.', 'error')
                    return redirect(url_for('cart_issue_books'))
            
            # Issue books with 10-day return period
            for book in issued:
                cursor.execute("""
                    INSERT INTO issued_books 
                    (book_id, title, author, issued_by, issue_date, return_date) 
                    VALUES (?, ?, ?, ?, GETDATE(), DATEADD(day, 10, GETDATE()))
                """,
                (book['id'], book['title'], book['author'], user_id)
                )
                
                # Decrement available copies
                cursor.execute(
                    "UPDATE books SET copies = copies - 1 WHERE id = ?",
                    (book['id'],)
                )
            
            conn.commit()
            flash(f'Successfully issued {len(issued)} book(s)! Return within 10 days.', 'success')
            session['cart'] = []
            session.modified = True
            return redirect(url_for('view_books'))
            
        except Exception as e:
            conn.rollback()
            flash(f'Error issuing books: {str(e)}', 'error')
            return redirect(url_for('cart_issue_books'))
        finally:
            conn.close()
    
    # GET request
    issued = session.get('cart', [])
    return render_template('cart_issue_books.html', issued_books=issued)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        if role == 'librarian':
            if username == 'admin' and password == 'admin':
                session.clear()
                session['librarian_logged_in'] = True
                return redirect(url_for('home'))
            else:
                flash('Invalid librarian credentials', 'danger')

        elif role == 'user':
            conn = get_db_connection()
            cursor = conn.cursor()

            # Query user table for matching username and password
            cursor.execute("SELECT id FROM Users WHERE username = ? AND password = ?", (username, password))
            user = cursor.fetchone()

            cursor.close()
            conn.close()

            if user:
                session.clear()
                session['user_logged_in'] = True
                session['user_id'] = user[0]
                return redirect(url_for('home'))
            else:
                flash('Invalid user credentials', 'danger')

    return render_template('login.html')




@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()  # Plain password
        email = request.form['email'].strip()
        phone = request.form['phone'].strip()

        # Validation
        if len(username) < 3 or len(password) < 6:
            flash("Username must be 3+ characters and password 6+ characters.", "danger")
            return redirect('/signup')

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if user already exists
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            flash("Username already exists.", "danger")
            conn.close()
            return redirect('/signup')

        # ⚠️ Storing password as plain text (for testing only)
        cursor.execute(
            "INSERT INTO users (username, password, email, phone) VALUES (?, ?, ?, ?)",
            (username, password, email, phone)
        )
        conn.commit()
        conn.close()

        flash("Signup successful. Please log in.", "success")
        return redirect('/login')

    return render_template('signup.html')


@app.route('/view_records')
def view_records():
    if 'librarian_logged_in' in session:
        # Librarian: show all issued books
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, book_id, title, author, issued_by, issue_date, return_date FROM issued_books")
        records = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('view_records.html', records=records, is_librarian=True)

    elif 'user_logged_in' in session:
        # User: show only their issued books
        user_id = session.get('user_id')
        conn = get_db_connection()
        cursor = conn.cursor()
        # Assuming issued_by column stores user_id or username, adapt accordingly
        cursor.execute("SELECT id, book_id, title, author, issued_by, issue_date, return_date FROM issued_books WHERE issued_by = ?", (user_id,))
        records = cursor.fetchall()

        # Count how many books issued
        cursor.execute("SELECT COUNT(*) FROM issued_books WHERE issued_by = ?", (user_id,))
        count = cursor.fetchone()[0]

        cursor.close()
        conn.close()
        return render_template('view_records.html', records=records, book_count=count, is_librarian=False)

    else:
        flash("You need to login first.", "warning")
        return redirect(url_for('login'))




if __name__ == '__main__':
    app.run(debug=True)
