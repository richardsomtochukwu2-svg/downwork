"""
FastWork - Global Freelance Marketplace
A comprehensive platform with profiles, proposals, messaging, payments, reviews, and more.
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from database import get_db_connection, init_db
from datetime import datetime
import uuid

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize Flask app
app = Flask(__name__)

# Configuration for session management
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-secret-key-change-in-production')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
Session(app)

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize database on first run
init_db()

# Helper function to get unread message count
def get_unread_count(user_id):
    conn = get_db_connection()
    count = conn.execute('SELECT COUNT(*) as count FROM messages WHERE receiver_id = ? AND is_read = 0', (user_id,)).fetchone()['count']
    conn.close()
    return count

# Helper function to get unread notification count
def get_notification_count(user_id):
    conn = get_db_connection()
    count = conn.execute('SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0', (user_id,)).fetchone()['count']
    conn.close()
    return count

@app.route('/')
def index():
    """Home page with job categories and featured jobs"""
    conn = get_db_connection()
    categories = conn.execute('SELECT * FROM categories').fetchall()
    
    # Get recent jobs
    recent_jobs = conn.execute('''
        SELECT j.*, u.username as client_name, c.name as category_name,
               (SELECT COUNT(*) FROM proposals WHERE job_id = j.id) as proposal_count
        FROM jobs j
        LEFT JOIN users u ON j.client_id = u.id
        LEFT JOIN categories c ON j.category_id = c.id
        WHERE j.status = 'open'
        ORDER BY j.created_at DESC
        LIMIT 6
    ''').fetchall()
    conn.close()
    
    return render_template('index.html', categories=categories, recent_jobs=recent_jobs)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration with extended profile creation"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        role = request.form.get('role')
        country = request.form.get('country')
        skills = request.form.get('skills')
        withdrawal_method = request.form.get('withdrawal_method')
        
        if not username or not password or not role or not email or not country or not phone:
            flash('All fields are required!', 'error')
            return redirect(url_for('register'))
        
        if role not in ['client', 'freelancer']:
            flash('Invalid role selected!', 'error')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        profile_picture = None
        
        # Handle profile picture upload
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename and allowed_file(file.filename):
                filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                profile_picture = f"uploads/{filename}"
        
        conn = get_db_connection()
        try:
            # Create user account
            cursor = conn.execute(
                'INSERT INTO users (username, email, phone, password, role, country, profile_picture) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (username, email, phone, hashed_password, role, country, profile_picture)
            )
            user_id = cursor.lastrowid
            
            # Create user profile with new fields
            conn.execute(
                'INSERT INTO user_profiles (user_id, skills, withdrawal_method) VALUES (?, ?, ?)',
                (user_id, skills, withdrawal_method)
            )
            
            # Create welcome notification
            welcome_msg = f"Welcome to FastWork! 🎉 You're now registered as a {role}. "
            if role == 'freelancer':
                welcome_msg += "Browse jobs in any category, submit proposals with your bid amount and delivery time, and start earning! Your profile and ratings help you build credibility with clients worldwide. FastWork charges 10% commission on each completed project."
            else:
                welcome_msg += "Post jobs, review proposals from talented freelancers worldwide, hire the best fit for your project, and manage contracts. You can connect with professionals from any country!"
            
            conn.execute('''
                INSERT INTO notifications (user_id, title, message, type)
                VALUES (?, ?, ?, ?)
            ''', (user_id, 'Welcome to FastWork!', welcome_msg, 'info'))
            
            conn.commit()
            flash('Registration successful! Please complete your profile and login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Username or email already exists!', 'error')
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please enter both username and password!', 'error')
            return redirect(url_for('login'))
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, username)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash(f'Welcome back, {user["username"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """User settings - background color, payment methods, withdrawal"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'background_color':
            color = request.form.get('background_color')
            if color in ['white', 'black']:
                conn.execute('UPDATE users SET background_color = ? WHERE id = ?', (color, session['user_id']))
                conn.commit()
                flash(f'Background color changed to {color}!', 'success')
        
        elif action == 'payment_method':
            method_type = request.form.get('method_type')
            if method_type == 'credit_card':
                conn.execute('''
                    INSERT INTO payment_methods (user_id, type, card_number, card_holder, expiry, cvv, is_default)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                ''', (session['user_id'], 'credit_card', 
                      request.form.get('card_number'), 
                      request.form.get('card_holder'),
                      request.form.get('expiry'),
                      request.form.get('cvv')))
            elif method_type == 'paypal':
                conn.execute('''
                    INSERT INTO payment_methods (user_id, type, paypal_email, is_default)
                    VALUES (?, ?, ?, 1)
                ''', (session['user_id'], 'paypal', request.form.get('paypal_email')))
            elif method_type == 'bank_transfer':
                conn.execute('''
                    INSERT INTO payment_methods (user_id, type, bank_account, is_default)
                    VALUES (?, ?, ?, 1)
                ''', (session['user_id'], 'bank_transfer', request.form.get('bank_account')))
            
            conn.commit()
            flash('Payment method added successfully!', 'success')
        
        elif action == 'withdrawal':
            withdrawal_method = request.form.get('withdrawal_method')
            
            if not withdrawal_method:
                flash('Please select a withdrawal method!', 'error')
            else:
                wallet_address = ''
                bank_account_holder = ''
                bank_account_number = ''
                bank_name = ''
                bank_country = ''
                
                if withdrawal_method == 'paypal':
                    wallet_address = request.form.get('paypal_email', '')
                    if not wallet_address:
                        flash('Please enter your PayPal email!', 'error')
                        conn.close()
                        return redirect(url_for('settings'))
                elif withdrawal_method == 'crypto':
                    wallet_address = request.form.get('wallet_address', '')
                    if not wallet_address:
                        flash('Please enter your crypto wallet address!', 'error')
                        conn.close()
                        return redirect(url_for('settings'))
                elif withdrawal_method == 'bank_transfer':
                    bank_account_holder = request.form.get('bank_account_holder', '')
                    bank_account_number = request.form.get('bank_account_number', '')
                    bank_name = request.form.get('bank_name', '')
                    bank_country = request.form.get('bank_country', '')
                    
                    if not all([bank_account_holder, bank_account_number, bank_name, bank_country]):
                        flash('Please fill in all bank transfer details!', 'error')
                        conn.close()
                        return redirect(url_for('settings'))
                
                conn.execute('''
                    UPDATE user_profiles 
                    SET withdrawal_method = ?, wallet_address = ?, bank_account_holder = ?, bank_account_number = ?, bank_name = ?, bank_code = ?
                    WHERE user_id = ?
                ''', (withdrawal_method, wallet_address, bank_account_holder, bank_account_number, bank_name, bank_country, session['user_id']))
                conn.commit()
                flash('Withdrawal method updated successfully!', 'success')
    
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    profile = conn.execute('SELECT * FROM user_profiles WHERE user_id = ?', (session['user_id'],)).fetchone()
    payment_methods = conn.execute('SELECT * FROM payment_methods WHERE user_id = ?', (session['user_id'],)).fetchall()
    
    conn.close()
    return render_template('settings.html', user=user, profile=profile, payment_methods=payment_methods)

