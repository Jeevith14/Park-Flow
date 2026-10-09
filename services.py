"""
=============================================================================
PARKFLOW SERVICES (services.py)
=============================================================================
Academic Topic: Business Logic & Data Structure Orchestration
Role:
- Bridges Flask web routes with the Python ParkingStack data structure
  and persistent database storage.
- Enforces data integrity: validation, duplicate detection, full lot handling.
- Executes Python stack operations (POP on entry, PUSH on exit).
=============================================================================
"""

from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
import database
from data_structures.parking_stack import ParkingStack, StackUnderflowError, StackOverflowError


class ParkingService:
    """Orchestrates parking operations with Python ParkingStack."""

    def __init__(self):
        # Ensure database is initialized
        database.init_db()

    def get_stack(self) -> ParkingStack:
        """
        Hydrate and return the ParkingStack from persistent storage.
        """
        slots_list = database.get_stack_slots()
        return ParkingStack(initial_slots=slots_list)

    def save_stack(self, stack: ParkingStack) -> None:
        """
        Save the in-memory ParkingStack state to persistent storage.
        """
        database.save_stack_slots(stack.to_list())

    def park_vehicle(self, vehicle_no: str, owner_name: str, vehicle_type: str = "Car") -> Tuple[bool, str, Dict[str, Any]]:
        """
        Allocate a parking slot to an incoming vehicle using stack.pop().
        
        Args:
            vehicle_no: Registration plate (e.g. KA01AB1234)
            owner_name: Name of the vehicle owner
            vehicle_type: Car, Bike, SUV, or Other
            
        Returns:
            Tuple of (success: bool, message: str, data: dict)
        """
        # 1. Validation
        if not vehicle_no or not vehicle_no.strip():
            return False, "Vehicle registration number is required.", {}
        if not owner_name or not owner_name.strip():
            return False, "Owner name is required.", {}

        clean_plate = vehicle_no.strip().upper()
        clean_owner = owner_name.strip()
        clean_type = vehicle_type.strip().capitalize() if vehicle_type else "Car"

        # 2. Check for duplicate active parked vehicle
        existing = database.find_active_vehicle(clean_plate)
        if existing:
            return False, f"Vehicle {clean_plate} is already parked in Slot {existing['slot_number']}.", {
                "slot_number": existing["slot_number"],
                "entry_time": existing["entry_time"]
            }

        # 3. Retrieve ParkingStack from persistent storage
        stack = self.get_stack()

        # 4. Check capacity / underflow
        if stack.is_empty():
            return False, "Parking lot is full! All 20 slots are currently occupied.", {
                "total_slots": database.TOTAL_SLOTS,
                "available_slots": 0
            }

        # 5. EXECUTE STACK OPERATION: POP
        # Academic Viva Highlight: pop() retrieves and removes the TOP element
        allocated_slot = stack.pop()

        # 6. Persist updated stack state
        self.save_stack(stack)

        # 7. Record vehicle entry in database
        entry_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        database.park_vehicle_in_db(
            vehicle_no=clean_plate,
            owner_name=clean_owner,
            vehicle_type=clean_type,
            slot_number=allocated_slot,
            entry_time=entry_time
        )

        return True, f"Vehicle {clean_plate} successfully parked in Slot {allocated_slot}.", {
            "slot_number": allocated_slot,
            "vehicle_no": clean_plate,
            "owner_name": clean_owner,
            "vehicle_type": clean_type,
            "entry_time": entry_time,
            "remaining_available_slots": stack.size(),
            "next_slot_peek": stack.peek(),
            "stack_operation": f"POP() -> Slot {allocated_slot}"
        }

    def exit_vehicle(self, slot_or_plate: Any) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Process vehicle exit and return slot to ParkingStack using stack.push(slot).
        
        Args:
            slot_or_plate: Integer slot number or string vehicle plate number
            
        Returns:
            Tuple of (success: bool, message: str, data: dict)
        """
        active_vehicles = database.get_active_vehicles()
        target_vehicle = None

        # Determine target vehicle by slot or plate
        if isinstance(slot_or_plate, int) or (isinstance(slot_or_plate, str) and slot_or_plate.isdigit()):
            slot_no = int(slot_or_plate)
            target_vehicle = next((v for v in active_vehicles if v["slot_number"] == slot_no), None)
        elif isinstance(slot_or_plate, str):
            clean_plate = slot_or_plate.strip().upper()
            target_vehicle = next((v for v in active_vehicles if v["vehicle_no"].upper() == clean_plate), None)

        if not target_vehicle:
            return False, f"No currently parked vehicle found for '{slot_or_plate}'.", {}

        slot_number = target_vehicle["slot_number"]
        entry_time_str = target_vehicle["entry_time"]
        exit_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Calculate duration
        try:
            entry_dt = datetime.strptime(entry_time_str, "%Y-%m-%d %H:%M:%S")
            now_dt = datetime.strptime(exit_time, "%Y-%m-%d %H:%M:%S")
            duration_minutes = max(1, int((now_dt - entry_dt).total_seconds() / 60))
        except Exception:
            duration_minutes = 1

        # 1. Update database record
        database.exit_vehicle_from_db(slot_number, exit_time, duration_minutes)

        # 2. Retrieve ParkingStack from persistent storage
        stack = self.get_stack()

        # 3. EXECUTE STACK OPERATION: PUSH
        # Academic Viva Highlight: push() returns the freed slot to the TOP of the stack
        try:
            stack.push(slot_number)
        except ValueError as e:
            # Slot was already present in stack (safety check)
            pass

        # 4. Persist updated stack state
        self.save_stack(stack)

        return True, f"Vehicle {target_vehicle['vehicle_no']} exited from Slot {slot_number}.", {
            "slot_number": slot_number,
            "vehicle_no": target_vehicle["vehicle_no"],
            "owner_name": target_vehicle["owner_name"],
            "entry_time": entry_time_str,
            "exit_time": exit_time,
            "duration_minutes": duration_minutes,
            "duration_display": f"{duration_minutes} min" if duration_minutes < 60 else f"{duration_minutes // 60}h {duration_minutes % 60}m",
            "remaining_available_slots": stack.size(),
            "next_slot_peek": stack.peek(),
            "stack_operation": f"PUSH({slot_number}) -> Slot {slot_number} now at TOP"
        }

    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Return aggregated data for dashboard KPIs, slot map, and stack status.
        """
        stack = self.get_stack()
        all_slots = database.get_all_slots()
        active_vehicles = database.get_active_vehicles()

        total = database.TOTAL_SLOTS
        occupied = len(active_vehicles)
        available = stack.size()
        utilization = round((occupied / total) * 100) if total > 0 else 0

        return {
            "total_slots": total,
            "available_slots": available,
            "occupied_slots": occupied,
            "utilization_rate": utilization,
            "next_available_slot": stack.peek(),
            "stack_details": stack.get_details(),
            "slots": all_slots,
            "active_vehicles": active_vehicles
        }

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for vehicles across active and history records.
        """
        return database.get_vehicle_history(search=query)

    def get_history(self) -> List[Dict[str, Any]]:
        """
        Get full vehicle parking audit history.
        """
        return database.get_vehicle_history()

    def reset_system(self) -> Tuple[bool, str]:
        """
        Reset all slots, vehicles, and re-initialize the 20-slot stack.
        """
        database.reset_all_parking_data()
        return True, "Parking management system has been reset to initial state with all 20 slots available."


# Global service singleton
parking_service = ParkingService()
