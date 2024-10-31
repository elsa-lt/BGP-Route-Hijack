
from flask import Flask, Response, request, jsonify
from flask_cors import CORS
import subprocess
import os
import argparse
import json

app = Flask(__name__)
CORS(app)

# Set up argument parser
parser = argparse.ArgumentParser(description="Proxy server for curl commands.")
parser.add_argument('pid', type=int, help='Process ID to be used with mnexec')
args = parser.parse_args()

# Store the provided PID in a global variable
pid = args.pid

# Mapping of file extensions to MIME types
MIME_TYPES = {
    'html': 'text/html',
    'css': 'text/css',
    'js': 'application/javascript',
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'svg': 'image/svg+xml',
    'txt': 'text/plain',
}

def get_mime_type(filename):
    # Extract the file extension
    _, ext = os.path.splitext(filename)
    # Remove the dot and convert to lowercase
    ext = ext[1:].lower()
    # Return the corresponding MIME type or default to 'application/octet-stream'
    return MIME_TYPES.get(ext, 'application/octet-stream')


@app.route('/')
def index():
    try:
        result = subprocess.run(
            ['sudo', 'mnexec', '-a', str(pid), 'curl', f'http://15.0.1.1/'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return Response(result.stdout, mimetype='text/html')
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}", 500


@app.route('/<path:filename>')
def fetch_file(filename):
    try:
        # Execute the curl command to get content from 15.0.1.1/<filename>
        result = subprocess.run(
            ['sudo', 'mnexec', '-a', str(pid), 'curl', f'http://15.0.1.1/{filename}'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            check=True
        )
        
        mime_type = get_mime_type(filename)

        return Response(result.stdout, mimetype=mime_type)
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}", 500
    
@app.route('/login/user', methods=['POST'])
def submit_login():
    # Extract JSON payload and headers
    login_data = request.json
    username = login_data.get('username')
    password = login_data.get('password')
    # Prepare the JSON payload for the curl command as a string
    json_data = f'{{"username": "{username}", "password": "{password}"}}'

    # Run the curl command with the specified headers to forward the request
    try:
        result = subprocess.run(
            ['sudo', 'mnexec', '-a', str(pid), 'curl', '-X', 'POST', 
                '-H', 'Content-Type: application/json',
                '-H', f'Authorization: Basic {username}:{password}', 
                '-d', json_data, 
                'http://15.0.1.1/login/user'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        
        # Send response back to client
        if "success" in result.stdout:
            return Response(status=200)  # Login successful, send 200 status only
        else:
            return Response(status=401)  # Login failed, send 401 status only
        
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}", 500
    
@app.route('/account/secret', methods=['GET'])
def get_secret():
    auth = request.headers.get('Authorization')
    if not auth:
        return jsonify({"message": "Unauthorized access."}), 401

    try:
        # Make a GET request to retrieve the secret
        result = subprocess.run(
            ['sudo', 'mnexec', '-a', str(pid), 'curl', '-X', 'GET',
                '-H', f'Authorization: {auth}', 
                'http://15.0.1.1/account/secret'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        
        print("STDOUT:", result.stdout)

        # Forward the response from the external server
        return result.stdout, 200

    except subprocess.CalledProcessError as e:
        print("Error:", e.stderr)
        return jsonify({'error': e.stderr}), e.returncode


@app.route('/account/secret', methods=['POST'])
def save_secret():
    data = request.get_json()
    if not data or 'secret_word' not in data:
        return jsonify({"message": "Secret word is required."}), 400
    
    auth = request.headers.get('Authorization')
    if not auth:
        return jsonify({"message": "Unauthorized access."}), 401
    
    secret_word = data['secret_word']
    
    # Prepare JSON data to send
    json_data = f'{{"secret_word": "{secret_word}"}}'
    print("json_data : " + json_data)

    try:
        # Make a POST request to save the secret
        result = subprocess.run(
            ['sudo', 'mnexec', '-a', str(pid), 'curl', '-X', 'POST',
                '-H', 'Content-Type: application/json',
                '-H', f'Authorization: {auth}', 
                '-d', json_data,
                'http://15.0.1.1/account/secret'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )

        # Forward the response from the external server
        return result.stdout, 200

    except subprocess.CalledProcessError as e:
        print("Error:", e.stderr)
        return jsonify({'error': e.stderr}), e.returncode

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
                                                        
