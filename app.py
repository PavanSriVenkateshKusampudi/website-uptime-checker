from flask import Flask, render_template
import requests
import sqlite3
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# List of websites to monitor
websites = [
    "https://www.google.com",
    "https://www.github.com",
    "https://www.facebook.com",
    "https://www.nonexistentwebsite12345.com"
]

# --- Email Config ---
EMAIL_ADDRESS = "ramkeka123@gmail.com"        # Your email
EMAIL_PASSWORD = "6300329093"          # App password
TO_EMAIL = "shaikfirozahmad99@gmail.com"       # Recipient email

def send_email_alert(website):
    """Send alert email if website goes DOWN"""
    subject = f"ALERT! Website DOWN: {website}"
    body = f"The website {website} is currently DOWN. Checked at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = TO_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ Alert email sent for {website}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect("uptime.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  url TEXT,
                  status TEXT,
                  time TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS last_status
                 (url TEXT PRIMARY KEY, status TEXT)''')
    conn.commit()
    conn.close()

def log_status(url, status):
    conn = sqlite3.connect("uptime.db")
    c = conn.cursor()
    # Insert into logs
    c.execute("INSERT INTO logs (url, status, time) VALUES (?, ?, ?)",
              (url, status, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()

    # Update last_status table
    c.execute("SELECT status FROM last_status WHERE url=?", (url,))
    row = c.fetchone()
    if row is None:
        c.execute("INSERT INTO last_status (url, status) VALUES (?, ?)", (url, status))
    else:
        last_status = row[0]
        if last_status != status and status == "DOWN":
            # Send email only if status changed to DOWN
            send_email_alert(url)
        c.execute("UPDATE last_status SET status=? WHERE url=?", (status, url))

    conn.commit()
    conn.close()

def get_logs(limit=50):
    conn = sqlite3.connect("uptime.db")
    c = conn.cursor()
    c.execute("SELECT url, status, time FROM logs ORDER BY id DESC LIMIT ?", (limit,))
    data = c.fetchall()
    conn.close()
    return data

# --- Website Checker ---
def check_website(url):
    try:
        response = requests.get(url, timeout=5)
        return "UP" if response.status_code == 200 else "DOWN"
    except requests.RequestException:
        return "DOWN"

# --- Flask Routes ---
@app.route("/")
def index():
    results = []
    for site in websites:
        status = check_website(site)
        log_status(site, status)
        results.append({
            "url": site,
            "status": "✅ UP" if status == "UP" else "❌ DOWN",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    return render_template("index.html", results=results)

@app.route("/history")
def history():
    logs = get_logs(100)
    chart_data = {}
    for url, status, time in logs:
        if url not in chart_data:
            chart_data[url] = {"times": [], "statuses": []}
        chart_data[url]["times"].append(time)
        chart_data[url]["statuses"].append(1 if status == "UP" else 0)
    return render_template("history.html", logs=logs, chart_data=chart_data)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
