from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from database import init_db, get_db_connection
import os
from werkzeug.utils import secure_filename
import smtplib
# from email.mime.text import MimeText
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize database
init_db()

# Email configuration (for OTP)
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USER = 'your_email@gmail.com'
EMAIL_PASS = 'your_app_password'

def send_otp_email(email, otp):
    try:
        subject = "Apartment Hub - OTP Verification"
        body = f"Your OTP for Apartment Hub registration is: {otp}"
        
        msg = MimeText(body)
        msg['Subject'] = subject
        msg['From'] = EMAIL_USER
        msg['To'] = email
        
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

# Routes
@app.route('/')
def home():
    return render_template("home.html")

@app.route('/index')
def index():
    return redirect(url_for('user_login'))

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# Admin Routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        if email == 'admin@gmail.com' and password == 'admin':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('admin/login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    
    # Get counts for dashboard
    total_users = conn.execute('SELECT COUNT(*) FROM users WHERE approved = 1').fetchone()[0]
    pending_users = conn.execute('SELECT COUNT(*) FROM users WHERE approved = 0').fetchone()[0]
    total_professions = conn.execute('SELECT COUNT(*) FROM professions WHERE approved = 1').fetchone()[0]
    pending_professions = conn.execute('SELECT COUNT(*) FROM professions WHERE approved = 0').fetchone()[0]
    total_products = conn.execute('SELECT COUNT(*) FROM products WHERE approved = 1').fetchone()[0]
    pending_products = conn.execute('SELECT COUNT(*) FROM products WHERE approved = 0').fetchone()[0]
    
    conn.close()
    
    return render_template('admin/dashboard.html', 
                         total_users=total_users, 
                         pending_users=pending_users,
                         total_professions=total_professions,
                         pending_professions=pending_professions,
                         total_products=total_products,
                         pending_products=pending_products)

@app.route('/admin/users')
def admin_users():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    users = conn.execute('''
        SELECT * FROM users 
        WHERE approved = 1 
        ORDER BY created_at DESC
    ''').fetchall()
    conn.close()
    
    return render_template('admin/users.html', users=users)

@app.route('/admin/pending-users')
def admin_pending_users():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    users = conn.execute('''
        SELECT * FROM users 
        WHERE approved = 0 
        ORDER BY created_at DESC
    ''').fetchall()
    conn.close()
    
    return render_template('admin/pending_users.html', users=users)

