import http.server
import socketserver
import os
import json
import webbrowser
import threading
import time

PORT = 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class RewariSMPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        if self.path == '/api/save-circles':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode('utf-8')
                data = json.loads(body)

                # 1. Save GeoJSON
                if 'geojson' in data and data['geojson']:
                    geojson_str = json.dumps(data['geojson'], indent=2) if isinstance(data['geojson'], dict) else data['geojson']
                    geojson_path = os.path.join(DIRECTORY, 'Rewari_30_Cleaning_Circles.geojson')
                    with open(geojson_path, 'w', encoding='utf-8') as f:
                        f.write(geojson_str)
                    print("[Server] Updated Rewari_30_Cleaning_Circles.geojson on disk.")

                # 2. Save KML if provided
                if 'kml' in data and data['kml']:
                    kml_path = os.path.join(DIRECTORY, 'Rewari_30_Cleaning_Circles.kml')
                    with open(kml_path, 'w', encoding='utf-8') as f:
                        f.write(data['kml'])
                    print("[Server] Updated Rewari_30_Cleaning_Circles.kml on disk.")

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'success', 'message': 'Circles saved to disk'}).encode('utf-8'))
            except Exception as e:
                print("[Server Error]", e)
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def open_browser():
    time.sleep(1.2)
    webbrowser.open(f'http://localhost:{PORT}')

if __name__ == '__main__':
    # Try port 8000, fallback to 8080 if in use
    for test_port in [8000, 8080, 8888]:
        try:
            httpd = socketserver.TCPServer(("", test_port), RewariSMPRequestHandler)
            PORT = test_port
            break
        except OSError:
            continue

    print(f"===========================================================")
    print(f" Rewari Municipal Council - SMP Road Cleaning Circles GIS ")
    print(f" Running at: http://localhost:{PORT}")
    print(f" Press Ctrl+C to stop.")
    print(f"===========================================================")
    threading.Thread(target=open_browser, daemon=True).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