@app.route('/dashboard')
def dashboard():
    """Main dashboard redirect"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if session['role'] == 'client':
        return redirect(url_for('client_dashboard'))
    else:
        return redirect(url_for('freelancer_dashboard'))

@app.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    """Edit user profile"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    if request.method == 'POST':
        title = request.form.get('title')
        bio = request.form.get('bio')
        skills = request.form.get('skills')
        hourly_rate = request.form.get('hourly_rate')
        location = request.form.get('location')
        
        conn.execute('''
            UPDATE user_profiles 
            SET title = ?, bio = ?, skills = ?, hourly_rate = ?, location = ?
            WHERE user_id = ?
        ''', (title, bio, skills, hourly_rate, location, session['user_id']))
        conn.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('view_profile', user_id=session['user_id']))
    
    profile = conn.execute('SELECT * FROM user_profiles WHERE user_id = ?', (session['user_id'],)).fetchone()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    
    return render_template('edit_profile.html', profile=profile, user=user)

@app.route('/profile/<int:user_id>')
def view_profile(user_id):
    """View user profile"""
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    profile = conn.execute('SELECT * FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
    reviews = conn.execute('''
        SELECT r.*, u.username as reviewer_name
        FROM reviews r
        JOIN users u ON r.reviewer_id = u.id
        WHERE r.reviewee_id = ?
        ORDER BY r.created_at DESC
        LIMIT 10
    ''', (user_id,)).fetchall()
    conn.close()
    
    return render_template('view_profile.html', user=user, profile=profile, reviews=reviews)

# CLIENT ROUTES
@app.route('/client/dashboard')
def client_dashboard():
    """Client dashboard with posted jobs"""
    if 'user_id' not in session or session['role'] != 'client':
        flash('Access denied!', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    jobs = conn.execute('''
        SELECT j.*, c.name as category_name,
               (SELECT COUNT(*) FROM proposals WHERE job_id = j.id) as proposal_count
        FROM jobs j
        LEFT JOIN categories c ON j.category_id = c.id
        WHERE j.client_id = ?
        ORDER BY j.created_at DESC
    ''', (session['user_id'],)).fetchall()
    
    # Get active contracts
    contracts = conn.execute('''
        SELECT c.*, j.title as job_title, u.username as freelancer_name
        FROM contracts c
        JOIN jobs j ON c.job_id = j.id
        JOIN users u ON c.freelancer_id = u.id
        WHERE c.client_id = ? AND c.status = 'active'
    ''', (session['user_id'],)).fetchall()
    
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    
    return render_template('client_dashboard.html', jobs=jobs, contracts=contracts, balance=user['balance'])

@app.route('/client/post-job', methods=['GET', 'POST'])
def post_job():
    """Post a new job"""
    if 'user_id' not in session or session['role'] != 'client':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category_id = request.form.get('category_id')
        budget = request.form.get('budget')
        duration = request.form.get('duration')
        experience_level = request.form.get('experience_level')
        
        if not title or not description:
            flash('Title and description are required!', 'error')
            return redirect(url_for('post_job'))
        
        # Check if budget is specified
        if not budget:
            flash('Job budget is required!', 'error')
            return redirect(url_for('post_job'))
        
        try:
            budget_amount = float(budget)
            if budget_amount <= 0:
                flash('Budget must be greater than 0!', 'error')
                return redirect(url_for('post_job'))
            
            # Check if user has enough balance
            if user['balance'] < budget_amount:
                flash(f'Insufficient balance! You need ${budget_amount:.2f} but only have ${user["balance"]:.2f}. Please fund your wallet first.', 'error')
                conn.close()
                return redirect(url_for('fund_wallet'))
            
            # Check if user has set deposit method
            payment_method = conn.execute('SELECT * FROM payment_methods WHERE user_id = ?', (session['user_id'],)).fetchone()
            if not payment_method:
                conn.close()
                flash('Please set up a deposit method before posting a job!', 'info')
                return redirect(url_for('setup_payment'))
            
            # Deduct budget from balance and create job
            conn.execute('''
                INSERT INTO jobs (title, description, category_id, budget, duration, experience_level, client_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (title, description, category_id, budget, duration, experience_level, session['user_id']))
            
            conn.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (budget_amount, session['user_id']))
            conn.commit()
            conn.close()
            
            flash('Job posted successfully! Budget has been set aside in escrow.', 'success')
            return redirect(url_for('client_dashboard'))
        except ValueError:
            flash('Invalid budget amount!', 'error')
    
    categories = conn.execute('SELECT * FROM categories').fetchall()
    conn.close()
    
    return render_template('post_job.html', categories=categories, balance=user['balance'])

@app.route('/job/<int:job_id>')
def view_job(job_id):
    """View job details"""
    conn = get_db_connection()
    job = conn.execute('''
        SELECT j.*, u.username as client_name, c.name as category_name,
               (SELECT COUNT(*) FROM proposals WHERE job_id = j.id) as proposal_count
        FROM jobs j
        LEFT JOIN users u ON j.client_id = u.id
        LEFT JOIN categories c ON j.category_id = c.id
        WHERE j.id = ?
    ''', (job_id,)).fetchone()
    
    if not job:
        flash('Job not found!', 'error')
        conn.close()
        return redirect(url_for('index'))
    
    # Check if user has applied
    has_applied = False
    if 'user_id' in session:
        proposal = conn.execute('SELECT * FROM proposals WHERE job_id = ? AND freelancer_id = ?',
                               (job_id, session['user_id'])).fetchone()
        has_applied = proposal is not None
    
    # If client, get proposals
    proposals = []
    if 'user_id' in session and session['user_id'] == job['client_id']:
        proposals = conn.execute('''
            SELECT p.*, u.username as freelancer_name, up.rating, up.total_jobs, up.hourly_rate
            FROM proposals p
            JOIN users u ON p.freelancer_id = u.id
            LEFT JOIN user_profiles up ON u.id = up.user_id
            WHERE p.job_id = ?
            ORDER BY p.applied_at DESC
        ''', (job_id,)).fetchall()
    
    conn.close()
    
    return render_template('view_job.html', job=job, has_applied=has_applied, proposals=proposals)

# FREELANCER ROUTES
@app.route('/freelancer/dashboard')
def freelancer_dashboard():
    """Freelancer dashboard"""
    if 'user_id' not in session or session['role'] != 'freelancer':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    # Get active proposals
    proposals = conn.execute('''
        SELECT p.*, j.title as job_title, u.username as client_name
        FROM proposals p
        JOIN jobs j ON p.job_id = j.id
        JOIN users u ON j.client_id = u.id
        WHERE p.freelancer_id = ?
        ORDER BY p.applied_at DESC
    ''', (session['user_id'],)).fetchall()
    
    # Get active contracts
    contracts = conn.execute('''
        SELECT c.*, j.title as job_title, u.username as client_name
        FROM contracts c
        JOIN jobs j ON c.job_id = j.id
        JOIN users u ON c.client_id = u.id
        WHERE c.freelancer_id = ? AND c.status = 'active'
    ''', (session['user_id'],)).fetchall()
    
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    profile = conn.execute('SELECT * FROM user_profiles WHERE user_id = ?', (session['user_id'],)).fetchone()
    conn.close()
    
    if not user:
        return redirect(url_for('login'))
    
    return render_template('freelancer_dashboard.html', proposals=proposals, contracts=contracts, 
                         balance=user['balance'], profile=profile)

@app.route('/freelancer/browse-jobs')
def browse_jobs():
    """Browse available jobs with search and filters"""
    conn = get_db_connection()
    
    # Get search and filter parameters
    search = request.args.get('search', '')
    category_id = request.args.get('category', '')
    
    # Build query
    query = '''
        SELECT j.*, u.username as client_name, c.name as category_name,
               (SELECT COUNT(*) FROM proposals WHERE job_id = j.id) as proposal_count
        FROM jobs j
        LEFT JOIN users u ON j.client_id = u.id
        LEFT JOIN categories c ON j.category_id = c.id
        WHERE j.status = 'open'
    '''
    params = []
    
    if search:
        query += ' AND (j.title LIKE ? OR j.description LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])
    
    if category_id:
        query += ' AND j.category_id = ?'
        params.append(category_id)
    
    query += ' ORDER BY j.created_at DESC'
    
    jobs = conn.execute(query, params).fetchall()
    
    # Check which jobs user has applied to
    jobs_with_status = []
    for job in jobs:
        has_applied = False
        if 'user_id' in session:
            proposal = conn.execute('SELECT * FROM proposals WHERE job_id = ? AND freelancer_id = ?',
                                   (job['id'], session['user_id'])).fetchone()
            has_applied = proposal is not None
        jobs_with_status.append({'job': job, 'has_applied': has_applied})
    
    categories = conn.execute('SELECT * FROM categories').fetchall()
    conn.close()
    
    return render_template('browse_jobs.html', jobs=jobs_with_status, categories=categories,
                         search=search, selected_category=category_id)

@app.route('/freelancer/submit-proposal/<int:job_id>', methods=['GET', 'POST'])
def submit_proposal(job_id):
    """Submit proposal to a job"""
    if 'user_id' not in session or session['role'] != 'freelancer':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    job = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
    
    if not job:
        flash('Job not found!', 'error')
        conn.close()
        return redirect(url_for('browse_jobs'))
    
    if request.method == 'POST':
        cover_letter = request.form.get('cover_letter')
        bid_amount = request.form.get('bid_amount')
        delivery_time = request.form.get('delivery_time')
        
        if not cover_letter or not bid_amount:
            flash('Cover letter and bid amount are required!', 'error')
            return redirect(url_for('submit_proposal', job_id=job_id))
        
        try:
            conn.execute('''
                INSERT INTO proposals (job_id, freelancer_id, cover_letter, bid_amount, delivery_time)
                VALUES (?, ?, ?, ?, ?)
            ''', (job_id, session['user_id'], cover_letter, bid_amount, delivery_time))
            conn.commit()
            
            # Create notification for client
            conn.execute('''
                INSERT INTO notifications (user_id, title, message, type)
                VALUES (?, ?, ?, ?)
            ''', (job['client_id'], 'New Proposal', 
                  f'{session["username"]} submitted a proposal for "{job["title"]}"', 'proposal'))
            conn.commit()
            
            flash('Proposal submitted successfully!', 'success')
            return redirect(url_for('freelancer_dashboard'))
        except:
            flash('You have already submitted a proposal for this job!', 'error')
        finally:
            conn.close()
    
    profile = conn.execute('SELECT * FROM user_profiles WHERE user_id = ?', (session['user_id'],)).fetchone()
    conn.close()
    
    return render_template('submit_proposal.html', job=job, profile=profile)

@app.route('/client/accept-proposal/<int:proposal_id>', methods=['POST'])
def accept_proposal(proposal_id):
    """Accept a proposal and create contract"""
    if 'user_id' not in session or session['role'] != 'client':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    proposal = conn.execute('SELECT * FROM proposals WHERE id = ?', (proposal_id,)).fetchone()
    job = conn.execute('SELECT * FROM jobs WHERE id = ?', (proposal['job_id'],)).fetchone()
    
    if job['client_id'] != session['user_id']:
        flash('Access denied!', 'error')
        conn.close()
        return redirect(url_for('index'))
    
    # Create contract and calculate commission (10% FastWork fee)
    commission_amount = proposal['bid_amount'] * 0.10
    cursor = conn.execute('''
        INSERT INTO contracts (job_id, client_id, freelancer_id, proposal_id, amount, commission_amount)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (job['id'], session['user_id'], proposal['freelancer_id'], proposal_id, proposal['bid_amount'], commission_amount))
    contract_id = cursor.lastrowid
    
    # Create transaction for escrow (holds funds with client)
    total_amount = proposal['bid_amount'] + commission_amount
    conn.execute('''
        INSERT INTO transactions (user_id, contract_id, amount, type, status, description)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (session['user_id'], contract_id, total_amount, 'payment', 'pending', 
          f'Payment for {job["title"]} (held in escrow, includes 10% FastWork commission)'))
    
    # Update proposal status
    conn.execute('UPDATE proposals SET status = ? WHERE id = ?', ('accepted', proposal_id))
    
    # Update job status
    conn.execute('UPDATE jobs SET status = ? WHERE id = ?', ('in_progress', job['id']))
    
    # Create notification
    conn.execute('''
        INSERT INTO notifications (user_id, title, message, type)
        VALUES (?, ?, ?, ?)
    ''', (proposal['freelancer_id'], 'Proposal Accepted', 
          f'Your proposal for "{job["title"]}" has been accepted! Contract amount: ${proposal["bid_amount"]}', 'contract'))
    
    conn.commit()
    conn.close()
    
    flash('Proposal accepted! Contract created and payment held in escrow.', 'success')
    return redirect(url_for('view_job', job_id=job['id']))

# MESSAGING ROUTES
@app.route('/messages')
def messages():
    """View all messages"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Get conversations (unique users) - fixed query
    conversations = conn.execute('''
        SELECT DISTINCT 
            CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END as other_user_id,
            u.username as other_username,
            MAX(m.message) as last_message,
            MAX(m.sent_at) as last_message_time,
            SUM(CASE WHEN m.sender_id != ? AND m.receiver_id = ? AND m.is_read = 0 THEN 1 ELSE 0 END) as unread_count
        FROM messages m
        JOIN users u ON u.id = CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END
        WHERE sender_id = ? OR receiver_id = ?
        GROUP BY CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END
        ORDER BY last_message_time DESC
    ''', (session['user_id'], session['user_id'], session['user_id'], session['user_id'], 
          session['user_id'], session['user_id'], session['user_id'])).fetchall()
    
    conn.close()
    
    return render_template('messages.html', conversations=conversations)

@app.route('/messages/<int:other_user_id>')
def message_thread(other_user_id):
    """View message thread with specific user"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    other_user = conn.execute('SELECT * FROM users WHERE id = ?', (other_user_id,)).fetchone()
    
    # Get messages
    messages_list = conn.execute('''
        SELECT m.*, u.username as sender_name
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE (m.sender_id = ? AND m.receiver_id = ?)
           OR (m.sender_id = ? AND m.receiver_id = ?)
        ORDER BY m.sent_at ASC
    ''', (session['user_id'], other_user_id, other_user_id, session['user_id'])).fetchall()
    
    # Mark messages as read
    conn.execute('''
        UPDATE messages SET is_read = 1 
        WHERE receiver_id = ? AND sender_id = ?
    ''', (session['user_id'], other_user_id))
    conn.commit()
    conn.close()
    
    return render_template('message_thread.html', other_user=other_user, messages=messages_list)

@app.route('/messages/send/<int:receiver_id>', methods=['POST'])
def send_message(receiver_id):
    """Send a message"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    message = request.form.get('message')
    
    if not message:
        flash('Message cannot be empty!', 'error')
        return redirect(url_for('message_thread', other_user_id=receiver_id))
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO messages (sender_id, receiver_id, message)
        VALUES (?, ?, ?)
    ''', (session['user_id'], receiver_id, message))
    
    # Create notification
    conn.execute('''
        INSERT INTO notifications (user_id, title, message, type)
        VALUES (?, ?, ?, ?)
    ''', (receiver_id, 'New Message', f'{session["username"]} sent you a message', 'message'))
    
    conn.commit()
    conn.close()
    
    return redirect(url_for('message_thread', other_user_id=receiver_id))

# REVIEW ROUTES
@app.route('/contract/<int:contract_id>/review', methods=['GET', 'POST'])
def submit_review(contract_id):
    """Submit review for completed contract"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    contract = conn.execute('SELECT * FROM contracts WHERE id = ?', (contract_id,)).fetchone()
    
    if not contract or contract['status'] != 'completed':
        flash('Cannot review this contract!', 'error')
        conn.close()
        return redirect(url_for('dashboard'))
    
    # Determine reviewee
    if session['user_id'] == contract['client_id']:
        reviewee_id = contract['freelancer_id']
    elif session['user_id'] == contract['freelancer_id']:
        reviewee_id = contract['client_id']
    else:
        flash('Access denied!', 'error')
        conn.close()
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        rating = request.form.get('rating')
        comment = request.form.get('comment')
        
        if not rating:
            flash('Rating is required!', 'error')
            return redirect(url_for('submit_review', contract_id=contract_id))
        
        try:
            conn.execute('''
                INSERT INTO reviews (contract_id, reviewer_id, reviewee_id, rating, comment)
                VALUES (?, ?, ?, ?, ?)
            ''', (contract_id, session['user_id'], reviewee_id, rating, comment))
            
            # Update user profile rating
            conn.execute('''
                UPDATE user_profiles
                SET rating = (SELECT AVG(rating) FROM reviews WHERE reviewee_id = ?),
                    reviews_count = (SELECT COUNT(*) FROM reviews WHERE reviewee_id = ?)
                WHERE user_id = ?
            ''', (reviewee_id, reviewee_id, reviewee_id))
            
            conn.commit()
            flash('Review submitted successfully!', 'success')
            return redirect(url_for('dashboard'))
        except:
            flash('You have already reviewed this contract!', 'error')
        finally:
            conn.close()
    
    job = conn.execute('SELECT * FROM jobs WHERE id = ?', (contract['job_id'],)).fetchone()
    reviewee = conn.execute('SELECT * FROM users WHERE id = ?', (reviewee_id,)).fetchone()
    conn.close()
    
    return render_template('submit_review.html', contract=contract, job=job, reviewee=reviewee)

# WALLET / TRANSACTIONS
@app.route('/report-problem', methods=['GET', 'POST'])
def report_problem():
    """Report a problem with the platform"""
    if request.method == 'POST':
        category = request.form.get('category')
        subject = request.form.get('subject')
        description = request.form.get('description')
        email = request.form.get('email')
        phone = request.form.get('phone')
        severity = request.form.get('severity', 'medium')
        
        if not category or not subject or not description:
            flash('Please fill in all required fields!', 'error')
            return redirect(url_for('report_problem'))
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO reports (user_id, category, subject, description, email, phone, severity, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session.get('user_id'), category, subject, description, email, phone, severity, 'open'))
        conn.commit()
        conn.close()
        
        flash('Thank you! Your report has been submitted. Our support team will review it within 24 hours.', 'success')
        return redirect(url_for('dashboard') if 'user_id' in session else url_for('index'))
    
    user = None
    if 'user_id' in session:
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        conn.close()
    
    return render_template('report_problem.html', user=user)

@app.route('/fund-wallet', methods=['GET', 'POST'])
def fund_wallet():
    """Add funds to wallet"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    has_deposit_method = conn.execute('SELECT * FROM payment_methods WHERE user_id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        amount = request.form.get('amount')
        if not amount:
            flash('Please enter an amount!', 'error')
            return redirect(url_for('fund_wallet'))
        try:
            amount = float(amount)
            if amount <= 0:
                flash('Amount must be greater than 0!', 'error')
                return redirect(url_for('fund_wallet'))
            
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
            
            conn.execute('''
                INSERT INTO transactions (user_id, type, amount, status, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (session['user_id'], 'deposit', amount, 'pending', f'Deposit ${amount}'))
            
            conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (amount, session['user_id']))
            conn.commit()
            conn.close()
            
            flash(f'Successfully added ${amount} to your wallet!', 'success')
            return redirect(url_for('wallet'))
        except ValueError:
            flash('Invalid amount!', 'error')
    
    return render_template('fund_wallet.html', has_deposit_method=has_deposit_method)

@app.route('/setup-payment', methods=['GET', 'POST'])
def setup_payment():
    """Setup payment method, country, and theme before accessing wallet/withdrawal"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    profile = conn.execute('SELECT * FROM user_profiles WHERE user_id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'theme':
            theme = request.form.get('theme')
            if theme in ['white', 'black']:
                conn.execute('UPDATE users SET background_color = ? WHERE id = ?', (theme, session['user_id']))
                conn.commit()
                session['theme'] = theme
        
        elif action == 'country_payment':
            country = request.form.get('country')
            payment_method = request.form.get('payment_method')
            
            if country and payment_method:
                conn.execute('UPDATE users SET country = ? WHERE id = ?', (country, session['user_id']))
                
                method_type = request.form.get('method_type')
                if method_type == 'credit_card':
                    conn.execute('''
                        INSERT INTO payment_methods (user_id, type, card_number, card_holder, expiry, cvv, is_default)
                        VALUES (?, ?, ?, ?, ?, ?, 1)
                    ''', (session['user_id'], 'credit_card', 
                          request.form.get('card_number'), 
                          request.form.get('card_holder'),
                          request.form.get('expiry'),
                          request.form.get('cvv')))
                elif method_type == 'paypal':
                    conn.execute('''
                        INSERT INTO payment_methods (user_id, type, paypal_email, is_default)
                        VALUES (?, ?, ?, 1)
                    ''', (session['user_id'], 'paypal', request.form.get('paypal_email')))
                elif method_type == 'bank_transfer':
                    conn.execute('''
                        INSERT INTO payment_methods (user_id, type, bank_account, is_default)
                        VALUES (?, ?, ?, 1)
                    ''', (session['user_id'], 'bank_transfer', request.form.get('bank_account')))
                
                conn.commit()
                flash('Setup complete! Redirecting to wallet...', 'success')
                conn.close()
                return redirect(url_for('wallet'))
    
    conn.close()
    return render_template('setup_payment.html', user=user, profile=profile)

@app.route('/wallet')
def wallet():
    """View wallet and transactions"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    profile = conn.execute('SELECT * FROM user_profiles WHERE user_id = ?', (session['user_id'],)).fetchone()
    
    # Check payment methods based on role
    payment_methods = conn.execute('SELECT * FROM payment_methods WHERE user_id = ?', (session['user_id'],)).fetchall()
    has_deposit_method = len(payment_methods) > 0
    has_withdrawal_method = False
    if profile:
        has_withdrawal_method = profile['withdrawal_method'] is not None and profile['withdrawal_method'] != ''
    
    transactions = conn.execute('''
        SELECT * FROM transactions 
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 50
    ''', (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('wallet.html', balance=user['balance'], transactions=transactions, 
                         user_role=session.get('role'), has_deposit_method=has_deposit_method, 
                         has_withdrawal_method=has_withdrawal_method, payment_methods=payment_methods, 
                         profile=profile)

@app.route('/request-withdrawal', methods=['GET', 'POST'])
def request_withdrawal():
    """Request withdrawal of funds for freelancers"""
    if 'user_id' not in session or session['role'] != 'freelancer':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    profile = conn.execute('SELECT * FROM user_profiles WHERE user_id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        amount = request.form.get('amount')
        if not amount:
            flash('Please enter an amount!', 'error')
            return redirect(url_for('request_withdrawal'))
        
        try:
            amount = float(amount)
            if amount <= 0:
                flash('Amount must be greater than 0!', 'error')
                return redirect(url_for('request_withdrawal'))
            
            if user['balance'] < amount:
                flash(f'Insufficient balance! You have ${user["balance"]:.2f}', 'error')
                return redirect(url_for('request_withdrawal'))
            
            if not profile or not profile['withdrawal_method']:
                conn.close()
                flash('Please set up a withdrawal method first!', 'error')
                return redirect(url_for('settings'))
            
            # Deduct from balance and create withdrawal record
            conn.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (amount, session['user_id']))
            conn.execute('''
                INSERT INTO transactions (user_id, type, amount, status, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (session['user_id'], 'withdrawal', amount, 'pending', f'Withdrawal ${amount} to {profile["withdrawal_method"]}'))
            conn.commit()
            conn.close()
            
            flash(f'Withdrawal request submitted! ${amount:.2f} will be sent to your {profile["withdrawal_method"]} account within 2-3 business days.', 'success')
            return redirect(url_for('wallet'))
        except ValueError:
            flash('Invalid amount!', 'error')
    
    conn.close()
    return render_template('request_withdrawal.html', balance=user['balance'], profile=profile)

# NOTIFICATIONS
@app.route('/notifications')
def notifications():
    """View notifications"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    notifs = conn.execute('''
        SELECT * FROM notifications 
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 50
    ''', (session['user_id'],)).fetchall()
    
    # Mark as read
    conn.execute('UPDATE notifications SET is_read = 1 WHERE user_id = ?', (session['user_id'],))
    conn.commit()
    conn.close()
    
    return render_template('notifications.html', notifications=notifs)

# API endpoints for counts (for navigation badge)
@app.route('/api/counts')
def api_counts():
    """Get unread counts for badges"""
    if 'user_id' not in session:
        return jsonify({'messages': 0, 'notifications': 0})
    
    return jsonify({
        'messages': get_unread_count(session['user_id']),
        'notifications': get_notification_count(session['user_id'])
    })

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
