"""
Unit tests for ParkingStack data structure
"""
import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_structures.parking_stack import ParkingStack, StackUnderflowError, StackOverflowError


class TestParkingStack(unittest.TestCase):

    def test_initialization_default(self):
        stack = ParkingStack()
        self.assertEqual(stack.size(), 20)
        self.assertFalse(stack.is_empty())
        self.assertEqual(stack.peek(), 1)  # Slot 1 is at top

    def test_pop_order(self):
        stack = ParkingStack()
        # Initial stack should pop 1, 2, 3...
        first = stack.pop()
        self.assertEqual(first, 1)
        self.assertEqual(stack.size(), 19)
        self.assertEqual(stack.peek(), 2)

        second = stack.pop()
        self.assertEqual(second, 2)
        self.assertEqual(stack.size(), 18)

    def test_push_lifo_behavior(self):
        stack = ParkingStack()
        # Pop slot 1, then slot 2
        s1 = stack.pop()
        s2 = stack.pop()
        self.assertEqual(s1, 1)
        self.assertEqual(s2, 2)

        # Vehicle at slot 1 exits first -> push(1)
        stack.push(1)
        self.assertEqual(stack.peek(), 1)
        self.assertEqual(stack.size(), 19)

        # Vehicle at slot 2 exits -> push(2)
        stack.push(2)
        self.assertEqual(stack.peek(), 2)

        # Next pop should return 2 (LIFO: last freed is first allocated!)
        next_alloc = stack.pop()
        self.assertEqual(next_alloc, 2)

        # Next pop should return 1
        next_alloc2 = stack.pop()
        self.assertEqual(next_alloc2, 1)

    def test_underflow_error(self):
        stack = ParkingStack()
        # Pop all 20 slots
        for _ in range(20):
            stack.pop()

        self.assertTrue(stack.is_empty())
        self.assertEqual(stack.size(), 0)
        self.assertIsNone(stack.peek())

        # Further pop should raise StackUnderflowError
        with self.assertRaises(StackUnderflowError):
            stack.pop()

    def test_overflow_and_duplicate_prevention(self):
        stack = ParkingStack()
        # Stack is full (20 items). Trying to push an existing slot should raise ValueError
        with self.assertRaises(ValueError):
            stack.push(1)  # Already present in stack

        # Pop one, push it back
        s = stack.pop()
        self.assertEqual(stack.size(), 19)
        stack.push(s)
        self.assertEqual(stack.size(), 20)

        # Trying to push again raises duplicate error
        with self.assertRaises(ValueError):
            stack.push(s)

    def test_invalid_slot_validation(self):
        stack = ParkingStack()
        stack.pop()  # size is now 19
        with self.assertRaises(ValueError):
            stack.push(0)  # out of bounds
        with self.assertRaises(ValueError):
            stack.push(25)  # out of bounds

    def test_display_order(self):
        stack = ParkingStack([10, 5, 2])
        # Bottom is 10, middle is 5, TOP is 2
        self.assertEqual(stack.peek(), 2)
        self.assertEqual(stack.to_list(), [10, 5, 2])
        self.assertEqual(stack.to_display_list(), [2, 5, 10])  # top first


if __name__ == "__main__":
    unittest.main()
