"""
Test database operations and SQLite fallback
"""
import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import database
from data_structures.parking_stack import ParkingStack


class TestDatabase(unittest.TestCase):

    def setUp(self):
        # Use a fresh test database
        database.SQLITE_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_parkflow.db"))
        database.IS_POSTGRES = False
        database.DATABASE_URL = None
        if os.path.exists(database.SQLITE_DB_PATH):
            os.remove(database.SQLITE_DB_PATH)
        database.init_db()

    def tearDown(self):
        if os.path.exists(database.SQLITE_DB_PATH):
            try:
                os.remove(database.SQLITE_DB_PATH)
            except Exception:
                pass

    def test_init_creates_20_slots(self):
        slots = database.get_all_slots()
        self.assertEqual(len(slots), 20)
        self.assertEqual(slots[0]["slot_number"], 1)
        self.assertEqual(slots[-1]["slot_number"], 20)
        self.assertFalse(slots[0]["is_occupied"])

    def test_stack_seeded_correctly(self):
        stack_slots = database.get_stack_slots()
        self.assertEqual(len(stack_slots), 20)
        # Position 0 is 20, Position 19 is 1 (top of stack)
        self.assertEqual(stack_slots[-1], 1)
        stack = ParkingStack(initial_slots=stack_slots)
        self.assertEqual(stack.peek(), 1)
        popped = stack.pop()
        self.assertEqual(popped, 1)

    def test_park_and_exit_cycle(self):
        # 1. Pop from stack
        stack_slots = database.get_stack_slots()
        stack = ParkingStack(initial_slots=stack_slots)
        allocated_slot = stack.pop()
        self.assertEqual(allocated_slot, 1)
        database.save_stack_slots(stack.to_list())

        # 2. Park vehicle
        database.park_vehicle_in_db("KA01AB1234", "John Doe", "Car", allocated_slot, "2026-10-09 10:00:00")

        # 3. Check active vehicles
        active = database.get_active_vehicles()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["vehicle_no"], "KA01AB1234")
        self.assertEqual(active[0]["slot_number"], 1)

        # 4. Check slot table
        slots = database.get_all_slots()
        s1 = next(s for s in slots if s["slot_number"] == 1)
        self.assertEqual(s1["is_occupied"], 1)
        self.assertEqual(s1["vehicle_no"], "KA01AB1234")

        # 5. Exit vehicle
        database.exit_vehicle_from_db(1, "2026-10-09 11:30:00", 90)
        # Push back to stack
        stack.push(1)
        database.save_stack_slots(stack.to_list())

        # 6. Verify stack top is now 1 again
        updated_stack_slots = database.get_stack_slots()
        self.assertEqual(updated_stack_slots[-1], 1)
        updated_active = database.get_active_vehicles()
        self.assertEqual(len(updated_active), 0)


if __name__ == "__main__":
    unittest.main()
