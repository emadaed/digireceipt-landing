import streamlit as st
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from PIL import Image
import qrcode
import sqlite3
import pandas as pd

st.set_page_config(
    page_title="DigiReceipt",
    page_icon="🧾",   # favicon in Streamlit tab
    layout="centered"
)

# ------------------ Database ------------------
def init_db():
    conn = sqlite3.connect("digireceipts.db")
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            vendor TEXT,
            invoice_no TEXT,
            total REAL
        )
    """
    )
    conn.commit()
    conn.close()

def log_invoice(timestamp, vendor, invoice_no, total):
    conn = sqlite3.connect("digireceipts.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO invoices (timestamp, vendor, invoice_no, total) VALUES (?, ?, ?, ?)",
        (timestamp, vendor, invoice_no, total),
    )
    conn.commit()
    conn.close()

def get_invoices(limit=10):
    conn = sqlite3.connect("digireceipts.db")
    c = conn.cursor()
    c.execute("SELECT * FROM invoices ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_next_invoice_no():
    conn = sqlite3.connect("digireceipts.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM invoices")
    count = c.fetchone()[0]
    conn.close()
    return f"INV-{datetime.today().strftime('%Y%m%d')}-{count + 1}"

init_db()

# ------------------ UI ------------------
st.title("🧾 DigiReceipt – رسید بنائیں، فوراً حاصل کریں")
st.markdown(
    "سادہ رسید بنانے والا موبائل ایپ۔ لوگو اپلوڈ کریں، تفصیلات درج کریں، اور PDF رسید حاصل کریں۔"
)

# Logo upload
logo = st.file_uploader("🔗 دکان کا لوگو اپلوڈ کریں", type=["png", "jpg", "jpeg"])
if logo:
    st.image(logo, width=100)

with st.form("invoice_form"):
    st.markdown("### 🏪 دکان کی معلومات")
    vendor_name = st.text_input("Store Name / دکان کا نام")
    store_address = st.text_input("Address / پتہ")
    store_phone = st.text_input("Phone / فون نمبر")
    ntn = st.text_input("NTN / ٹیکس نمبر")
    tax_format = st.text_input("Tax Format / ٹیکس فارمیٹ")
    pos_id = st.text_input("POS ID")
    terminal_id = st.text_input("Terminal ID")
    cashier_id = st.text_input("Cashier ID")

    st.markdown("### 🧾 رسید کی تفصیلات")
    invoice_no = st.text_input("Invoice Number / رسید نمبر", value=get_next_invoice_no())
    payment_method = st.selectbox(
        "Payment Method / ادائیگی کا طریقہ",
        ["Cash", "Credit Card", "Bank Transfer", "Easypaisa", "JazzCash"],
    )
    warranty_note = st.selectbox(
        "Warranty / وارنٹی",
        [
            "14-Day Return Policy",
            "No Returns, Only Replacement",
            "Service Warranty: 7 Days",
            "Product Warranty: 30 Days",
            "No Warranty Provided",
        ],
    )
    footer_note = st.text_area(
        "Footer Note / آخر میں نوٹ",
        value="Verify this invoice via FBR TaxAsaan App or SMS at 9966.",
    )
    tax_rate = st.number_input("Sales Tax %", min_value=0.0, max_value=100.0, value=18.0)

    st.markdown("### 🛒 اشیاء کی تفصیلات")
    item_count = st.number_input("How many items?", min_value=1, max_value=20, value=5)
    items = []
    for i in range(1, item_count + 1):
        with st.expander(f"Item {i}"):
            name = st.text_input(f"Item {i} Name", key=f"name_{i}")
            code = st.text_input(f"Item {i} Code", key=f"code_{i}")
            price = st.number_input(f"Item {i} Price", min_value=0.0, step=0.01, key=f"price_{i}")
            discount = st.number_input(f"Item {i} Discount", min_value=0.0, step=0.01, key=f"discount_{i}")
            quantity = st.number_input(f"Item {i} Quantity", min_value=0, step=1, key=f"qty_{i}")
            if name and quantity > 0:
                items.append({
                    "name": name,
                    "code": code,
                    "price": price,
                    "discount": discount,
                    "quantity": quantity,
                })
            elif name and quantity == 0:
                st.warning(f"⚠️ Quantity missing for item: {name}")

    submitted = st.form_submit_button("🧾 Generate Invoice")

# ------------------ Invoice Generation ------------------
if submitted and items:
    date = datetime.today().strftime("%d/%m/%Y")
    time = datetime.today().strftime("%H:%M")
    timestamp = f"{date} {time}"
    subtotal = sum((item["price"] - item["discount"]) * item["quantity"] for item in items)
    tax_amount = round(subtotal * (tax_rate / 100), 2)
    pos_fee = 1.00
    grand_total = round(subtotal + tax_amount + pos_fee, 2)

    # Save invoice
    log_invoice(timestamp, vendor_name, invoice_no, grand_total)

    # PDF build
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40

    if logo:
        img = Image.open(logo)
        img_width = 40 * mm
        img_height = img.height / img.width * img_width
        pdf.drawInlineImage(img, 40, y - img_height, width=img_width, height=img_height)
        y -= img_height + 20

    pdf.setFont("Courier-Bold", 12)
    pdf.drawString(40, y, vendor_name.upper())
    y -= 15
    pdf.setFont("Courier", 9)
    pdf.drawString(40, y, f"Address: {store_address}")
    pdf.drawString(300, y, f"Phone: {store_phone}")
    y -= 15
    pdf.drawString(40, y, f"NTN: {ntn}")
    pdf.drawString(300, y, f"Tax Format: {tax_format}")
    y -= 15
    pdf.drawString(40, y, f"POS: {pos_id} | Terminal: {terminal_id} | Cashier: {cashier_id}")
    y -= 15
    pdf.drawString(40, y, f"Date: {date} | Time: {time}")
    pdf.drawString(300, y, f"Invoice #: {invoice_no}")
    y -= 25

    pdf.setFont("Courier-Bold", 9)
    pdf.drawString(40, y, "Item Name")
    pdf.drawString(200, y, "Code")
    pdf.drawString(260, y, "Qty")
    pdf.drawString(300, y, "Price")
    pdf.drawString(360, y, "Disc")
    pdf.drawString(420, y, "Total")
    y -= 10
    pdf.line(40, y, 500, y)
    y -= 15

    pdf.setFont("Courier", 9)
    for item in items:
        line_total = (item["price"] - item["discount"]) * item["quantity"]
        pdf.drawString(40, y, item["name"][:20])
        pdf.drawString(200, y, item["code"])
        pdf.drawRightString(260, y, str(item["quantity"]))
        pdf.drawRightString(300, y, f"{item['price']:.2f}")
        pdf.drawRightString(360, y, f"{item['discount']:.2f}")
        pdf.drawRightString(420, y, f"{line_total:.2f}")
        y -= 20

    pdf.setFont("Courier-Bold", 9)
    pdf.drawRightString(420, y, f"Subtotal: {subtotal:.2f}")
    y -= 15
    pdf.drawRightString(420, y, f"Sales Tax ({tax_rate:.2f}%): {tax_amount:.2f}")
    y -= 15
    pdf.drawRightString(420, y, f"POS Fee: {pos_fee:.2f}")
    y -= 15
    pdf.drawRightString(420, y, f"Grand Total: {grand_total:.2f}")
    y -= 25
    pdf.setFont("Courier", 9)
    pdf.drawString(40, y, f"Payment: {payment_method}")
    y -= 15
    pdf.drawString(40, y, f"Warranty: {warranty_note}")
    y -= 15
    pdf.drawString(40, y, footer_note)
    y -= 60

    # QR Code with full data
    qr_data = {
        "invoice_no": invoice_no,
        "vendor": vendor_name,
        "date": timestamp,
        "items": items,
        "subtotal": subtotal,
        "tax": tax_amount,
        "total": grand_total
    }
    qr = qrcode.make(str(qr_data))
    qr_buffer = BytesIO()
    qr.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    qr_img = Image.open(qr_buffer)
    pdf.drawInlineImage(qr_img, 40, y, width=50, height=50)

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    st.download_button("📥 Download PDF Receipt", buffer, file_name=f"{invoice_no}.pdf")

# ------------------ Owner-only history ------------------
owner_code = st.text_input("🔐 Enter Owner Code to View History", type="password")
if "OWNER_CODE" in st.secrets and owner_code == st.secrets["OWNER_CODE"]:
    st.subheader("📜 Receipt History (Last 10)")
    invoices = get_invoices()
    df = pd.DataFrame(invoices, columns=["ID", "Timestamp", "Vendor", "Invoice #", "Total"])
    st.dataframe(df)
else:
    st.info("Receipt history is restricted to the owner.")
