import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'cloud9_spa_super_secret_key' # Change this to a random string in production!
DATABASE = 'cloud9_spa.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def get_membership_tier(points):
    """Calculates premium tier naming based on user's rebalanced point milestones."""
    if points >= 800: return "🌌 MAJESTIC MEMBER"
    if points >= 500: return "💎 DIAMOND MEMBER"
    if points >= 300: return "🥇 GOLD MEMBER"
    if points >= 150: return "🥈 SILVER MEMBER"
    return "🥉 BRONZE MEMBER"

def init_db():
    """Initializes schema and pre-seeds the ultra admin and spa service items."""
    if not os.path.exists(DATABASE):
        conn = get_db_connection()
        with app.open_resource('schema.sql', mode='r') as f:
            conn.cursor().executescript(f.read())
        
        # 1. Seed Ultra Admin Profile (Pre-unlocked)
        hashed_pw = generate_password_hash('cloud9master123')
        conn.execute('''
            INSERT INTO users (username, password_hash, full_name, role, is_active)
            VALUES (?, ?, ?, 'ultra_admin', 1)
        ''', ('ultra_admin_me', hashed_pw, 'System Architect'))
        
        # 2. Seed the Standard Cloud 9 Spa Menu
        services_to_seed = [
            ('Massage', 'Diamond Package', 45, 15.00, 12),
            ('Massage', 'Gold Package', 30, 10.00, 8),
            ('Mini Package', 'Quick Chill', 10, 3.00, 2),
            ('Add-On', 'Cucumber Face Mask', 5, 2.00, 1)
        ]
        conn.executemany('''
            INSERT INTO services (category, name, duration_minutes, base_price, points_granted)
            VALUES (?, ?, ?, ?, ?)
        ''', services_to_seed)
        
        conn.commit()
        conn.close()

init_db()

# --- AUTH DECORATORS ---
def login_required(role=None):
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please authenticate to access the terminal.', 'warning')
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                if session.get('role') == 'ultra_admin':
                    return f(*args, **kwargs) # Master key bypasses restrictions
                flash('Unauthorized operations tier.', 'danger')
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- CENTRAL ROUTING INTERFACES ---

@app.route('/')
def home():
    return render_template('base.html')

