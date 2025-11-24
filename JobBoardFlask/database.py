"""
Database initialization for FastWork - Global freelance marketplace with payments, commissions, and withdrawal support.
"""

import sqlite3
from werkzeug.security import generate_password_hash

DATABASE = 'marketplace.db'

def get_db_connection():
    """Get database connection with Row factory and foreign key enforcement."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def init_db():
    """Initialize database with all tables for FastWork platform."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table - extended with new fields
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT UNIQUE,
            phone TEXT,
            role TEXT NOT NULL CHECK(role IN ('client', 'freelancer', 'both')),
            avatar_url TEXT,
            profile_picture TEXT,
            country TEXT,
            background_color TEXT DEFAULT 'white',
            balance DECIMAL(10,2) DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # User profiles - extended for freelancer account details
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            title TEXT,
            bio TEXT,
            skills TEXT,
            hourly_rate DECIMAL(10,2),
            location TEXT,
            portfolio_url TEXT,
            bank_account_holder TEXT,
            bank_account_number TEXT,
            bank_name TEXT,
            bank_code TEXT,
            withdrawal_method TEXT,
            wallet_address TEXT,
            total_earned DECIMAL(10,2) DEFAULT 0,
            total_jobs INTEGER DEFAULT 0,
            rating DECIMAL(3,2) DEFAULT 0,
            reviews_count INTEGER DEFAULT 0,
            commission_paid DECIMAL(10,2) DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # Payment methods table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('credit_card', 'paypal', 'bank_transfer', 'wallet')),
            card_number TEXT,
            card_holder TEXT,
            expiry TEXT,
            cvv TEXT,
            paypal_email TEXT,
            bank_account TEXT,
            is_default BOOLEAN DEFAULT 0,
            status TEXT DEFAULT 'verified',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # Categories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT
        )
    ''')
    
    # Insert categories
    default_categories = [
        ('Web Development', 'Website and web application development'),
        ('Mobile Development', 'iOS and Android app development'),
        ('Design', 'Graphic design, UI/UX, and visual design'),
        ('Writing', 'Content writing, copywriting, and editing'),
        ('Marketing', 'Digital marketing, SEO, and social media'),
        ('Data Entry', 'Data entry and administrative tasks'),
        ('Customer Service', 'Customer support and service'),
        ('Accounting', 'Bookkeeping and financial services')
    ]
    
    cursor.execute('SELECT COUNT(*) as count FROM categories')
    if cursor.fetchone()['count'] == 0:
        cursor.executemany('INSERT INTO categories (name, description) VALUES (?, ?)', default_categories)
    
    # Jobs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category_id INTEGER,
            budget DECIMAL(10,2),
            duration TEXT,
            experience_level TEXT,
            client_id INTEGER NOT NULL,
            status TEXT DEFAULT 'open' CHECK(status IN ('open', 'in_progress', 'completed', 'closed')),
            escrow_status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    ''')
    
    # Proposals table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            freelancer_id INTEGER NOT NULL,
            cover_letter TEXT NOT NULL,
            bid_amount DECIMAL(10,2) NOT NULL,
            delivery_time INTEGER,
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'accepted', 'rejected', 'withdrawn')),
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE,
            FOREIGN KEY (freelancer_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE(job_id, freelancer_id)
        )
    ''')
    
    # Contracts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            client_id INTEGER NOT NULL,
            freelancer_id INTEGER NOT NULL,
            proposal_id INTEGER,
            amount DECIMAL(10,2) NOT NULL,
            commission_amount DECIMAL(10,2) DEFAULT 0,
            status TEXT DEFAULT 'active' CHECK(status IN ('active', 'completed', 'cancelled', 'disputed')),
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE,
            FOREIGN KEY (client_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (freelancer_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (proposal_id) REFERENCES proposals (id)
        )
    ''')
    
    # Messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            subject TEXT,
            message TEXT NOT NULL,
            is_read BOOLEAN DEFAULT 0,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (receiver_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # Reviews table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER NOT NULL,
            reviewer_id INTEGER NOT NULL,
            reviewee_id INTEGER NOT NULL,
            rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts (id) ON DELETE CASCADE,
            FOREIGN KEY (reviewer_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (reviewee_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE(contract_id, reviewer_id)
        )
    ''')
    
    # Transactions table - extended for commissions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            contract_id INTEGER,
            amount DECIMAL(10,2) NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('deposit', 'withdrawal', 'payment', 'refund', 'fee', 'commission')),
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'completed', 'failed')),
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (contract_id) REFERENCES contracts (id)
        )
    ''')
    
    # Notifications table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT,
            is_read BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # Reports table - for user problem reports
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            category TEXT NOT NULL,
            subject TEXT NOT NULL,
            description TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            severity TEXT DEFAULT 'medium' CHECK(severity IN ('low', 'medium', 'high', 'critical')),
            status TEXT DEFAULT 'open' CHECK(status IN ('open', 'investigating', 'resolved', 'closed')),
            admin_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully for FastWork!")

if __name__ == '__main__':
    init_db()
