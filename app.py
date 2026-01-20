# app.py
from flask import Flask, render_template, request, send_file, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from fpdf import FPDF
from datetime import datetime, date
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Exactly 14 parking slots
PARKING_SLOTS = [f"SLOT-{i:02d}" for i in range(1, 15)]
YEARS = [str(year) for year in range(2020, 2031)]

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='operator')  # admin, operator
    created_at = db.Column(db.DateTime, default=datetime.now)

class ParkingBill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    vehicle_number = db.Column(db.String(20), nullable=False)
    vehicle_type = db.Column(db.String(20), nullable=False)
    slot_number = db.Column(db.String(20), nullable=False)
    month = db.Column(db.String(20), nullable=False)
    year = db.Column(db.String(4), nullable=False)
    payment_mode = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, default=1000.00)
    bill_date = db.Column(db.DateTime, default=datetime.now)
    generated_by = db.Column(db.String(80))
    is_paid = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<ParkingBill {self.customer_name}>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required!', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Create tables
with app.app_context():
    db.create_all()
    # Create default admin user if not exists
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            password=generate_password_hash('admin123'),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()

# Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    monthly_count = ParkingBill.query.filter(
        db.extract('month', ParkingBill.bill_date) == today.month,
        db.extract('year', ParkingBill.bill_date) == today.year
    ).count()
    
    total_bills = ParkingBill.query.count()
    recent_bills = ParkingBill.query.order_by(ParkingBill.bill_date.desc()).limit(5).all()
    
    # Get slots occupancy
    occupied_slots = db.session.query(
        ParkingBill.slot_number
    ).filter(
        ParkingBill.month == today.strftime("%B"),
        ParkingBill.year == str(today.year)
    ).distinct().count()
    
    available_slots = len(PARKING_SLOTS) - occupied_slots
    
    return render_template('dashboard.html',
                         monthly_count=monthly_count,
                         total_bills=total_bills,
                         recent_bills=recent_bills,
                         available_slots=available_slots,
                         total_slots=len(PARKING_SLOTS))

@app.route('/')
@login_required
def home():
    current_year = datetime.now().year
    return render_template('index.html', 
                         slots=PARKING_SLOTS, 
                         years=YEARS, 
                         current_year=current_year)

@app.route('/generate', methods=['POST'])
@login_required
def generate():
    try:
        # Get form data
        name = request.form['name']
        vehicle_no = request.form['vehicle_no'].upper()
        vehicle_type = request.form['vehicle_type']
        slot_number = request.form['slot_number']
        month = request.form['month']
        year = request.form['year']
        payment_mode = request.form['payment_mode']
        
        # Check if slot is already occupied for this month/year
        existing = ParkingBill.query.filter_by(
            slot_number=slot_number,
            month=month,
            year=year
        ).first()
        
        if existing:
            flash(f'Slot {slot_number} is already occupied for {month} {year}!', 'danger')
            return redirect(url_for('home'))
        
        # Save to database
        bill = ParkingBill(
            customer_name=name,
            vehicle_number=vehicle_no,
            vehicle_type=vehicle_type,
            slot_number=slot_number,
            month=month,
            year=year,
            payment_mode=payment_mode,
            generated_by=current_user.username
        )
        db.session.add(bill)
        db.session.commit()
        
        # Create PDF
        pdf = create_pdf(name, vehicle_no, vehicle_type, slot_number, month, year, payment_mode, bill.id)
        
        filename = f"Parking_Bill_{name.replace(' ', '_')}_{month}_{year}_{bill.id}.pdf"
        
        return send_file(pdf,
                        download_name=filename,
                        as_attachment=True,
                        mimetype='application/pdf')
        
    except Exception as e:
        flash(f'Error generating bill: {str(e)}', 'danger')
        return redirect(url_for('home'))

