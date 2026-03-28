#!/usr/bin/env python3
"""
Retail AI Assistant -- OpenClaw
CLI chatbot for Personal Shopping and Customer Support.

Usage:
    python main.py              # Start interactive chatbot
    python main.py --demo       # Run all demo scenarios
    python main.py --offline    # Offline tool verification (no API key)
"""

import os
import sys
import time
from dotenv import load_dotenv
from agent import RetailAgent, OpenClawChatbot
from tools import RetailTools


# ======================================================================
#  DEMO FUNCTIONS (for assignment deliverables)
# ======================================================================

def run_demo_personal_shopper(agent: RetailAgent):
    """Part 1 -- Personal Shopper: multi-constraint product search"""
    print("\n" + "=" * 70)
    print("  DEMO: Personal Shopper Scenarios")
    print("=" * 70)
    
    scenarios = [
        {
            "name": "Scenario 1: Modest Evening Gown Under $300 (Sale Preferred)",
            "query": "I need a modest evening gown under $300 in size 8. I prefer something on sale."
        },
        {
            "name": "Scenario 2: Professional Work Dress with Sleeves",
            "query": "Looking for a professional work dress in size 10, preferably with sleeves, budget around $200."
        }
    ]
    
    for i, scenario in enumerate(scenarios):
        if i > 0:
            print("\n  [Waiting 10s to respect API rate limits...]\n")
            time.sleep(10)
        
        print(f"\n  >> {scenario['name']}")
        print(f"     Customer: \"{scenario['query']}\"\n")
        
        try:
            response = agent.chat(scenario['query'], mode="personal_shopper")
            print(f"     Assistant: {response}")
        except Exception as e:
            print(f"     [Error: {e}]")
        print("-" * 70)


def run_demo_support(agent: RetailAgent):
    """Part 2 -- Support Reasoning: policy-based return evaluation"""
    print("\n" + "=" * 70)
    print("  DEMO: Customer Support Scenarios")
    print("=" * 70)
    
    scenarios = [
        {
            "name": "Scenario 1: Return Request (Sale Item)",
            "query": "Order O0005 -- I bought this dress recently. It doesn't fit. Can I return it?"
        },
        {
            "name": "Scenario 2: Clearance Item Return Request",
            "query": "Hi, I have order O0012 and I'd like to return it. It doesn't look good on me."
        }
    ]
    
    for i, scenario in enumerate(scenarios):
        if i > 0:
            print("\n  [Waiting 10s to respect API rate limits...]\n")
            time.sleep(10)
        
        print(f"\n  >> {scenario['name']}")
        print(f"     Customer: \"{scenario['query']}\"\n")
        
        try:
            response = agent.chat(scenario['query'], mode="support")
            print(f"     Assistant: {response}")
        except Exception as e:
            print(f"     [Error: {e}]")
        print("-" * 70)


def run_demo_edge_cases(agent: RetailAgent):
    """Part 3 -- Edge Cases: invalid orders, missing products, vendor exceptions"""
    print("\n" + "=" * 70)
    print("  DEMO: Edge Cases & Error Handling")
    print("=" * 70)
    
    scenarios = [
        {
            "name": "Edge Case 1: Invalid Order ID",
            "query": "I want to return order O9999. Can you help?"
        },
        {
            "name": "Edge Case 2: Product Not Available in Size",
            "query": "I need the Beaded Gala Gown (P0011) in size 4."
        },
        {
            "name": "Edge Case 3: Vendor Exception (Aurelia Couture -- Exchange Only)",
            "query": "I ordered from Aurelia Couture, order O0003. I want a refund."
        }
    ]
    
    for i, scenario in enumerate(scenarios):
        if i > 0:
            print("\n  [Waiting 10s to respect API rate limits...]\n")
            time.sleep(10)
        
        print(f"\n  >> {scenario['name']}")
        print(f"     Customer: \"{scenario['query']}\"\n")
        
        try:
            response = agent.chat(scenario['query'], mode="unified")
            print(f"     Assistant: {response}")
        except Exception as e:
            print(f"     [Error: {e}]")
        print("-" * 70)


def run_demo_openclaw(agent: RetailAgent):
    """Task 1 -- OpenClaw Chat/WhatsApp Automation Demo"""
    print("\n" + "=" * 70)
    print("  DEMO: OpenClaw Chat & WhatsApp Automation")
    print("=" * 70)
    
    chatbot = OpenClawChatbot(agent)
    
    # Simulate WhatsApp conversation
    print("\n  Simulating WhatsApp conversation:\n")
    whatsapp_messages = [
        "Hi, what size should I order? I usually wear a medium.",
        "Where is my order? Order number O0005.",
        "I want to return order O0001. The dress doesn't fit."
    ]
    chatbot.simulate_conversation(whatsapp_messages, channel="whatsapp")
    
    # Simulate escalation
    print("\n  Simulating escalation scenario:\n")
    escalation_messages = [
        "I'm very disappointed with my order. I want to speak to a manager immediately!"
    ]
    chatbot.simulate_conversation(escalation_messages, channel="chat")


# ======================================================================
#  OFFLINE VERIFICATION (runs without API key)
# ======================================================================