@app.route('/dashboard/redirect')
def dashboard_router():
    """Ensures users hitting global link land on their unique console viewport."""
    role = session.get('role')
    if role == 'ultra_admin': return redirect(url_for('ultra_dashboard'))
    if role == 'admin': return redirect(url_for('admin_dashboard'))
    if role == 'employee': return redirect(url_for('employee_dashboard'))
    return redirect(url_for('user_dashboard'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        password = request.form['password']
        full_name = request.form['full_name'].strip()
        
        conn = get_db_connection()
        try:
            # Approach B deployment architecture rule default logic:
            conn.execute('''
                INSERT INTO users (username, password_hash, full_name, role, is_active)
                VALUES (?, ?, ?, 'user', 0)
            ''', (username, generate_password_hash(password), full_name))
            conn.commit()
            flash('Registration submitted! Account locked until authorized by Ultra Admin.', 'info')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username is currently taken by another family member.', 'danger')
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
            if user['is_active'] == 0:
                flash('Access Denied. Account is locked pending Ultra Admin activation.', 'danger')
                return redirect(url_for('login'))
                
            session.update({
                'user_id': user['id'], 'username': user['username'],
                'role': user['role'], 'full_name': user['full_name']
            })
            return redirect(url_for('dashboard_router'))
        flash('Invalid verification credentials provided.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Successfully logged out of the spa network.', 'success')
    return redirect(url_for('login'))

# --- ULTRA ADMIN CORE ACTIONS ---

@app.route('/dashboard/ultra')
@login_required('ultra_admin')
def ultra_dashboard():
    conn = get_db_connection()
    # Pull all system users to populate the access control matrix
    users = conn.execute('SELECT * FROM users WHERE role != "ultra_admin"').fetchall()
    conn.close()
    return render_template('ultra_dash.html', users=users)

@app.route('/ultra/toggle-user/<int:user_id>')
@login_required('ultra_admin')
def ultra_toggle_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT is_active FROM users WHERE id = ?', (user_id,)).fetchone()
    if user:
        new_status = 1 if user['is_active'] == 0 else 0
        conn.execute('UPDATE users SET is_active = ? WHERE id = ?', (new_status, user_id))
        conn.commit()
        flash('Account lock state updated successfully.', 'success')
    conn.close()
    return redirect(url_for('ultra_dashboard'))

@app.route('/ultra/update-discount/<int:user_id>', methods=['POST'])
@login_required('ultra_admin')
def ultra_update_discount(user_id):
    discount = float(request.form.get('custom_discount', 0.00))
    conn = get_db_connection()
    conn.execute('UPDATE users SET custom_discount = ? WHERE id = ?', (discount, user_id))
    conn.commit()
    conn.close()
    flash('Custom account discount matrix modified.', 'success')
    return redirect(url_for('ultra_dashboard'))

@app.route('/system/create-account', methods=['POST'])
@login_required('ultra_admin')
def system_create_account():
    username = request.form['username'].strip().lower()
    password = request.form['password']
    full_name = request.form['full_name'].strip()
    role = request.form['role']
    
    conn = get_db_connection()
    try:
        # Ultra Admin created profiles bypass verification limits instantly
        conn.execute('''
            INSERT INTO users (username, password_hash, full_name, role, is_active)
            VALUES (?, ?, ?, ?, 1)
        ''', (username, generate_password_hash(password), full_name, role))
        conn.commit()
        flash(f'Pre-approved operational account generated for {full_name}.', 'success')
    except sqlite3.IntegrityError:
        flash('Username identifier collision occurred.', 'danger')
    finally:
        conn.close()
    return redirect(url_for('dashboard_router'))

# --- USER PORTAL METHODS ---

@app.route('/dashboard/user')
@login_required('user')
def user_dashboard():
    conn = get_db_connection()
    user_data = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    raw_services = conn.execute('SELECT * FROM services').fetchall()
    
    # Track existing appointments
    appointments = conn.execute('''
        SELECT a.*, s.name as service_name, u.full_name as worker_name 
        FROM appointments a
        JOIN services s ON a.service_id = s.id
        LEFT JOIN users u ON a.employee_id = u.id
        WHERE a.user_id = ? ORDER BY a.id DESC
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    
    # Dynamic discount math injection
    discount_pct = user_data['custom_discount']
    calculated_menu = []
    for s in raw_services:
        final_p = round(s['base_price'] * (1.0 - (discount_pct / 100.0)), 2)
        calculated_menu.append({
            'id': s['id'], 'name': s['name'], 'category': s['category'],
            'duration': s['duration_minutes'], 'pts': s['points_granted'], 'final_price': final_p
        })
        
    tier = get_membership_tier(user_data['current_points'])
    return render_template('user_dash.html', user=user_data, menu=calculated_menu, appointments=appointments, tier=tier)

@app.route('/appointments/request', methods=['POST'])
@login_required('user')
def request_appointment():
    service_id = int(request.form['service_id'])
    req_date = request.form['date']
    req_time = request.form['time']
    notes = request.form.get('notes', '')
    
    conn = get_db_connection()
    user = conn.execute('SELECT custom_discount FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    service = conn.execute('SELECT base_price FROM services WHERE id = ?', (service_id,)).fetchone()
    
    final_price = round(service['base_price'] * (1.0 - (user['custom_discount'] / 100.0)), 2)
    
    conn.execute('''
        INSERT INTO appointments (user_id, service_id, requested_date, requested_time, status, notes, final_price)
        VALUES (?, ?, ?, ?, 'Pending', ?, ?)
    ''', (session['user_id'], service_id, req_date, req_time, notes, final_price))
    conn.commit()
    conn.close()
    flash('Appointment requested! Awaiting manager confirmation schedule.', 'success')
    return redirect(url_for('user_dashboard'))

# --- ADMIN BASE LAYER (BROTHER OPERATIONS) ---

@app.route('/dashboard/admin')
@login_required('admin')
def admin_dashboard():
    conn = get_db_connection()
    pending = conn.execute('''
        SELECT a.*, u.full_name as client_name, s.name as service_name 
        FROM appointments a
        JOIN users u ON a.user_id = u.id
        JOIN services s ON a.service_id = s.id
        WHERE a.status = "Pending"
    ''').fetchall()
    
    completed = conn.execute('''
        SELECT a.*, u.full_name as client_name, s.name as service_name, w.full_name as worker_name
        FROM appointments a
        JOIN users u ON a.user_id = u.id
        JOIN services s ON a.service_id = s.id
        JOIN users w ON a.employee_id = w.id
        WHERE a.status = "Confirmed"
    ''').fetchall()
    
    employees = conn.execute('SELECT id, full_name FROM users WHERE role = "employee" AND is_active = 1').fetchall()
    conn.close()
    return render_template('admin_dash.html', pending=pending, completed=completed, employees=employees)

@app.route('/admin/approve-job/<int:app_id>', methods=['POST'])
@login_required('admin')
def admin_approve_job(app_id):
    worker_id = request.form.get('employee_id')
    if not worker_id:
        flash('You must assign a staff member to approve.', 'warning')
        return redirect(url_for('admin_dashboard'))
        
    conn = get_db_connection()
    conn.execute('UPDATE appointments SET employee_id = ?, status = "Confirmed" WHERE id = ?', (worker_id, app_id))
    conn.commit()
    conn.close()
    flash('Appointment approved and assigned to worker.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/payout-job/<int:app_id>', methods=['POST'])
@login_required('admin')
def admin_payout_job(app_id):
    payout_amount = float(request.form.get('payout_amount', 0.00))
    conn = get_db_connection()
    
    job = conn.execute('SELECT * FROM appointments WHERE id = ?', (app_id,)).fetchone()
    service = conn.execute('SELECT points_granted FROM services WHERE id = ?', (job['service_id'],)).fetchone()
    
    # 1. Update appointment status
    conn.execute('UPDATE appointments SET status = "Completed" WHERE id = ?', (app_id,))
    # 2. Add custom layout tracking balance to staff ledger row
    conn.execute('INSERT INTO employee_ledgers (employee_id, amount, description) VALUES (?, ?, ?)',
                 (job['employee_id'], payout_amount, f"Payout for appointment identity run #{app_id}"))
    # 3. Award customer account loyalty points
    conn.execute('UPDATE users SET current_points = current_points + ? WHERE id = ?', 
                 (service['points_granted'], job['user_id']))
                 
    conn.commit()
    conn.close()
    flash('Payout balance allocated and family reward points dispatched!', 'success')
    return redirect(url_for('admin_dashboard'))

# --- EMPLOYEE SYSTEM ENGINE ---

@app.route('/dashboard/employee')
@login_required('employee')
def employee_dashboard():
    conn = get_db_connection()
    # Calculate rolling cash balance
    ledger_sum = conn.execute('SELECT TOTAL(amount) as bal FROM employee_ledgers WHERE employee_id = ?', 
                               (session['user_id'],)).fetchone()
    balance = ledger_sum['bal'] if ledger_sum else 0.00
    
    agenda = conn.execute('''
        SELECT a.*, u.full_name as client_name, s.name as service_name
        FROM appointments a
        JOIN users u ON a.user_id = u.id
        JOIN services s ON a.service_id = s.id
        WHERE a.employee_id = ? AND a.status = "Confirmed"
    ''', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('employee_dash.html', balance=f"{balance:,.2f}", agenda=agenda)

if __name__ == '__main__':
    app.run(debug=True)