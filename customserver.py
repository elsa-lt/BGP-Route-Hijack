from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import argparse
import os
import base64

parser = argparse.ArgumentParser()
parser.add_argument('--text', default="Default web server")
FLAGS = parser.parse_args()

VALID_LOGIN = [('admin', 'password'), ('user', '123456')]

# Define the directory where your static files (HTML, CSS, etc.) are stored
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')
SECRETS_FILE_PATH = os.path.join(WEB_DIR, 'secrets.json')

def read_secrets():
    try:
        with open(SECRETS_FILE_PATH, 'r') as f:
            secrets = json.load(f)
            return secrets
    except FileNotFoundError:
        return {}

def write_secrets(secrets):
    try:
        with open(SECRETS_FILE_PATH, 'w') as f:
            json.dump(secrets, f)
            return
    except FileNotFoundError:
        return

class Handler(SimpleHTTPRequestHandler):
    # Override the method to serve static files from your 'web' directory
    def translate_path(self, path):
        # Ensure the path requested corresponds to files in the 'web' directory
        return os.path.join(WEB_DIR, path.lstrip('/'))
    
    # Override the do_GET method
    def do_GET(self):
        if self.path == '/':  # If the root path is requested
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html_response = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Home</title>
            </head>
            <body>
                <h1>{FLAGS.text}</h1>
            </body>
            </html>
            """
            self.wfile.write(html_response.encode('utf-8'))
            self.wfile.flush()

        elif self.path == '/account/secret':
            # Check Authorization header
            auth_header = self.headers.get('Authorization')
            if not auth_header:
                self.send_response(401)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {"message": "Authorization header missing."}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return
            
            try:
                _, credentials = auth_header.split(' ', 1)
                decoded_credentials = base64.b64decode(credentials).decode('utf-8')
                username, _ = decoded_credentials.split(':', 1)

                # Read the secrets file for user
                secrets = read_secrets()
                secret_word = secrets.get(username)

                if secret_word:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    response = {"secret_word": secret_word}
                    self.wfile.write(json.dumps(response).encode('utf-8'))

                else:
                    self.send_response(200)  # or 200 if you prefer to indicate no content
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    response = {"secret_word": None, "message": "No secret word currently."}
                    self.wfile.write(json.dumps(response).encode('utf-8'))

            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {"message": "Invalid Authorization header format."}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return

        else:
            # For other paths, call the default handler
            super().do_GET()

    def do_POST(self):
        # Check the path to handle the login endpoint
        if self.path == '/login/user':
            # Content length header is required to get the size of the incoming data
            content_length = int(self.headers['Content-Length'])
            # Read the incoming JSON data
            post_data = self.rfile.read(content_length)
            # Parse the JSON data
            data = json.loads(post_data)

            username = data.get('username')
            password = data.get('password')
            
            if (username, password) in VALID_LOGIN:
                response = {"status": "success", "message": "Login successful!"}
                self.send_response(200)
            else:
                response = {"status": "error", "message": "Invalid username or password."}
                self.send_response(401)

            # Send headers for JSON response
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            # Write the JSON response back to the client
            self.wfile.write(json.dumps(response).encode('utf-8'))
        
        elif self.path == '/account/secret':
            # Content length header is required to get the size of the incoming data
            content_length = int(self.headers['Content-Length'])
            # Read the incoming JSON data
            post_data = self.rfile.read(content_length)
            try:
                # Check Authorization header
                auth_header = self.headers.get('Authorization')
                _, credentials = auth_header.split(' ', 1)
                decoded_credentials = base64.b64decode(credentials).decode('utf-8')
                username,_ = decoded_credentials.split(':', 1)

                # Parse the JSON data
                data = json.loads(post_data)
                secret_word = data.get('secret_word')

                # Read the secrets file for user
                secrets = read_secrets()
                secrets[username] = secret_word

                # Write the updated secrets file
                write_secrets(secrets)  

                # Send success response
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {"secret_word": secret_word, "message": "Secret word saved successfully."}
                self.wfile.write(json.dumps(response).encode('utf-8'))
            
            except json.JSONDecodeError:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {"message": "Invalid JSON"}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return

        else:
            # If the path is not found, send a 404 response
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "End point not Found"}).encode('utf-8'))

# Set the server to listen on port 80
host = ('', 80)

httpd = HTTPServer(host, Handler)
print("Serving on port 80...")
httpd.serve_forever()
