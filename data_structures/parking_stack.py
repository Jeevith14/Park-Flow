"""
=============================================================================
PARKFLOW DATA STRUCTURES MODULE: parking_stack.py
=============================================================================
Academic Topic: Stack Data Structure (LIFO: Last-In, First-Out)
Implementation: Hand-crafted Stack using a Python List

College / Viva Presentation Summary:
- A Stack is a linear data structure that follows the LIFO (Last-In, First-Out)
  principle, where the element added most recently is the first to be removed.
- In ParkFlow, the available parking slots are managed by a ParkingStack.
- When all 20 slots are free, the stack holds slots [20, 19, ..., 1] with Slot 1
  at the TOP.
- POP operation: When a vehicle enters, pop() removes the TOP slot from the
  stack and allocates it to the vehicle.
- PUSH operation: When a vehicle leaves, push(slot) returns that freed slot back
  to the TOP of the stack.
- Real-World Benefit: The most recently vacated slot is re-allocated immediately,
  optimizing lot turnaround and turnaround time.

Time Complexities:
- push(slot):  O(1)
- pop():       O(1)
- peek():      O(1)
- is_empty():  O(1)
- size():      O(1)
=============================================================================
"""

from typing import List, Optional, Any, Dict


class StackUnderflowError(Exception):
    """Raised when attempting to pop or peek an empty stack."""
    pass


class StackOverflowError(Exception):
    """Raised when pushing to a stack that has exceeded maximum capacity."""
    pass


class ParkingStack:
    """
    ParkingStack manages parking slot allocations using a LIFO Stack.
    """

    MAX_CAPACITY = 20

    def __init__(self, initial_slots: Optional[List[int]] = None):
        """
        Initialize the parking stack.
        
        Args:
            initial_slots: Optional list of slot numbers to initialize the stack.
                           If None, initializes a full lot: [20, 19, ..., 2, 1]
                           so Slot 1 is at the TOP (end of the list).
        """
        if initial_slots is not None:
            # Validate input list
            self._slots: List[int] = list(initial_slots)
        else:
            # Default: 20 slots down to 1. Slot 1 is at the top (end of list).
            self._slots: List[int] = list(range(self.MAX_CAPACITY, 0, -1))

    def push(self, slot: int) -> None:
        """
        PUSH operation: Add a freed parking slot back to the top of the stack.
        
        Academic note: In Python's list implementation, list.append() inserts at
        the end of the list in amortized O(1) time, representing the TOP of the stack.
        
        Args:
            slot: The integer slot number (1 to MAX_CAPACITY).
            
        Raises:
            ValueError: If slot is invalid or already present in the stack.
            StackOverflowError: If stack already has MAX_CAPACITY slots.
        """
        if not isinstance(slot, int) or slot < 1 or slot > self.MAX_CAPACITY:
            raise ValueError(f"Invalid slot number: {slot}. Must be between 1 and {self.MAX_CAPACITY}.")

        if slot in self._slots:
            raise ValueError(f"Slot {slot} is already available in the stack.")

        if len(self._slots) >= self.MAX_CAPACITY:
            raise StackOverflowError(f"Cannot push to stack: full capacity ({self.MAX_CAPACITY}) reached.")

        self._slots.append(slot)

    def pop(self) -> int:
        """
        POP operation: Remove and return the top available slot from the stack.
        
        Academic note: In Python's list implementation, list.pop() removes from
        the end of the list in O(1) time, representing the TOP of the stack.
        
        Returns:
            The integer slot number allocated to the incoming vehicle.
            
        Raises:
            StackUnderflowError: If all parking slots are occupied (stack is empty).
        """
        if self.is_empty():
            raise StackUnderflowError("Parking Stack is empty! No parking slots available.")

        return self._slots.pop()

    def peek(self) -> Optional[int]:
        """
        PEEK operation: Inspect the top available slot without removing it.
        
        Returns:
            The slot number currently at the top of the stack, or None if empty.
        """
        if self.is_empty():
            return None
        return self._slots[-1]

    def is_empty(self) -> bool:
        """
        Check whether the parking stack has zero available slots.
        
        Returns:
            True if empty, False otherwise.
        """
        return len(self._slots) == 0

    def size(self) -> int:
        """
        Return the number of available slots remaining in the stack.
        
        Returns:
            Integer count of items in stack.
        """
        return len(self._slots)

    def to_list(self) -> List[int]:
        """
        Return a copy of the stack elements from bottom to top.
        """
        return list(self._slots)

    def to_display_list(self) -> List[int]:
        """
        Return stack elements ordered from TOP to BOTTOM for visual representation.
        Index 0 represents the TOP element (next to be popped).
        """
        return list(reversed(self._slots))

    def clear(self) -> None:
        """Clear all slots from the stack."""
        self._slots.clear()

    def reset_to_full(self) -> None:
        """Reset stack to default state with all 20 slots available."""
        self._slots = list(range(self.MAX_CAPACITY, 0, -1))

    def get_details(self) -> Dict[str, Any]:
        """
        Returns structured data describing current stack state for API & UI.
        """
        return {
            "size": self.size(),
            "max_capacity": self.MAX_CAPACITY,
            "is_empty": self.is_empty(),
            "peek": self.peek(),
            "items_bottom_to_top": self.to_list(),
            "items_top_to_bottom": self.to_display_list(),
            "academic_notes": {
                "principle": "LIFO (Last-In, First-Out)",
                "push_complexity": "O(1)",
                "pop_complexity": "O(1)",
                "peek_complexity": "O(1)",
                "description": (
                    "Available parking slots are maintained in a LIFO stack. "
                    "When a vehicle arrives, pop() retrieves the top available slot. "
                    "When a vehicle departs, push(slot) returns the freed slot to the top, "
                    "ensuring the most recently freed slot is allocated next."
                )
            }
        }
