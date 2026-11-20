"""
Simple HTTP server to serve the frontend.

Run this alongside the API server:
  Terminal 1: python run_api.py
  Terminal 2: python run_frontend.py

Then open: http://localhost:3000
"""

import http.server
import socketserver
import os

PORT = 3000
DIRECTORY = "frontend"

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # Enable CORS
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
    print("=" * 70)
    print("VLA Research Engine - Frontend Server")
    print("=" * 70)
    print(f"\nFrontend running at: http://localhost:{PORT}")
    print("\nMake sure the API is also running:")
    print("  python run_api.py")
    print("\nPress Ctrl+C to stop")
    print("=" * 70)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
