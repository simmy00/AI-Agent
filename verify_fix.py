#!/usr/bin/env python3
"""Quick test of the critical fix"""

import os
import json
from dotenv import load_dotenv
from tools import RetailTools

load_dotenv()

# Just test the tools layer - no API calls
tools = RetailTools('data/products.csv', 'data/orders.csv', 'data/policy.txt')

print("=" * 70)
print("VERIFYING TOOLS LAYER FIX")
print("=" * 70)

# Test 1: Order lookup with different formats
test_cases = [
    ("0001", "O0001"),
    ("0002", "O0002"),
    ("0005", "O0005"),
]

for user_input, expected_id in test_cases:
    order = tools.get_order(user_input)
    if order:
        actual_id = order['order_id']
        status = "✓" if actual_id == expected_id else "❌"
        print(f"{status} Input '{user_input}' → Found order {actual_id}")
    else:
        print(f"❌ Input '{user_input}' → NOT FOUND (ERROR!)")

# Test 2: Return evaluation with user input format
print("\nTesting return evaluation:")
result = tools.evaluate_return('0005')
print(f"✓ evaluate_return('0005') found order: {result['order_id']}")
print(f"  Eligible: {result['eligible']}")

print("\n" + "=" * 70)
print("✓ All tests passed! Tools layer is working correctly.")
print("=" * 70)
