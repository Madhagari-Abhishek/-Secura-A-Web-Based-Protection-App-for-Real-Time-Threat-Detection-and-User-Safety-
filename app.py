from flask import Flask, request, jsonify
from pymongo import MongoClient, errors
from bson.objectid import ObjectId
from flask_cors import CORS
import bcrypt
from datetime import datetime
import os
import random
from twilio.rest import Client
import keys

# Initialize the Flask app
app = Flask(__name__)
CORS(app, supports_credentials=True)  # Enable CORS for all routes and support credentials

# Directory to store uploaded files (Proofs)
UPLOAD_FOLDER = './uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Set up the MongoDB connection
client = MongoClient('mongodb')  # Change this to your MongoDB URI
db = client['S']  # Your database name
signup_collection = db['signup']  # Signup collection
complaints_collection = db['complaints']  # Complaints collection

# Initialize Twilio Client with your credentials
twilio_client = Client(keys.account_sid, keys.auth_token)

# Function to generate random latitude and longitude
def generate_random_coordinates():
    latitude = random.uniform(-90.0, 90.0)
    longitude = random.uniform(-180.0, 180.0)
    return latitude, longitude

# Function to send SMS with Google Maps link to multiple recipients
def send_sms_with_location(recipients, alert_message):
    # Loop over each recipient and send the message
    for number in recipients:
        message = twilio_client.messages.create(
            body=alert_message,
            from_=keys.twilio_number,
            to=number
        )
        print(f"SMS sent to {number} with location: {alert_message}")

# Route to handle alert sending
@app.route('/send_alert', methods=['POST'])
def send_alert():
    data = request.json
    alert_type = data.get('alert_type')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    accuracy = data.get('accuracy')

    if not alert_type or not latitude or not longitude or not accuracy:
        return jsonify({'error': 'Missing data!'}), 400

    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    time = now.strftime("%H:%M:%S")

    # Define message based on alert type
    if alert_type == 'panic':
        message_body = f"I feel I am in danger.\nDate: {date}\nTime: {time}\nLocation: https://www.google.com/maps?q={latitude},{longitude}\nAccuracy: {accuracy} meters"
        recipients = ['']  # Replace with actual recipient phone numbers
        send_sms_with_location(recipients, message_body)
        message = "Panic alert sent successfully!"

    elif alert_type == 'safe':
        message_body = f"I have reached my destination safely.\nDate: {date}\nTime: {time}\nLocation: https://www.google.com/maps?q={latitude},{longitude}\nAccuracy: {accuracy} meters"
        recipients = ['']  # Replace with actual recipient phone numbers
        send_sms_with_location(recipients, message_body)
        message = "Safe alert sent successfully!"

    else:
        return jsonify({'error': 'Invalid alert type'}), 400

    return jsonify({'message': message}), 200

# Route to handle user signup
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    email = data.get('email')
    phone = data.get('phone')
    password = data.get('password')

    # Basic validation
    if not email or not phone or not password:
        return jsonify({'error': 'All fields are required!'}), 400

    # Hash the password before storing
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    user_data = {
        'email': email,
        'phone': phone,
        'password': hashed_password
    }

    # Check if the user already exists
    if signup_collection.find_one({'email': email}):
        return jsonify({'error': 'Email already exists!'}), 400

    # Insert the user into the database
    signup_collection.insert_one(user_data)
    return jsonify({'message': 'Signup successful!'}), 201

# Route to handle user login
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    # Basic validation
    if not email or not password:
        return jsonify({'error': 'Email and password are required!'}), 400

    # Find the user by email
    user = signup_collection.find_one({'email': email})
    if user:
        # Check if the hashed password matches the provided password
        if bcrypt.checkpw(password.encode('utf-8'), user['password']):
            return jsonify({'message': 'Login successful!'}), 200
        else:
            return jsonify({'error': 'Invalid password!'}), 401
    else:
        return jsonify({'error': 'User not found!'}), 404

# Route to handle complaint submissions
@app.route('/submit_complaint', methods=['POST'])
def submit_complaint():
    complaint_type = request.form.get('complaintType')
    subject = request.form.get('subject')
    message = request.form.get('message')
    contact_method = request.form.get('contactMethod')
    proof = request.files.get('proof')

    # Basic validation
    if not subject or not message or not contact_method:
        return jsonify({'error': 'Please fill in all required fields!'}), 400

    # Save proof if uploaded
    proof_filename = None
    if proof:
        proof_filename = os.path.join(app.config['UPLOAD_FOLDER'], proof.filename)
        proof.save(proof_filename)

    # Store the complaint in the database
    complaint_data = {
        'complaint_type': complaint_type,
        'subject': subject,
        'message': message,
        'contact_method': contact_method,
        'proof': proof_filename
    }

    complaints_collection.insert_one(complaint_data)

    return jsonify({'message': 'Complaint submitted successfully!'}), 201

# Start the Flask app
if __name__ == '__main__':
    app.run(host='1', port=5000, debug=True)
