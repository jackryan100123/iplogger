from flask import Flask, request, jsonify, send_file
import os
from datetime import datetime
import requests

app = Flask(__name__)

# Ensure a logs directory exists
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Geolocation API configuration (example: ip-api)
GEOLOCATION_API_URL = "http://ip-api.com/json"

# Default route for the root URL
@app.route('/')
def home():
    return """
    <h1>Welcome to the Enhanced Tracking App</h1>
    <p>Use the following endpoints:</p>
    <ul>
        <li><b>/track?user=USER_ID</b>: Tracking pixel endpoint (logs user data)</li>
        <li><b>/view-logs</b>: View logged data</li>
        <li><b>/health</b>: Health check</li>
    </ul>
    """

# Route to handle tracking pixel requests
@app.route('/track')
def track():
    # Extract user details
    user_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'Unknown')
    referrer = request.referrer or 'Direct'
    user_id = request.args.get('user', 'Unknown')  # Optional user identifier
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Fetch geolocation data
    location_data = {}
    try:
        response = requests.get(f"{GEOLOCATION_API_URL}/{user_ip}")
        if response.status_code == 200:
            location_data = response.json()
    except Exception as e:
        location_data = {"error": str(e)}

    # Log data
    log_entry = {
        "timestamp": timestamp,
        "ip": user_ip,
        "user_agent": user_agent,
        "referrer": referrer,
        "user_id": user_id,
        "location": location_data,
    }
    log_line = f"{log_entry}\n"

    # Save to log file
    with open(os.path.join(LOG_DIR, "access_logs.txt"), "a") as log_file:
        log_file.write(log_line)

    # Serve a transparent tracking pixel
    return send_file("static/transparent.png", mimetype="image/png")

# Route to view logs (secured)
@app.route('/view-logs', methods=['GET'])
def view_logs():
    with open(os.path.join(LOG_DIR, "access_logs.txt"), "r") as log_file:
        logs = log_file.read()
    return jsonify({"logs": logs})

# Health check (useful for deployment testing)
@app.route('/health')
def health():
    return "App is running!"

if __name__ == "__main__":
    # Run the application
    app.run(host="0.0.0.0", port=5000)
