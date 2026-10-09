"""
=============================================================================
PARKFLOW – SMART PARKING MANAGER (app.py)
=============================================================================
Academic Topic: Flask Web Controller, RESTful API & Serverless Dispatcher
Data Structure: Python Stack (LIFO: Last-In, First-Out)
=============================================================================
"""

import os
import sys
from flask import Flask, render_template, request, jsonify, send_from_directory

# Base directory for relative template and static asset resolution
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from services import parking_service
import database

# Initialize Flask application
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
    static_url_path="/static"
)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "parkflow-smart-parking-secret-key-2026")

# Safe initialization of database tables and initial stack state
try:
    database.init_db()
except Exception as e:
    print(f"[Warning] Startup init_db bypassed: {e}")


# WSGI Middleware to normalize Vercel serverless rewrite paths
class VercelPathFixMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        # On Vercel, RAW_URI or REQUEST_URI preserves the client's actual requested path
        raw_uri = environ.get("RAW_URI") or environ.get("REQUEST_URI")
        if raw_uri:
            environ["PATH_INFO"] = raw_uri.split("?")[0]
        else:
            path = environ.get("PATH_INFO", "")
            if path in ("/api/index.py", "/api/index", "/api", "/api/"):
                environ["PATH_INFO"] = "/"
            elif path.startswith("/api/index.py/"):
                environ["PATH_INFO"] = path[len("/api/index.py"):]

        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathFixMiddleware(app.wsgi_app)


# =============================================================================
# WEB VIEWS & STATIC ASSET HANDLERS
# =============================================================================

@app.route("/")
def index():
    """Render the main ParkFlow Single-Page Application interface."""
    if request.args.get("debug") == "1":
        return jsonify({k: str(v) for k, v in request.environ.items() if isinstance(v, (str, int))})
    try:
        return render_template("index.html")
    except Exception as e:
        # Fallback to direct HTML file read if template engine encounters bundle path issues
        for possible_path in [
            os.path.join(BASE_DIR, "templates", "index.html"),
            os.path.join(os.getcwd(), "templates", "index.html"),
            os.path.join("/var/task", "templates", "index.html")
        ]:
            if os.path.exists(possible_path):
                try:
                    with open(possible_path, "r", encoding="utf-8") as f:
                        return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}
                except Exception:
                    pass
        return f"ParkFlow Backend Running. Template error: {e}", 500


@app.route("/static/<path:filename>")
def custom_static(filename):
    """Ensure static assets are always found in serverless environments."""
    for folder in [
        os.path.join(BASE_DIR, "static"),
        os.path.join(os.getcwd(), "static"),
        os.path.join("/var/task", "static")
    ]:
        target = os.path.join(folder, filename)
        if os.path.exists(target):
            return send_from_directory(folder, filename)
    return jsonify({"error": f"Static file {filename} not found"}), 404


# Vercel handler export
handler = app


# =============================================================================
# RESTful API ENDPOINTS
# =============================================================================

@app.route("/api/status", methods=["GET"])
def api_status():
    """
    Return dashboard statistics: total slots, occupied, available,
    utilization %, and stack peek.
    """
    try:
        data = parking_service.get_dashboard_data()
        return jsonify({
            "success": True,
            "data": data,
            "database_engine": "PostgreSQL" if database.IS_POSTGRES else "SQLite"
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/slots", methods=["GET"])
def api_slots():
    """
    Return all 20 parking slots with live status and parked vehicle details.
    """
    try:
        slots = database.get_all_slots()
        return jsonify({"success": True, "slots": slots}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stack", methods=["GET"])
def api_stack():
    """
    Return the live Python ParkingStack state, items from top to bottom,
    size, and academic viva notes.
    """
    try:
        stack = parking_service.get_stack()
        return jsonify({"success": True, "stack": stack.get_details()}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/vehicles", methods=["GET"])
def api_vehicles():
    """
    Return all currently parked vehicles.
    """
    try:
        vehicles = database.get_active_vehicles()
        return jsonify({"success": True, "vehicles": vehicles}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/park", methods=["POST"])
def api_park():
    """
    Allocate an available parking slot to an incoming vehicle using stack.pop().
    """
    try:
        payload = request.get_json(silent=True) or request.form
        vehicle_no = payload.get("vehicle_no", "").strip()
        owner_name = payload.get("owner_name", "").strip()
        vehicle_type = payload.get("vehicle_type", "Car").strip()

        success, message, data = parking_service.park_vehicle(
            vehicle_no=vehicle_no,
            owner_name=owner_name,
            vehicle_type=vehicle_type
        )

        status_code = 200 if success else 400
        return jsonify({
            "success": success,
            "message": message,
            "data": data
        }), status_code

    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/exit", methods=["POST"])
def api_exit():
    """
    Process vehicle exit and return the slot to the stack using stack.push(slot).
    """
    try:
        payload = request.get_json(silent=True) or request.form
        slot_number = payload.get("slot_number")
        vehicle_no = payload.get("vehicle_no")

        identifier = slot_number if slot_number is not None else vehicle_no
        if identifier is None:
            return jsonify({"success": False, "message": "Slot number or vehicle registration number is required."}), 400

        success, message, data = parking_service.exit_vehicle(identifier)

        status_code = 200 if success else 400
        return jsonify({
            "success": success,
            "message": message,
            "data": data
        }), status_code

    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/api/search", methods=["GET"])
def api_search():
    """
    Search parked and exited vehicles by vehicle number or owner name.
    """
    try:
        query = request.args.get("q", "").strip()
        results = parking_service.search(query)
        return jsonify({"success": True, "results": results, "query": query}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/history", methods=["GET"])
def api_history():
    """
    Return complete vehicle parking history log.
    """
    try:
        history = parking_service.get_history()
        return jsonify({"success": True, "history": history}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """
    Reset all parking slots and rebuild the fresh 20-slot stack.
    """
    try:
        success, message = parking_service.reset_system()
        return jsonify({"success": success, "message": message}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Reset failed: {str(e)}"}), 500


@app.route("/api/health", methods=["GET"])
def api_health():
    """Health check endpoint for deployment monitoring."""
    return jsonify({
        "status": "healthy",
        "app": "ParkFlow - Smart Parking Manager",
        "database": "PostgreSQL" if database.IS_POSTGRES else "SQLite",
        "stack_type": "LIFO Python List Stack",
        "total_slots": database.TOTAL_SLOTS
    }), 200


# Application entry point for local execution
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n=======================================================")
    print(f" ParkFlow – Smart Parking Manager")
    print(f" Data Structure: Python Stack (LIFO)")
    print(f" Database Engine: {'PostgreSQL' if database.IS_POSTGRES else 'SQLite (parkflow.db)'}")
    print(f" Server running at: http://127.0.0.1:{port}")
    print(f"=======================================================\n")
    app.run(host="0.0.0.0", port=port, debug=True)
