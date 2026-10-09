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

# Initialize database tables and initial stack state
database.init_db()


# =============================================================================
# WEB VIEWS
# =============================================================================

@app.route("/")
def index():
    """Render the main ParkFlow Single-Page Application interface."""
    return render_template("index.html")


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
