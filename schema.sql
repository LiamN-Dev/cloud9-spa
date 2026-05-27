-- Table to store our 4 types of accounts
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL, -- 'ultra_admin', 'admin', 'employee', 'user'
    is_active INTEGER DEFAULT 0, -- 0 = Locked (Default for public sign-ups), 1 = Active/Unlocked
    current_points INTEGER DEFAULT 0,
    custom_discount REAL DEFAULT 0.00 -- E.g., 25.32 for favorite family members
);

-- Table to store the Cloud 9 Menu items
CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL, -- 'Massage', 'Mini Package', 'Add-On'
    name TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    base_price REAL NOT NULL,
    points_granted INTEGER NOT NULL
);

-- Table to track employee earnings and payouts
CREATE TABLE IF NOT EXISTS employee_ledgers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    amount REAL NOT NULL, -- Positive for earnings, negative for admin payouts
    description TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES users(id)
);

-- Table to manage appointments and their lifecycles
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL,
    requested_date TEXT NOT NULL,
    requested_time TEXT NOT NULL,
    employee_id INTEGER, -- Assigned by Admin or Ultra Admin
    status TEXT DEFAULT 'Pending', -- 'Pending', 'Confirmed', 'Completed', 'Cancelled'
    notes TEXT,
    final_price REAL NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (service_id) REFERENCES services(id),
    FOREIGN KEY (employee_id) REFERENCES users(id)
);