def create_pdf(name, vehicle_no, vehicle_type, slot_number, month, year, payment_mode, bill_id):
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", style="B", size=16)
    pdf.cell(200, 10, txt="VENGATESAN CAR PARKING", ln=1, align="C")
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 8, txt="Tittagudi | Contact: 9791365506", ln=1, align="C")
    pdf.ln(10)
    
    # Title
    pdf.set_font("Arial", style="B", size=18)
    pdf.cell(200, 15, txt="MONTHLY PARKING BILL", ln=1, align="C")
    pdf.ln(5)
    
    # Bill ID
    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(200, 8, txt=f"BILL ID: PB{bill_id:06d}", ln=1, align="C")
    pdf.ln(5)
    
    # Bill Details
    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(200, 10, txt="BILL DETAILS", ln=1)
    pdf.set_font("Arial", size=11)
    
    details = [
        ("Bill Date", datetime.now().strftime("%d-%m-%Y %H:%M")),
        ("Customer Name", name),
        ("Vehicle Number", vehicle_no),
        ("Vehicle Type", vehicle_type.upper()),
        ("Parking Slot", slot_number),
        ("Parking Period", f"{month} {year}"),
        ("Payment Mode", payment_mode),
        ("Generated By", current_user.username),
        ("Status", "PAID")
    ]
    
    for label, value in details:
        pdf.cell(60, 8, txt=label + ":", ln=0)
        pdf.cell(130, 8, txt=str(value), ln=1)
    
    pdf.ln(10)
    
    # Amount Section
    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(200, 10, txt="AMOUNT DETAILS", ln=1)
    pdf.set_font("Arial", size=11)
    
    pdf.cell(120, 10, txt="Monthly Parking Charges:", ln=0)
    pdf.cell(70, 10, txt=f"Rs. 1000.00", ln=1)
    
    pdf.ln(8)
    
    # Total Amount
    pdf.set_font("Arial", style="B", size=14)
    pdf.cell(120, 12, txt="TOTAL AMOUNT:", ln=0)
    pdf.cell(70, 12, txt=f"Rs. 1000.00", ln=1)
    
    pdf.ln(15)
    
    # Terms and Conditions
    pdf.set_font("Arial", style="B", size=10)
    pdf.cell(200, 8, txt="TERMS & CONDITIONS:", ln=1)
    pdf.set_font("Arial", size=8)
    terms = [
        "1. This bill is valid only for the specified month.",
        "2. Vehicle should not block other slots.",
        "3. Parking charges are non-refundable.",
        "4. Management is not responsible for any damage/theft.",
        "5. Renewal should be done before 5th of every month."
    ]
    
    for term in terms:
        pdf.cell(200, 5, txt=term, ln=1)
    
    pdf.ln(10)
    
    # Footer
    create_footer(pdf)
    
    # Save to BytesIO
    import io
    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    pdf_io = io.BytesIO(pdf_bytes)
    pdf_io.seek(0)
    
    return pdf_io

def create_footer(pdf):
    pdf.set_font("Arial", style="B", size=8)
    pdf.cell(200, 4, txt="-" * 50, ln=1, align="C")
    pdf.set_font("Arial", style="B", size=10)
    pdf.cell(200, 6, txt="CODE HIVE", ln=1, align="C")
    pdf.set_font("Arial", style="I", size=8)
    pdf.cell(200, 5, txt="LEARN AND LEAD", ln=1, align="C")
    pdf.set_font("Arial", style="B", size=8)
    pdf.cell(200, 4, txt="-" * 50, ln=1, align="C")
    pdf.ln(2)
    
    pdf.set_font("Arial", style="B", size=8)
    pdf.cell(200, 5, txt="Development Partner", ln=1, align="C")
    pdf.set_font("Arial", size=7)
    pdf.cell(200, 4, txt="Email: codehive143@gmail.com", ln=1, align="C")
    pdf.cell(200, 4, txt="Phone: +91 63745 76277", ln=1, align="C")
    pdf.cell(200, 4, txt="Web: www.codehive.dev", ln=1, align="C")
    pdf.ln(3)
    
    pdf.set_font("Arial", style="I", size=7)
    pdf.cell(200, 4, txt="Thank you for choosing Vengatesan Car Parking!", ln=1, align="C")
    pdf.cell(200, 4, txt="This is a computer-generated bill.", ln=1, align="C")

# Admin Routes
@app.route('/admin/bills')
@admin_required
def admin_bills():
    page = request.args.get('page', 1, type=int)
    bills = ParkingBill.query.order_by(ParkingBill.bill_date.desc()).paginate(page=page, per_page=20)
    return render_template('admin/bills.html', bills=bills)

@app.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/add_user', methods=['POST'])
@admin_required
def add_user():
    username = request.form['username']
    password = request.form['password']
    role = request.form['role']
    
    if User.query.filter_by(username=username).first():
        flash('Username already exists!', 'danger')
        return redirect(url_for('admin_users'))
    
    user = User(
        username=username,
        password=generate_password_hash(password),
        role=role
    )
    db.session.add(user)
    db.session.commit()
    
    flash('User added successfully!', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/delete_user/<int:id>')
@admin_required
def delete_user(id):
    if id == 1:
        flash('Cannot delete primary admin!', 'danger')
        return redirect(url_for('admin_users'))
    
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully!', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/reports')
@admin_required
def reports():
    # Monthly report
    bills = db.session.query(
        ParkingBill.month,
        ParkingBill.year,
        db.func.count(ParkingBill.id).label('count'),
        db.func.sum(ParkingBill.amount).label('total')
    ).group_by(ParkingBill.month, ParkingBill.year).all()
    
    # Vehicle type distribution
    vehicle_stats = db.session.query(
        ParkingBill.vehicle_type,
        db.func.count(ParkingBill.id).label('count')
    ).group_by(ParkingBill.vehicle_type).all()
    
    return render_template('admin/reports.html', 
                         monthly_reports=bills,
                         vehicle_stats=vehicle_stats)

@app.route('/search', methods=['GET'])
@login_required
def search():
    query = request.args.get('q', '')
    if query:
        bills = ParkingBill.query.filter(
            (ParkingBill.customer_name.contains(query)) |
            (ParkingBill.vehicle_number.contains(query)) |
            (ParkingBill.slot_number.contains(query))
        ).order_by(ParkingBill.bill_date.desc()).limit(50).all()
    else:
        bills = []
    
    return render_template('search.html', bills=bills, query=query)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
