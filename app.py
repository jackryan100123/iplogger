from flask import Flask, request, jsonify, send_file
import os
from datetime import datetime
import requests
import logging

# Initialize Flask app
app = Flask(__name__)

# Ensure a logs directory exists
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Configure logging to output to console (for Render logs)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Geolocation API configuration
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
    <p><a href="/gps-tracker">Track GPS Location</a></p>
    """

# Route to serve the GPS tracker page
@app.route('/gps-tracker')
def gps_tracker():
    return """
    <h1>GPS Tracker</h1>
    <p>Click the button below to share your GPS location.</p>
    <button onclick="getLocation()">Share GPS Location</button>
    <p id="status"></p>
    <script>
        function getLocation() {
            if (navigator.geolocation) {
                document.getElementById("status").innerText = "Requesting location...";
                navigator.geolocation.getCurrentPosition(sendLocation, showError);
            } else {
                document.getElementById("status").innerText = "Geolocation is not supported by this browser.";
            }
        }

        function sendLocation(position) {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;

            fetch('/gps-logger', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ latitude: lat, longitude: lon })
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById("status").innerText = "Location logged successfully: " + JSON.stringify(data);
            })
            .catch(error => {
                document.getElementById("status").innerText = "Error logging location.";
            });
        }

        function showError(error) {
            switch(error.code) {
                case error.PERMISSION_DENIED:
                    document.getElementById("status").innerText = "User denied the request for Geolocation.";
                    break;
                case error.POSITION_UNAVAILABLE:
                    document.getElementById("status").innerText = "Location information is unavailable.";
                    break;
                case error.TIMEOUT:
                    document.getElementById("status").innerText = "The request to get user location timed out.";
                    break;
                case error.UNKNOWN_ERROR:
                    document.getElementById("status").innerText = "An unknown error occurred.";
                    break;
            }
        }
    </script>
    """

# Route to log GPS data from the frontend
@app.route('/gps-logger', methods=['POST'])
def gps_logger():
    data = request.get_json()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Log GPS data
    log_entry = {
        "timestamp": timestamp,
        "gps": {
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude")
        }
    }

    log_line = f"{log_entry}\n"

    # Save to log file
    with open(os.path.join(LOG_DIR, "access_logs.txt"), "a") as log_file:
        log_file.write(log_line)

    # Log to Render logs
    logging.info(f"GPS Log entry: {log_entry}")

    return jsonify({"message": "GPS data logged successfully", "data": log_entry}), 200

# Route to handle tracking pixel requests
@app.route('/track')
def track():
    # Extract user details
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0]
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
        else:
            location_data = {"error": "Failed to fetch geolocation data"}
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

    # Log to Render logs
    logging.info(f"Log entry: {log_entry}")

    # Serve a transparent tracking pixel
    return send_file("static/transparent.png", mimetype="image/png")

# Route to view logs (secured)
@app.route('/view-logs', methods=['GET'])
def view_logs():
    try:
        with open(os.path.join(LOG_DIR, "access_logs.txt"), "r") as log_file:
            logs = log_file.read()
        return jsonify({"logs": logs})
    except FileNotFoundError:
        return jsonify({"error": "Log file not found"}), 404

# Health check (useful for deployment testing)
@app.route('/health')
def health():
    return "App is running!"

if __name__ == "__main__":
    # Run the application
    app.run(host="0.0.0.0", port=5000)