@app.route('/admin/approve-user/<int:user_id>')
def approve_user(user_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    conn.execute('UPDATE users SET approved = 1 WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    flash('User approved successfully', 'success')
    return redirect(url_for('admin_pending_users'))

@app.route('/admin/reject-user/<int:user_id>')
def reject_user(user_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    flash('User rejected and deleted', 'success')
    return redirect(url_for('admin_pending_users'))

@app.route('/admin/delete-user/<int:user_id>')
def delete_user(user_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    
    # Delete user's professions and products first
    conn.execute('DELETE FROM professions WHERE user_id = ?', (user_id,))
    conn.execute('DELETE FROM products WHERE user_id = ?', (user_id,))
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    
    conn.commit()
    conn.close()
    
    flash('User deleted successfully', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/professions')
def admin_professions():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    search = request.args.get('search', '')
    
    conn = get_db_connection()
    
    if search:
        professions = conn.execute('''
            SELECT p.*, u.username, u.email, u.contact_number, u.house_no 
            FROM professions p 
            JOIN users u ON p.user_id = u.id 
            WHERE p.approved = 1 AND p.role LIKE ?
            ORDER BY p.created_at DESC
        ''', (f'%{search}%',)).fetchall()
    else:
        professions = conn.execute('''
            SELECT p.*, u.username, u.email, u.contact_number, u.house_no 
            FROM professions p 
            JOIN users u ON p.user_id = u.id 
            WHERE p.approved = 1 
            ORDER BY p.created_at DESC
        ''').fetchall()
    
    conn.close()
    
    return render_template('admin/professions.html', professions=professions, search=search)

@app.route('/admin/pending-professions')
def admin_pending_professions():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    professions = conn.execute('''
        SELECT p.*, u.username, u.email, u.contact_number, u.house_no 
        FROM professions p 
        JOIN users u ON p.user_id = u.id 
        WHERE p.approved = 0 
        ORDER BY p.created_at DESC
    ''').fetchall()
    conn.close()
    
    return render_template('admin/pending_professions.html', professions=professions)

@app.route('/admin/approve-profession/<int:profession_id>')
def approve_profession(profession_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    conn.execute('UPDATE professions SET approved = 1 WHERE id = ?', (profession_id,))
    conn.commit()
    conn.close()
    
    flash('Profession approved successfully', 'success')
    return redirect(url_for('admin_pending_professions'))

@app.route('/admin/reject-profession/<int:profession_id>')
def reject_profession(profession_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    conn.execute('DELETE FROM professions WHERE id = ?', (profession_id,))
    conn.commit()
    conn.close()
    
    flash('Profession rejected and deleted', 'success')
    return redirect(url_for('admin_pending_professions'))

@app.route('/admin/delete-profession/<int:profession_id>')
def delete_profession(profession_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    conn.execute('DELETE FROM professions WHERE id = ?', (profession_id,))
    conn.commit()
    conn.close()
    
    flash('Profession deleted successfully', 'success')
    return redirect(url_for('admin_professions'))

@app.route('/admin/products')
def admin_products():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    search = request.args.get('search', '')
    
    conn = get_db_connection()
    
    if search:
        products = conn.execute('''
            SELECT p.*, u.username, u.email, u.contact_number, u.house_no 
            FROM products p 
            JOIN users u ON p.user_id = u.id 
            WHERE p.approved = 1 AND (p.name LIKE ? OR p.category LIKE ?)
            ORDER BY p.created_at DESC
        ''', (f'%{search}%', f'%{search}%')).fetchall()
    else:
        products = conn.execute('''
            SELECT p.*, u.username, u.email, u.contact_number, u.house_no 
            FROM products p 
            JOIN users u ON p.user_id = u.id 
            WHERE p.approved = 1 
            ORDER BY p.created_at DESC
        ''').fetchall()
    
    conn.close()
    
    return render_template('admin/products.html', products=products, search=search)

@app.route('/admin/pending-products')
def admin_pending_products():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    products = conn.execute('''
        SELECT p.*, u.username, u.email, u.contact_number, u.house_no 
        FROM products p 
        JOIN users u ON p.user_id = u.id 
        WHERE p.approved = 0 
        ORDER BY p.created_at DESC
    ''').fetchall()
    conn.close()
    
    return render_template('admin/pending_products.html', products=products)

@app.route('/admin/approve-product/<int:product_id>')
def approve_product(product_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    conn.execute('UPDATE products SET approved = 1 WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    
    flash('Product approved successfully', 'success')
    return redirect(url_for('admin_pending_products'))

@app.route('/admin/reject-product/<int:product_id>')
def reject_product(product_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    
    flash('Product rejected and deleted', 'success')
    return redirect(url_for('admin_pending_products'))

@app.route('/admin/delete-product/<int:product_id>')
def delete_product(product_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    
    flash('Product deleted successfully', 'success')
    return redirect(url_for('admin_products'))

from datetime import datetime

@app.route('/admin/events')
def admin_events():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    events_raw = conn.execute('SELECT * FROM events ORDER BY date DESC').fetchall()
    conn.close()

    # Convert each row to a dict and parse the date string into a datetime object
    events = []
    for row in events_raw:
        event = dict(row)
        try:
            event['date'] = datetime.strptime(event['date'], '%Y-%m-%d')  # Adjust if your DB format includes time
        except Exception as e:
            print(f"Error parsing date for event {event}: {e}")
            event['date'] = None  # or handle however you like
        events.append(event)

    return render_template('admin/events.html', events=events, now=datetime.now())


@app.route('/admin/add-event', methods=['POST'])
def add_event():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    name = request.form['name']
    date = request.form['date']
    description = request.form['description']
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO events (name, date, description) 
        VALUES (?, ?, ?)
    ''', (name, date, description))
    conn.commit()
    conn.close()
    
    flash('Event added successfully', 'success')
    return redirect(url_for('admin_events'))

@app.route('/admin/update-event/<int:event_id>', methods=['POST'])
def update_event(event_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    name = request.form['name']
    date = request.form['date']
    description = request.form['description']
    
    conn = get_db_connection()
    conn.execute('''
        UPDATE events SET name = ?, date = ?, description = ? 
        WHERE id = ?
    ''', (name, date, description, event_id))
    conn.commit()
    conn.close()
    
    flash('Event updated successfully', 'success')
    return redirect(url_for('admin_events'))

@app.route('/admin/delete-event/<int:event_id>')
def delete_event(event_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    conn.execute('DELETE FROM events WHERE id = ?', (event_id,))
    conn.commit()
    conn.close()
    
    flash('Event deleted successfully', 'success')
    return redirect(url_for('admin_events'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

# User Routes
@app.route('/user/register', methods=['GET', 'POST'])
def user_register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        contact_number = request.form['contact_number']
        house_no = request.form['house_no']
        
        # Handle profile photo upload
        profile_photo = None
        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                profile_photo = f"profiles/{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], profile_photo))
        
        # Generate OTP
        otp = str(random.randint(100000, 999999))
        print("OTP" ,otp)
        
        conn = get_db_connection()
        
        # Check if email already exists
        existing_user = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if existing_user:
            flash('Email already registered', 'error')
            return render_template('user/register.html')
        
        # Insert user with OTP
        conn.execute('''
            INSERT INTO users (username, email, password, contact_number, house_no, profile_photo, otp, approved) 
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        ''', (username, email, password, contact_number, house_no, profile_photo, otp))
        conn.commit()
        conn.close()
        return redirect(url_for('user_otp'))

        # Send OTP email
        # if send_otp_email(email, otp):
        #     session['register_email'] = email
        #     return redirect(url_for('user_otp'))
        # else:
        #     flash('Error sending OTP. Please try again.', 'error')
    
    return render_template('user/register.html')

@app.route('/user/otp', methods=['GET', 'POST'])
def user_otp():
    if 'register_email' not in session:
        return redirect(url_for('user_register'))
    
    if request.method == 'POST':
        otp = request.form['otp']
        
        conn = get_db_connection()
        user = conn.execute('SELECT otp FROM users WHERE email = ?', (session['register_email'],)).fetchone()
        
        if user and user['otp'] == otp:
            # OTP verified, mark user as pending approval
            conn.execute('UPDATE users SET otp_verified = 1 WHERE email = ?', (session['register_email'],))
            conn.commit()
            conn.close()
            
            session.pop('register_email', None)
            flash('Registration successful! Please wait for admin approval.', 'success')
            return redirect(url_for('user_login'))
        else:
            flash('Invalid OTP', 'error')
    
    return render_template('user/otp.html')

@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('''
            SELECT * FROM users 
            WHERE email = ? AND password = ? AND approved = 1
        ''', (email, password)).fetchone()
        conn.close()
        
        if user:
            session['user_logged_in'] = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid credentials or account not approved', 'error')
    
    return render_template('user/login.html')

@app.route('/user/dashboard')
def user_dashboard():
    if not session.get('user_logged_in'):
        return redirect(url_for('user_login'))
    
    user_id = session['user_id']
    
    conn = get_db_connection()
    
    # Get user info
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    
    # Get user's professions
    professions = conn.execute('SELECT * FROM professions WHERE user_id = ?', (user_id,)).fetchall()
    
    # Get user's products
    products = conn.execute('SELECT * FROM products WHERE user_id = ?', (user_id,)).fetchall()
    
    # Get pending purchases
    purchases = conn.execute('''
        SELECT p.*, pr.name as product_name, u.username as buyer_name 
        FROM purchases p 
        JOIN products pr ON p.product_id = pr.id 
        JOIN users u ON p.buyer_id = u.id 
        WHERE pr.user_id = ? AND p.verified = 0
    ''', (user_id,)).fetchall()
    
    conn.close()
    
    return render_template('user/dashboard.html', 
                         user=user, 
                         professions=professions, 
                         products=products,
                         purchases=purchases)

@app.route('/user/profile')
def user_profile():
    if not session.get('user_logged_in'):
        return redirect(url_for('user_login'))
    
    user_id = session['user_id']
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    
    return render_template('user/profile.html', user=user)

@app.route('/user/update-profile', methods=['POST'])
def update_profile():
    if not session.get('user_logged_in'):
        return redirect(url_for('user_login'))
    
    user_id = session['user_id']
    username = request.form['username']
    contact_number = request.form['contact_number']
    house_no = request.form['house_no']
    
    # Handle profile photo upload
    profile_photo = None
    if 'profile_photo' in request.files:
        file = request.files['profile_photo']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            profile_photo = f"profiles/{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], profile_photo))
    
    conn = get_db_connection()
    
    if profile_photo:
        conn.execute('''
            UPDATE users SET username = ?, contact_number = ?, house_no = ?, profile_photo = ? 
            WHERE id = ?
        ''', (username, contact_number, house_no, profile_photo, user_id))
    else:
        conn.execute('''
            UPDATE users SET username = ?, contact_number = ?, house_no = ? 
            WHERE id = ?
        ''', (username, contact_number, house_no, user_id))
    
    conn.commit()
    conn.close()
    
    session['username'] = username
    flash('Profile updated successfully', 'success')
    return redirect(url_for('user_profile'))

@app.route('/user/add-profession', methods=['GET', 'POST'])
def add_profession():
    if not session.get('user_logged_in'):
        return redirect(url_for('user_login'))
    
    user_id = session['user_id']
    
    if request.method == 'POST':
        role = request.form['role']
        description = request.form['description']
        
        conn = get_db_connection()
        
        # Check if user already has this profession
        existing = conn.execute('SELECT id FROM professions WHERE user_id = ? AND role = ?', (user_id, role)).fetchone()
        if existing:
            flash('You already have this profession listed', 'error')
            return redirect(url_for('add_profession'))
        
        conn.execute('''
            INSERT INTO professions (user_id, role, description, approved) 
            VALUES (?, ?, ?, 0)
        ''', (user_id, role, description))
        conn.commit()
        conn.close()
        
        flash('Profession added successfully! Waiting for admin approval.', 'success')
        return redirect(url_for('user_dashboard'))
    
    return render_template('user/add_profession.html')

@app.route('/user/add-product', methods=['GET', 'POST'])
def add_product():
    if not session.get('user_logged_in'):
        return redirect(url_for('user_login'))
    
    user_id = session['user_id']
    
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        price = request.form['price']
        quantity = request.form['quantity']
        description = request.form['description']
        
        # Handle product image upload
        product_image = None
        if 'product_image' in request.files:
            file = request.files['product_image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                product_image = f"products/{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], product_image))
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO products (user_id, name, category, price, quantity, description, image, approved) 
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        ''', (user_id, name, category, price, quantity, description, product_image))
        conn.commit()
        conn.close()
        
        flash('Product added successfully! Waiting for admin approval.', 'success')
        return redirect(url_for('user_dashboard'))
    
    return render_template('user/add_product.html')

@app.route('/user/marketplace')
def marketplace():
    if not session.get('user_logged_in'):
        return redirect(url_for('user_login'))
    
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    
    conn = get_db_connection()
    
    query = '''
        SELECT p.*, u.username, u.contact_number, u.house_no 
        FROM products p 
        JOIN users u ON p.user_id = u.id 
        WHERE p.approved = 1 AND p.quantity > 0
    '''
    params = []
    
    if search:
        query += ' AND (p.name LIKE ? OR p.description LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])
    
    if category:
        query += ' AND p.category = ?'
        params.append(category)
    
    query += ' ORDER BY p.created_at DESC'
    
    products = conn.execute(query, params).fetchall()
    
    # Get unique categories for filter
    categories = conn.execute('SELECT DISTINCT category FROM products WHERE approved = 1').fetchall()
    
    conn.close()
    
    return render_template('user/marketplace.html', products=products, categories=categories, search=search, category=category)

@app.route('/user/buy-product/<int:product_id>', methods=['POST'])
def buy_product(product_id):
    if not session.get('user_logged_in'):
        return redirect(url_for('user_login'))
    
    buyer_id = session['user_id']
    quantity = int(request.form['quantity'])
    
    conn = get_db_connection()
    
    # Check product availability
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    
    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('marketplace'))
    
    if quantity > product['quantity']:
        flash('Requested quantity not available', 'error')
        return redirect(url_for('marketplace'))
    
    # Create purchase record
    conn.execute('''
        INSERT INTO purchases (product_id, buyer_id, quantity, verified) 
        VALUES (?, ?, ?, 0)
    ''', (product_id, buyer_id, quantity))
    
    conn.commit()
    conn.close()
    
    flash('Purchase request submitted! Waiting for seller verification.', 'success')
    return redirect(url_for('marketplace'))

@app.route('/user/verify-purchase/<int:purchase_id>')
def verify_purchase(purchase_id):
    if not session.get('user_logged_in'):
        return redirect(url_for('user_login'))
    
    user_id = session['user_id']
    
    conn = get_db_connection()
    
    # Verify that the purchase belongs to the user's product
    purchase = conn.execute('''
        SELECT p.*, pr.user_id as seller_id, pr.quantity as available_quantity 
        FROM purchases p 
        JOIN products pr ON p.product_id = pr.id 
        WHERE p.id = ? AND pr.user_id = ?
    ''', (purchase_id, user_id)).fetchone()
    
    if not purchase:
        flash('Purchase not found or unauthorized', 'error')
        return redirect(url_for('user_dashboard'))
    
    if purchase['quantity'] > purchase['available_quantity']:
        flash('Insufficient quantity available', 'error')
        return redirect(url_for('user_dashboard'))
    
    # Update product quantity and mark purchase as verified
    new_quantity = purchase['available_quantity'] - purchase['quantity']
    
    conn.execute('UPDATE products SET quantity = ? WHERE id = ?', (new_quantity, purchase['product_id']))
    conn.execute('UPDATE purchases SET verified = 1 WHERE id = ?', (purchase_id,))
    
    # If quantity becomes 0, delete the product
    if new_quantity == 0:
        conn.execute('DELETE FROM products WHERE id = ?', (purchase['product_id'],))
    
    conn.commit()
    conn.close()
    
    flash('Purchase verified successfully', 'success')
    return redirect(url_for('user_dashboard'))

@app.route('/user/reject-purchase/<int:purchase_id>')
def reject_purchase(purchase_id):
    if not session.get('user_logged_in'):
        return redirect(url_for('user_login'))
    
    user_id = session['user_id']
    
    conn = get_db_connection()
    
    # Verify that the purchase belongs to the user's product
    purchase = conn.execute('''
        SELECT p.*, pr.user_id as seller_id 
        FROM purchases p 
        JOIN products pr ON p.product_id = pr.id 
        WHERE p.id = ? AND pr.user_id = ?
    ''', (purchase_id, user_id)).fetchone()
    
    if not purchase:
        flash('Purchase not found or unauthorized', 'error')
        return redirect(url_for('user_dashboard'))
    
    # Delete the purchase record
    conn.execute('DELETE FROM purchases WHERE id = ?', (purchase_id,))
    conn.commit()
    conn.close()
    
    flash('Purchase rejected', 'success')
    return redirect(url_for('user_dashboard'))

@app.route('/user/professionals')
def professionals():
    if not session.get('user_logged_in'):
        return redirect(url_for('user_login'))
    
    search = request.args.get('search', '')
    
    conn = get_db_connection()
    
    if search:
        professions = conn.execute('''
            SELECT p.*, u.username, u.email, u.contact_number, u.house_no, u.profile_photo 
            FROM professions p 
            JOIN users u ON p.user_id = u.id 
            WHERE p.approved = 1 AND p.role LIKE ?
            ORDER BY p.role
        ''', (f'%{search}%',)).fetchall()
    else:
        professions = conn.execute('''
            SELECT p.*, u.username, u.email, u.contact_number, u.house_no, u.profile_photo 
            FROM professions p 
            JOIN users u ON p.user_id = u.id 
            WHERE p.approved = 1 
            ORDER BY p.role
        ''').fetchall()
    
    conn.close()
    
    return render_template('user/professionals.html', professions=professions, search=search)

@app.route('/user/events')
def user_events():
    if not session.get('user_logged_in'):
        return redirect(url_for('user_login'))
    
    conn = get_db_connection()
    events_raw = conn.execute('SELECT * FROM events WHERE date >= date("now") ORDER BY date').fetchall()
    conn.close()

    # Convert each row to a dict and parse the date string into a datetime object
    events = []
    for row in events_raw:
        event = dict(row)
        try:
            event['date'] = datetime.strptime(event['date'], '%Y-%m-%d')  # Adjust if your DB format includes time
        except Exception as e:
            print(f"Error parsing date for event {event}: {e}")
            event['date'] = None  # or handle however you like
        events.append(event)
    
    return render_template('user/events.html', events=events, now=datetime.now())


@app.route('/user/add-event1', methods=['POST'])
def add_event1():
    if not session.get('user_logged_in'):
        return redirect(url_for('user_login'))
    
    name = request.form['name']
    date = request.form['date']
    description = request.form['description']
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO events (name, date, description) 
        VALUES (?, ?, ?)
    ''', (name, date, description))
    conn.commit()
    conn.close()
    
    flash('Event added successfully', 'success')
    return redirect(url_for('user_events'))




@app.route('/user/logout')
def user_logout():
    session.pop('user_logged_in', None)
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('user_login'))

if __name__ == '__main__':
    app.run(debug=True)