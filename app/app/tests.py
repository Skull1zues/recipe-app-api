"""
Sample tests
"""
from django.test import SimpleTestCase
from app import calc

class ClacTests(SimpleTestCase):
    """Test the clac module."""

    def test_add_numbers(self):
        res=calc.add(5,8)
        self.assertEqual(res, 13)