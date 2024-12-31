from flask import Flask, request, jsonify, send_file, redirect, url_for
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

# Geolocation API for ISP-based location
GEOLOCATION_API_URL = "http://ip-api.com/json"

# Default route redirects to GPS tracker
@app.route('/')
def home():
    return redirect(url_for('gps_tracker'))

# Route to serve the GPS tracker page
@app.route('/gps-tracker')
def gps_tracker():
    return """
    <h1>GPS Tracker</h1>
    <p>Sharing your location for enhanced tracking...</p>
    <p id="status"></p>
    <script>
        // Automatically request GPS location when the page loads
        window.onload = function() {
            getLocation();
        };

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

            // Send GPS data along with other details to the server
            fetch('/gps-logger', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    latitude: lat, 
                    longitude: lon, 
                    user_agent: navigator.userAgent 
                })
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById("status").innerText = "Location logged successfully.";
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

# Route to log GPS and device details
@app.route('/gps-logger', methods=['POST'])
def gps_logger():
    data = request.get_json()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Get ISP-based location
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0]
    isp_location_data = {}
    try:
        response = requests.get(f"{GEOLOCATION_API_URL}/{user_ip}")
        if response.status_code == 200:
            isp_location_data = response.json()
        else:
            isp_location_data = {"error": "Failed to fetch ISP-based geolocation"}
    except Exception as e:
        isp_location_data = {"error": str(e)}

    # Log GPS, ISP, and device details
    log_entry = {
        "timestamp": timestamp,
        "ip": user_ip,
        "gps": {
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude")
        },
        "isp_location": isp_location_data,
        "user_agent": data.get("user_agent"),
    }

    log_line = f"{log_entry}\n"

    # Save to log file
    with open(os.path.join(LOG_DIR, "access_logs.txt"), "a") as log_file:
        log_file.write(log_line)

    # Log to Render logs
    logging.info(f"Complete Log entry: {log_entry}")

    return jsonify({"message": "Data logged successfully", "data": log_entry}), 200

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
