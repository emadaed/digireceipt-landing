import streamlit as st
import sqlite3
from datetime import datetime
import requests
import qrcode
from PIL import Image
import io

# (1) --- Initialize SQLite database ---
def init_db():
    conn = sqlite3.connect('receipts.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            vendor TEXT,
            total REAL
        )
    ''')
    conn.commit()
    conn.close()

# (2) --- Log receipt to database ---
def log_receipt(timestamp, vendor, total):
    conn = sqlite3.connect('receipts.db')
    c = conn.cursor()
    c.execute('INSERT INTO receipts (timestamp, vendor, total) VALUES (?, ?, ?)',
              (timestamp, vendor, total))
    conn.commit()
    conn.close()

# (3) --- Retrieve receipt history ---
def get_receipts():
    conn = sqlite3.connect('receipts.db')
    c = conn.cursor()
    c.execute('SELECT * FROM receipts ORDER BY timestamp DESC')
    rows = c.fetchall()
    conn.close()
    return rows

# (4) --- Generate QR code ---
def generate_qr(data):
    qr = qrcode.make(data)
    buf = io.BytesIO()
    qr.save(buf, format='PNG')
    buf.seek(0)
    return buf

# (5) --- Optional: Send SMS using Twilio (function present, not triggered) ---
def send_sms(to_number, message):
    url = 'https://api.twilio.com/2010-04-01/Accounts/ACXXXX/Messages.json'
    auth = ('ACXXXX', 'your_auth_token')  # Replace with real credentials
    data = {
        'From': '+1234567890',
        'To': to_number,
        'Body': message
    }
    response = requests.post(url, data=data, auth=auth)
    return response.status_code

# (6) --- Initialize database ---
init_db()

# (7) --- Streamlit UI ---
st.title("🧾 DigiReceipt")

vendor = st.text_input("🏪 Vendor Name")
total = st.number_input("💰 Total Amount", min_value=0.0, format="%.2f")
send_sms_flag = st.checkbox("📩 Send SMS confirmation")
recipient_number = st.text_input("📱 Customer mobile number (e.g. +923001234567)")

if st.button("Generate Receipt"):
    timestamp = datetime.now().isoformat()
    st.success("Receipt Generated ✅")

    # (8) --- Dynamic shop title fallback ---
    shop_title = vendor if vendor else "DigiReceipt"

    # (9) --- Monospace-style receipt block (Borjan-style layout) ---
    receipt_text = f"""
-------------------------------
        {shop_title}        
-------------------------------
🕒 Time: {timestamp}
🏪 Vendor: {vendor}
💰 Total: ${total:.2f}
-------------------------------
🔖 Tax Note: Inclusive of GST
🛡️ Warranty: 30 days from purchase
📜 FBR Ref: Not yet registered
-------------------------------
    Thank you for shopping!
-------------------------------
    """
    st.code(receipt_text, language='text')

    # (10) --- Log receipt to database ---
    log_receipt(timestamp, vendor, total)

    # (11) --- Generate and display QR code ---
    qr_data = f"Vendor: {vendor} | Total: ${total:.2f} | Time: {timestamp}"
    qr_buf = generate_qr(qr_data)
    st.image(qr_buf, caption="📎 Receipt QR Code", width=200)

    # (12) --- Optional SMS (muted logic) ---
    if send_sms_flag and recipient_number:
        st.info(f"📩 SMS would be sent to: {recipient_number}")
        # status = send_sms(recipient_number, f'Receipt for {vendor}: ${total:.2f}')
        # st.write(f"📩 SMS Status: {status}")

# (13) --- Receipt History Viewer ---
st.subheader("📜 Receipt History")
for r in get_receipts():
    st.text(f"{r[1]} | {r[2]} | ${r[3]:.2f}")

