from flask import Flask, render_template_string, request, send_file
from fpdf import FPDF
from datetime import datetime
import io

app = Flask(__name__)

# Exactly 14 parking slots
PARKING_SLOTS = [f"SLOT-{i:02d}" for i in range(1, 15)]  # SLOT-01 to SLOT-14

# Year options
YEARS = [str(year) for year in range(2020, 2031)]  # 2020 to 2030

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Parking Bill Generator</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            max-width: 600px; 
            margin: 20px auto; 
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            position: relative;
        }
        .main-header {
            display: flex;
            align-items: center;
            margin-bottom: 20px;
            border-bottom: 2px solid #eee;
            padding-bottom: 15px;
        }
        .parking-logo {
            width: 80px;
            height: 80px;
            background: linear-gradient(135deg, #4CAF50, #45a049);
            border-radius: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 24px;
            margin-right: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        .header-text h2 {
            margin: 0;
            color: #333;
            font-size: 28px;
        }
        .header-text p {
            margin: 5px 0 0 0;
            color: #666;
            font-size: 14px;
        }
        .codehive-logo-section {
            background: linear-gradient(135deg, #1a2a3a, #2c3e50);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin: 25px 0;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        }
        .codehive-main {
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 10px;
            line-height: 1.2;
        }
        .codehive-code {
            color: #4ECDC4;
        }
        .codehive-hive {
            color: #FF6B6B;
        }
        .codehive-tagline {
            font-size: 14px;
            color: #bdc3c7;
            font-style: italic;
            letter-spacing: 1px;
        }
        .form-group { 
            margin: 20px 0; 
        }
        label { 
            display: block; 
            margin-bottom: 8px; 
            font-weight: bold;
            color: #333;
        }
        input, select { 
            width: 100%; 
            padding: 12px; 
            border: 2px solid #ddd; 
            border-radius: 8px;
            font-size: 16px;
        }
        input:focus, select:focus { 
            outline: none; 
            border-color: #667eea; 
        }
        button { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            padding: 15px; 
            border: none; 
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            width: 100%;
            cursor: pointer;
            margin-top: 10px;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        .business-info {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            text-align: center;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 15px;
            border-top: 1px solid #eee;
            color: #666;
            font-size: 12px;
        }
        .developer-info {
            background: #2c3e50;
            color: white;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
            text-align: center;
        }
        .developer-contact {
            font-size: 11px;
            margin: 5px 0;
        }
        .powered-by {
            color: #ff6b6b;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="main-header">
            <div class="parking-logo">
                🅿️
            </div>
            <div class="header-text">
                <h2>Vengatesan Car Parking</h2>
                <p>Secure & Convenient Parking Solutions</p>
            </div>
        </div>
        
        <div class="business-info">
            <p><strong>📍 Address:</strong> Tittagudi</p>
            <p><strong>📞 Contact:</strong> 9791365506</p>
            <p><strong>💰 Monthly Rate:</strong> Rs. 1000</p>
        </div>
        
        <form action="/generate" method="POST">
            <div class="form-group">
                <label>Customer Name:</label>
                <input type="text" name="name" placeholder="Enter customer full name" required>
            </div>
            
            <div class="form-group">
                <label>Vehicle Number:</label>
                <input type="text" name="vehicle_no" placeholder="e.g., TN45AB1234" required>
            </div>
            
            <div class="form-group">
                <label>Vehicle Type:</label>
                <select name="vehicle_type" required>
                    <option value="">Select Vehicle Type</option>
                    <option value="car">Car</option>
                    <option value="bike">Bike</option>
                    <option value="truck">Truck</option>
                </select>
            </div>
            
            <div class="form-group">
                <label>Parking Slot Number:</label>
                <select name="slot_number" required>
                    <option value="">Select Parking Slot</option>
                    {% for slot in slots %}
                    <option value="{{ slot }}">{{ slot }}</option>
                    {% endfor %}
                </select>
            </div>
            
            <div class="form-group">
                <label>Parking Month:</label>
                <select name="month" required>
                    <option value="">Select Month</option>
                    <option value="January">January</option>
                    <option value="February">February</option>
                    <option value="March">March</option>
                    <option value="April">April</option>
                    <option value="May">May</option>
                    <option value="June">June</option>
                    <option value="July">July</option>
                    <option value="August">August</option>
                    <option value="September">September</option>
                    <option value="October">October</option>
                    <option value="November">November</option>
                    <option value="December">December</option>
                </select>
            </div>
            
            <div class="form-group">
                <label>Year:</label>
                <select name="year" required>
                    <option value="">Select Year</option>
                    {% for year in years %}
                    <option value="{{ year }}" {% if year == current_year %}selected{% endif %}>{{ year }}</option>
                    {% endfor %}
                </select>
            </div>
            
            <div class="form-group">
                <label>Payment Mode:</label>
                <select name="payment_mode" required>
                    <option value="">Select Payment Mode</option>
                    <option value="Online">Online Payment</option>
                    <option value="Cash">Cash</option>
                </select>
            </div>
            
            <button type="submit">Generate Parking Bill PDF</button>
        </form>

        <!-- CodeHive Logo Section -->
        <div class="codehive-logo-section">
            <div class="codehive-main">
                <span class="codehive-code">CODE</span> 
                <span class="codehive-hive">HIVE</span>
            </div>
            <div class="codehive-tagline">LEARN AND LEAD</div>
        </div>

        <div class="developer-info">
            <div class="developer-contact">📧 Email: codehive143@gmail.com</div>
            <div class="developer-contact">📱 Phone: +91 63745 76277</div>
            <div class="developer-contact">🌐 Website: www.codehive.dev</div>
            <div class="developer-contact">💼 Specialized in: Web Applications & Automation</div>
        </div>

        <div class="footer">
            <p>Powered by <span class="powered-by">CodeHive</span> - Your Technology Partner</p>
        </div>
    </div>
</body>
</html>
'''

@app.route('/')
def home():
    current_year = datetime.now().year
    return render_template_string(HTML_TEMPLATE, slots=PARKING_SLOTS, years=YEARS, current_year=current_year)

@app.route('/generate', methods=['POST'])
def generate():
    try:
        # Get form data
        name = request.form['name']
        vehicle_no = request.form['vehicle_no']
        vehicle_type = request.form['vehicle_type']
        slot_number = request.form['slot_number']
        month = request.form['month']
        year = request.form['year']
        payment_mode = request.form['payment_mode']
        
        # Create PDF
        pdf = FPDF()
        pdf.add_page()
        
        # Header - Normal size
        pdf.set_font("Arial", style="B", size=16)
        pdf.cell(200, 10, txt="VENGATESAN CAR PARKING", ln=1, align="C")
        pdf.set_font("Arial", size=10)
        pdf.cell(200, 8, txt="Tittagudi | Contact: 9791365506", ln=1, align="C")
        pdf.ln(10)
        
        # Title - Normal size
        pdf.set_font("Arial", style="B", size=18)
        pdf.cell(200, 15, txt="MONTHLY PARKING BILL", ln=1, align="C")
        pdf.ln(5)
        
        # Bill Details - Normal size
        pdf.set_font("Arial", style="B", size=12)
        pdf.cell(200, 10, txt="BILL DETAILS", ln=1)
        pdf.set_font("Arial", size=11)
        
        details = [
            ("Bill Date", datetime.now().strftime("%d-%m-%Y")),
            ("Customer Name", name),
            ("Vehicle Number", vehicle_no),
            ("Vehicle Type", vehicle_type.upper()),
            ("Parking Slot", slot_number),
            ("Parking Period", f"{month} {year}"),
            ("Payment Mode", payment_mode)
        ]
        
        for label, value in details:
            pdf.cell(60, 8, txt=label + ":", ln=0)
            pdf.cell(130, 8, txt=str(value), ln=1)
        
        pdf.ln(10)
        
        # Amount Section - Normal size
        pdf.set_font("Arial", style="B", size=12)
        pdf.cell(200, 10, txt="AMOUNT DETAILS", ln=1)
        pdf.set_font("Arial", size=11)
        
        pdf.cell(120, 10, txt="Monthly Parking Charges:", ln=0)
        pdf.cell(70, 10, txt=f"Rs. 1000.00", ln=1)
        
        pdf.ln(8)
        
        # Total Amount - Normal size
        pdf.set_font("Arial", style="B", size=14)
        pdf.cell(120, 12, txt="TOTAL AMOUNT:", ln=0)
        pdf.cell(70, 12, txt=f"Rs. 1000.00", ln=1)
        
        pdf.ln(15)
        
        # FOOTER SECTION - SMALLER FONT SIZES
        pdf.set_font("Arial", style="B", size=8)
        pdf.cell(200, 4, txt="-" * 50, ln=1, align="C")
        pdf.set_font("Arial", style="B", size=10)
        pdf.cell(200, 6, txt="CODE HIVE", ln=1, align="C")
        pdf.set_font("Arial", style="I", size=8)
        pdf.cell(200, 5, txt="LEARN AND LEAD", ln=1, align="C")
        pdf.set_font("Arial", style="B", size=8)
        pdf.cell(200, 4, txt="-" * 50, ln=1, align="C")
        pdf.ln(2)
        
        # Developer Information - Smaller
        pdf.set_font("Arial", style="B", size=8)
        pdf.cell(200, 5, txt="Development Partner", ln=1, align="C")
        pdf.set_font("Arial", size=7)
        pdf.cell(200, 4, txt="Email: codehive143@gmail.com", ln=1, align="C")
        pdf.cell(200, 4, txt="Phone: +91 63745 76277", ln=1, align="C")
        pdf.cell(200, 4, txt="Web: www.codehive.dev", ln=1, align="C")
        pdf.cell(200, 4, txt="Specialized in Web Applications & Automation", ln=1, align="C")
        pdf.ln(3)
        
        # Final Footer - Smallest
        pdf.set_font("Arial", style="I", size=7)
        pdf.cell(200, 4, txt="Thank you for choosing Vengatesan Car Parking!", ln=1, align="C")
        pdf.cell(200, 4, txt="This is a computer-generated bill.", ln=1, align="C")
        pdf.ln(2)
        pdf.set_font("Arial", style="B", size=7)
        pdf.cell(200, 4, txt="Powered by CodeHive - Your Technology Partner", ln=1, align="C")
        
        # Generate PDF in memory
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        
        filename = f"Parking_Bill_{name.replace(' ', '_')}_{month}_{year}.pdf"
        
        return pdf_bytes, 200, {
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'attachment; filename={filename}'
        }
        
    except Exception as e:
        return f"Error generating bill: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True)


