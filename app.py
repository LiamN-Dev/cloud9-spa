
import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'cloud9_spa_super_secret_key' # Change this to a random string later!
DATABASE = 'cloud9_spa.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database and seeds the master Ultra Admin account."""
    if not os.path.exists(DATABASE):
        conn = get_db_connection()
        with app.open_resource('schema.sql', mode='r') as f:
            conn.cursor().executescript(f.read())
        
        # Seed Ultra Admin (You)
        # Choose your master password here. It's pre-unlocked (is_active = 1)
        hashed_pw = generate_password_hash('cloud9master123')
        try:
            conn.execute('''
                INSERT INTO users (username, password_hash, full_name, role, is_active)
                VALUES (?, ?, ?, ?, ?)
            ''', ('ultra_admin_me', hashed_pw, 'System Architect', 'ultra_admin', 1))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        conn.close()

# Run database setup on startup
init_db()

# --- SECURITY DECORATORS ---
def login_required(role=None):
    """Decorator factory to protect routes based on login state and role tier."""
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'danger')
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                # Ultra Admin can bypass role restrictions to view or debug other panels
                if session.get('role') == 'ultra_admin':
                    return f(*args, **kwargs)
                flash('Unauthorized access tier.', 'danger')
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- ROUTES ---

@app.route('/')
def home():
    return render_template('base.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        password = request.form['password']
        full_name = request.form['full_name'].strip()
        
        if not username or not password or not full_name:
            flash('All fields are required.', 'warning')
            return redirect(url_for('register'))
            
        hashed_password = generate_password_hash(password)
        
        conn = get_db_connection()
        try:
            # Approach B: Public signups default to role='user' and is_active=0 (Locked)
            conn.execute('''
                INSERT INTO users (username, password_hash, full_name, role, is_active)
                VALUES (?, ?, ?, 'user', 0)
            ''', (username, hashed_password, full_name))
            conn.commit()
            flash('Account created successfully! It is currently LOCKED pending Ultra Admin activation.', 'info')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('That username is already taken. Try another!', 'danger')
        finally:
            conn.close()
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            # Check if Approach B activation has been granted by Ultra Admin
            if user['is_active'] == 0:
                flash('Your account is locked. Please wait for the Ultra Admin to activate it.', 'danger')
                return redirect(url_for('login'))
                
            # Log user into their session
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['full_name'] = user['full_name']
            
            # Route to their explicit dashboard dashboard
            if user['role'] == 'ultra_admin':
                return redirect(url_for('ultra_dashboard'))
            elif user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'employee':
                return redirect(url_for('employee_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have logged out.', 'success')
    return redirect(url_for('login'))

# --- DASHBOARD PLACEHOLDERS ---
@app.route('/dashboard/ultra')
@login_required('ultra_admin')
def ultra_dashboard():
    return "<h1>Ultra Admin Dashboard</h1><p>Welcome, master control layer.</p>"

@app.route('/dashboard/admin')
@login_required('admin')
def admin_dashboard():
    return "<h1>Admin Dashboard</h1><p>Welcome to Spa Operations Management.</p>"

@app.route('/dashboard/employee')
@login_required('employee')
def employee_dashboard():
    return "<h1>Employee Dashboard</h1><p>Your work list and earnings ledger ledger.</p>"

@app.route('/dashboard/user')
@login_required('user')
def user_dashboard():
    return "<h1>Family Portal</h1><p>Welcome to Cloud 9 Spa booking requests.</p>"

if __name__ == '__main__':
    app.run(debug=True)