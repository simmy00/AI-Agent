#!/usr/bin/env python3
"""Demonstration of hallucination prevention improvements"""
import os
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("GROQ_API_KEY")
if not api_key:
    print("ERROR: No API key configured")
    exit(1)

from agent import RetailAgent
from tools import RetailTools

# Patch to show tool responses
original_process = RetailAgent.process_tool_call
def debug_process(self, func_name, func_args):
    result = original_process(self, func_name, func_args)
    print(f"   🔧 Tool '{func_name}' returned status: '{result.get('status', 'unknown')}'")
    if 'error' in result:
        print(f"   ⚠️  Error code: {result['error']}")
        print(f"   📝 Message: {result.get('message', result.get('reason', 'N/A'))}...")
    return result

RetailAgent.process_tool_call = debug_process

tools = RetailTools('data/products.csv', 'data/orders.csv', 'data/policy.txt')
agent = RetailAgent(api_key=api_key, tools=tools)

print("=" * 70)
print("HALLUCINATION PREVENTION DEMO")
print("=" * 70)

# Scenario 1: Valid order
print("\n📌 SCENARIO 1: Valid Order (Should succeed)")
print("   Looking up order 0001")
try:
    response = agent.chat("order id = 0001", mode="unified")
    print(f"   ✓ Response: {response[:100]}...")
except Exception as e:
    print(f"   Error: {str(e)[:80]}...")

# Scenario 2: Invalid order (HALLUCINATION TEST)
print("\n📌 SCENARIO 2: Invalid Order 9999 (HALLUCINATION PREVENTION TEST)")
print("   Agent will receive 'NOT_FOUND' error")
print("   Agent should NOT make up order details")
try:
    response = agent.chat("where is order 9999?", mode="unified")
    
    # Check if response properly acknowledges missing data
    contains_error_phrase = any(phrase in response.lower() for phrase in [
        "not found", "not available", "can't find", "couldn't find",
        "verify the order", "check the order", "double-check"
    ])
    
    if contains_error_phrase:
        print(f"   ✓ GOOD: Agent properly reports missing data")
    else:
        print(f"   ⚠️  CHECK: Agent might be hallucinating")
    
    print(f"   📄 Response: {response[:120]}...")
    
except Exception as e:
    print(f"   Error: {str(e)[:80]}...")

print("\n" + "=" * 70)
print("END OF DEMO")
print("=" * 70)
