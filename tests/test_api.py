"""
=============================================================================
PARKFLOW END-TO-END TEST SUITE (test_api.py)
=============================================================================
Tests all core features specified in the project requirements:
1. Park a vehicle and verify slot allocation.
2. Park multiple vehicles and check the parking map.
3. Exit a vehicle and verify that its slot becomes available.
4. Search for an existing and a nonexistent vehicle.
5. Prevent duplicate vehicle entries.
6. Handle a full parking lot (20 slots capacity).
7. Verify that records persist across requests.
=============================================================================
"""

import unittest
import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import database
from app import app


class TestParkFlowE2E(unittest.TestCase):

    def setUp(self):
        # Configure test database
        self.test_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_api_parkflow.db"))
        database.SQLITE_DB_PATH = self.test_db_path
        database.IS_POSTGRES = False
        database.DATABASE_URL = None
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

        database.init_db()
        self.client = app.test_client()

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    def test_01_index_page(self):
        """Verify web interface loads properly with status 200."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"ParkFlow", res.data)
        self.assertIn(b"Python Stack", res.data)

    def test_02_initial_status(self):
        """Verify initial lot state has 20 total, 20 available, 0 occupied."""
        res = self.client.get("/api/status")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertEqual(data["total_slots"], 20)
        self.assertEqual(data["available_slots"], 20)
        self.assertEqual(data["occupied_slots"], 0)
        self.assertEqual(data["next_available_slot"], 1)

    def test_03_park_vehicle_allocation(self):
        """Test feature 1: Park a vehicle and verify slot 1 allocation via POP."""
        res = self.client.post("/api/park", json={
            "vehicle_no": "KA01AB1234",
            "owner_name": "Alice Smith",
            "vehicle_type": "Car"
        })
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["slot_number"], 1)
        self.assertEqual(body["data"]["remaining_available_slots"], 19)

        # Verify status endpoint reflects change
        status_res = self.client.get("/api/status")
        sdata = status_res.get_json()["data"]
        self.assertEqual(sdata["occupied_slots"], 1)
        self.assertEqual(sdata["available_slots"], 19)
        self.assertEqual(sdata["next_available_slot"], 2)

    def test_04_park_multiple_vehicles(self):
        """Test feature 2: Park multiple vehicles and check slot allocations."""
        vehicles = [
            ("KA01AB1001", "Bob"),
            ("KA01AB1002", "Charlie"),
            ("KA01AB1003", "David")
        ]
        for idx, (plate, owner) in enumerate(vehicles):
            res = self.client.post("/api/park", json={
                "vehicle_no": plate,
                "owner_name": owner,
                "vehicle_type": "Bike"
            })
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.get_json()["data"]["slot_number"], idx + 1)

        # Check active vehicles endpoint
        v_res = self.client.get("/api/vehicles")
        v_data = v_res.get_json()["vehicles"]
        self.assertEqual(len(v_data), 3)

    def test_05_prevent_duplicate_vehicle_entries(self):
        """Test feature 5: Prevent duplicate vehicle entries."""
        # Park vehicle first time
        res1 = self.client.post("/api/park", json={
            "vehicle_no": "TN07XYZ9999",
            "owner_name": "Eve",
            "vehicle_type": "SUV"
        })
        self.assertEqual(res1.status_code, 200)

        # Attempt to park duplicate vehicle
        res2 = self.client.post("/api/park", json={
            "vehicle_no": "tn07xyz9999",  # lowercase variation
            "owner_name": "Eve Duplicate",
            "vehicle_type": "SUV"
        })
        self.assertEqual(res2.status_code, 400)
        self.assertIn("already parked", res2.get_json()["message"])

    def test_06_exit_vehicle_and_slot_release(self):
        """Test feature 3: Exit a vehicle and verify slot pushed back to stack."""
        # Park slot 1 and slot 2
        self.client.post("/api/park", json={"vehicle_no": "CAR1", "owner_name": "User 1"})
        self.client.post("/api/park", json={"vehicle_no": "CAR2", "owner_name": "User 2"})

        # Exit CAR1 (from slot 1)
        exit_res = self.client.post("/api/exit", json={"slot_number": 1})
        self.assertEqual(exit_res.status_code, 200)
        exit_data = exit_res.get_json()
        self.assertTrue(exit_data["success"])
        self.assertEqual(exit_data["data"]["slot_number"], 1)

        # Stack peek should now be Slot 1 because it was just pushed to the top (LIFO)!
        stack_res = self.client.get("/api/stack")
        stack_data = stack_res.get_json()["stack"]
        self.assertEqual(stack_data["peek"], 1)

        # Next park should allocate slot 1 again!
        new_park = self.client.post("/api/park", json={"vehicle_no": "CAR3", "owner_name": "User 3"})
        self.assertEqual(new_park.get_json()["data"]["slot_number"], 1)

    def test_07_search_vehicle(self):
        """Test feature 4: Search for existing and nonexistent vehicle."""
        self.client.post("/api/park", json={"vehicle_no": "SEARCHME1", "owner_name": "Sherlock Holmes"})

        # Search existing by plate
        s1 = self.client.get("/api/search?q=SEARCHME1")
        self.assertEqual(s1.status_code, 200)
        results1 = s1.get_json()["results"]
        self.assertEqual(len(results1), 1)
        self.assertEqual(results1[0]["vehicle_no"], "SEARCHME1")

        # Search existing by owner
        s2 = self.client.get("/api/search?q=sherlock")
        self.assertEqual(s2.status_code, 200)
        results2 = s2.get_json()["results"]
        self.assertEqual(len(results2), 1)

        # Search nonexistent
        s3 = self.client.get("/api/search?q=NONEXISTENT_CAR")
        self.assertEqual(s3.status_code, 200)
        results3 = s3.get_json()["results"]
        self.assertEqual(len(results3), 0)

    def test_08_handle_full_parking_lot(self):
        """Test feature 6: Handle full parking lot capacity (20 slots)."""
        # Fill all 20 slots
        for i in range(1, 21):
            res = self.client.post("/api/park", json={
                "vehicle_no": f"FULL{i:02d}",
                "owner_name": f"Driver {i}"
            })
            self.assertEqual(res.status_code, 200)

        # Verify lot is full
        status_res = self.client.get("/api/status")
        sdata = status_res.get_json()["data"]
        self.assertEqual(sdata["occupied_slots"], 20)
        self.assertEqual(sdata["available_slots"], 0)
        self.assertIsNone(sdata["next_available_slot"])

        # Attempt to park 21st vehicle
        overflow_res = self.client.post("/api/park", json={
            "vehicle_no": "OVERFLOW",
            "owner_name": "Overflow Driver"
        })
        self.assertEqual(overflow_res.status_code, 400)
        self.assertIn("full", overflow_res.get_json()["message"].lower())

    def test_09_reset_system(self):
        """Test reset system endpoint."""
        # Park a vehicle
        self.client.post("/api/park", json={"vehicle_no": "TEMP1", "owner_name": "Temp"})

        # Call reset
        res = self.client.post("/api/reset")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])

        # Verify status is back to 20 available, 0 occupied
        status_res = self.client.get("/api/status")
        sdata = status_res.get_json()["data"]
        self.assertEqual(sdata["available_slots"], 20)
        self.assertEqual(sdata["occupied_slots"], 0)


if __name__ == "__main__":
    unittest.main()
