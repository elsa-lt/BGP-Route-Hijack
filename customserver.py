from http.server import HTTPServer, SimpleHTTPRequestHandler
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument('--text', default="Default web server")
FLAGS = parser.parse_args()

# Define the directory where your static files (HTML, CSS, etc.) are stored
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')

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
        else:
            # For other paths, call the default handler
            super().do_GET()

# Set the server to listen on port 80
host = ('', 80)

httpd = HTTPServer(host, Handler)
print("Serving on port 80...")
httpd.serve_forever()