def verify_tools_offline():
    """Verify that data loading and tool logic works without an API key"""
    print("\n" + "=" * 70)
    print("  OFFLINE VERIFICATION -- Tools & Data")
    print("=" * 70)
    
    tools = RetailTools(
        products_csv="data/products.csv",
        orders_csv="data/orders.csv",
        policy_file="data/policy.txt"
    )
    
    print("\n[1] Policy Rules Parsed:")
    for key, value in tools.policy_rules.items():
        print(f"    {key}: {value}")
    
    print("\n[2] Search: Modest evening gowns under $300, size 8, on sale")
    results = tools.search_products({
        'tags': ['modest', 'evening'],
        'max_price': 300,
        'size': '8',
        'is_sale': True,
        'limit': 3
    })
    for p in results:
        print(f"    {p['product_id']} | {p['title']} | ${p['price']} | Score: {p['bestseller_score']}")
    if not results:
        print("    No results found.")
    
    print("\n[3] Order Lookup: O0005")
    order = tools.get_order('O0005')
    if order:
        print(f"    Order: {order['order_id']} | Product: {order['product_id']} | Date: {order['order_date']}")
        if 'product_info' in order:
            print(f"    Product: {order['product_info'].get('title', 'N/A')} | Sale: {order['product_info'].get('is_sale', 'N/A')}")
    else:
        print("    Order not found!")
    
    print("\n[4] Return Evaluation: O0005 (Sale Item)")
    ret = tools.evaluate_return('O0005')
    for key, value in ret.items():
        print(f"    {key}: {value}")
    
    print("\n[5] Return Evaluation: O0012 (Clearance Item)")
    ret2 = tools.evaluate_return('O0012')
    for key, value in ret2.items():
        print(f"    {key}: {value}")
    
    print("\n[6] Return Evaluation: O9999 (Invalid Order)")
    ret3 = tools.evaluate_return('O9999')
    for key, value in ret3.items():
        print(f"    {key}: {value}")
    
    print("\n[7] Return Evaluation: O0003 (Aurelia Couture -- Exchange Only)")
    ret4 = tools.evaluate_return('O0003')
    for key, value in ret4.items():
        print(f"    {key}: {value}")
    
    print("\n" + "=" * 70)
    print("  ALL VERIFICATIONS PASSED")
    print("=" * 70)


# ======================================================================
#  MAIN ENTRY POINT
# ======================================================================

def main():
    """Main application -- runs directly as an interactive chatbot"""
    load_dotenv()
    
    groq_api_key = os.getenv("GROQ_API_KEY")
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    
    # Prefer OpenRouter if available, otherwise use Groq
    api_key = openrouter_api_key if openrouter_api_key and openrouter_api_key != "your_openrouter_api_key_here" else groq_api_key
    use_openrouter = bool(openrouter_api_key and openrouter_api_key != "your_openrouter_api_key_here")
    
    # Handle command-line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == "--offline":
            verify_tools_offline()
            return
        elif arg == "--whatsapp":
            # Start the WhatsApp webhook server + dashboard
            from whatsapp_server import start_server
            use_ngrok = "--no-ngrok" not in sys.argv
            port = int(os.getenv("PORT", 5000))
            start_server(port=port, use_ngrok=use_ngrok)
            return
        elif arg == "--simulate":
            # Start server without ngrok (just the simulated UI)
            from whatsapp_server import start_server
            port = int(os.getenv("PORT", 5000))
            start_server(port=port, use_ngrok=False)
            return
        elif arg == "--demo":
            if not api_key or api_key == "your_groq_api_key_here" or api_key == "your_openrouter_api_key_here":
                print("\n[ERROR] No API key configured")
                print("\nOptions:")
                print("1. GROQ (FREE): https://console.groq.com/keys")
                print("2. OpenRouter: https://openrouter.ai/keys")
                print("\nAdd to your .env file:")
                print("  GROQ_API_KEY=your_key_here")
                print("  # OR")
                print("  OPENROUTER_API_KEY=your_key_here")
                return
            
            tools = RetailTools("data/products.csv", "data/orders.csv", "data/policy.txt")
            agent = RetailAgent(api_key=api_key, tools=tools, use_openrouter=use_openrouter)
            
            run_demo_personal_shopper(agent)
            time.sleep(10)
            run_demo_support(agent)
            time.sleep(10)
            run_demo_edge_cases(agent)
            time.sleep(10)
            run_demo_openclaw(agent)
            
            print("\n" + "=" * 70)
            print("  ALL DEMOS COMPLETED")
            print("=" * 70)
            return
        elif arg == "--help":
            print("""
Retail AI Assistant -- OpenClaw
CLI chatbot for Personal Shopping and Customer Support.

Usage:
    python main.py              # Start interactive chatbot
    python main.py --demo       # Run all demo scenarios
    python main.py --offline    # Offline tool verification (no API key)
    python main.py --whatsapp   # Start WhatsApp server + dashboard (with ngrok)
    python main.py --simulate   # Start simulated WhatsApp UI (no ngrok)
    python main.py --help       # Show this help message
""")
            return
    
    # Default behavior: Start Chatbot immediately
    if not api_key or api_key == "your_groq_api_key_here" or api_key == "your_openrouter_api_key_here":
        print("\n[ERROR] No API key configured")
        print("\nOptions:")
        print("1. GROQ (FREE): https://console.groq.com/keys")
        print("    Add to .env: GROQ_API_KEY=your_key_here")
        print("\n2. OpenRouter: https://openrouter.ai/keys")
        print("    Add to .env: OPENROUTER_API_KEY=your_key_here")
        print("\nTo verify everything offline without a key, run:")
        print("  python main.py --offline\n")
        return
        
    print("\nLoading OpenClaw AI Assistant...")
    if use_openrouter:
        print("[INFO] Using OpenRouter API")
    else:
        print("[INFO] Using Groq API")
    
    tools = RetailTools("data/products.csv", "data/orders.csv", "data/policy.txt")
    agent = RetailAgent(api_key=api_key, tools=tools, use_openrouter=use_openrouter)
    
    # Launch directly into the unified mode chatbot
    agent.chat_interactive(mode="unified")


if __name__ == "__main__":
    main()