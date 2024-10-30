
from flask import Flask, Response
import subprocess
import os
import argparse

app = Flask(__name__)

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
            text=True,
            check=True
        )
        
        mime_type = get_mime_type(filename)

        return Response(result.stdout, mimetype=mime_type)
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}", 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
                                                        
