"""Offline verification script — tests tools and data without API key"""
from tools import RetailTools

tools = RetailTools('data/products.csv', 'data/orders.csv', 'data/policy.txt')

print("=" * 60)
print("  OFFLINE VERIFICATION")
print("=" * 60)

# 1. Policy parsing
print("\n--- Policy Rules Parsed ---")
for key, value in tools.policy_rules.items():
    print(f"  {key}: {value}")

# 2. Product search
print("\n--- Search: modest evening gowns under 300, size 8, on sale ---")
results = tools.search_products({
    'tags': ['modest', 'evening'],
    'max_price': 300,
    'size': '8',
    'is_sale': True,
    'limit': 5
})
for p in results:
    pid = p['product_id']
    title = p['title']
    price = p['price']
    score = p['bestseller_score']
    print(f"  {pid} | {title} | price={price} | score={score}")
if not results:
    print("  No results found.")

# 3. Professional work dress search
print("\n--- Search: work/professional with sleeves, size 10, under 200 ---")
results2 = tools.search_products({
    'tags': ['work', 'professional', 'sleeve'],
    'max_price': 200,
    'size': '10',
    'limit': 5
})
for p in results2:
    pid = p['product_id']
    title = p['title']
    price = p['price']
    vendor = p['vendor']
    print(f"  {pid} | {title} | price={price} | vendor={vendor}")
if not results2:
    print("  No results found.")

# 4. Order lookup
print("\n--- Order Lookup: O0005 ---")
order = tools.get_order('O0005')
if order:
    print(f"  order_id: {order['order_id']}")
    print(f"  product_id: {order['product_id']}")
    print(f"  order_date: {order['order_date']}")
    print(f"  size: {order['size']}")
    print(f"  price_paid: {order['price_paid']}")
    if 'product_info' in order:
        pi = order['product_info']
        print(f"  product_title: {pi.get('title', 'N/A')}")
        print(f"  is_sale: {pi.get('is_sale', 'N/A')}")
        print(f"  is_clearance: {pi.get('is_clearance', 'N/A')}")
        print(f"  vendor: {pi.get('vendor', 'N/A')}")
else:
    print("  Order not found!")

# 5. Return evaluation — regular item
print("\n--- Return Evaluation: O0005 (Regular Item) ---")
ret = tools.evaluate_return('O0005')
for key, value in ret.items():
    print(f"  {key}: {value}")

# 6. Return evaluation — clearance item
print("\n--- Return Evaluation: O0012 (Clearance Item) ---")
ret2 = tools.evaluate_return('O0012')
for key, value in ret2.items():
    print(f"  {key}: {value}")

# 7. Return evaluation — invalid order
print("\n--- Return Evaluation: O9999 (Invalid Order) ---")
ret3 = tools.evaluate_return('O9999')
for key, value in ret3.items():
    print(f"  {key}: {value}")

# 8. Return evaluation — Aurelia Couture vendor exception
print("\n--- Return Evaluation: O0003 (Aurelia Couture) ---")
ret4 = tools.evaluate_return('O0003')
for key, value in ret4.items():
    print(f"  {key}: {value}")

# 9. Return evaluation — Nocturne vendor exception
print("\n--- Return Evaluation: O0002 (Nocturne) ---")
ret5 = tools.evaluate_return('O0002')
for key, value in ret5.items():
    print(f"  {key}: {value}")

print("\n" + "=" * 60)
print("  ALL VERIFICATIONS COMPLETE")
print("=" * 60)
