import pandas as pd
from typing import Dict, List, Optional, Any
import json
import re
from datetime import datetime


class RetailTools:
    """Core tools for the retail AI assistant"""
    
    def __init__(self, products_csv: str, orders_csv: str, policy_file: str):
        """Initialize with data files"""
        self.products_df = pd.read_csv(products_csv)
        self.orders_df = pd.read_csv(orders_csv)
        
        # Ensure order_id is treated as string
        self.orders_df['order_id'] = self.orders_df['order_id'].astype(str).str.strip()
        self.products_df['product_id'] = self.products_df['product_id'].astype(str).str.strip()
        
        with open(policy_file, 'r') as f:
            self.policy_text = f.read()
        
        # Parse policy into structured rules
        self.policy_rules = self._parse_policy()
    
    def _parse_policy(self) -> Dict:
        """Parse policy text into structured rules based on actual policy.txt format"""
        rules = {
            'normal_return_days': 14,
            'sale_return_days': 7,
            'sale_refund_type': 'store_credit',
            'clearance_returnable': False,
            'vendor_exceptions': {},
            'exchange_allowed': True,
            'exchange_condition': 'stock_available',
            'return_shipping': 'customer_pays'
        }
        
        text = self.policy_text
        
        # Extract normal return days: "Returns accepted within X days"
        normal_match = re.search(r'returns?\s+accepted\s+within\s+(\d+)\s+days', text, re.IGNORECASE)
        if normal_match:
            rules['normal_return_days'] = int(normal_match.group(1))
        
        # Extract sale return days: "Returnable within X days"
        sale_match = re.search(r'returnable\s+within\s+(\d+)\s+days', text, re.IGNORECASE)
        if sale_match:
            rules['sale_return_days'] = int(sale_match.group(1))
        
        # Check sale refund type
        if 'store credit only' in text.lower():
            rules['sale_refund_type'] = 'store_credit'
        
        # Clearance policy: "Final sale" or "Not eligible for return"
        if 'final sale' in text.lower() or 'not eligible for return' in text.lower():
            rules['clearance_returnable'] = False
        
        # Vendor exceptions
        # Pattern: "VendorName: description"
        vendor_section = text.split('Vendor Exceptions:')
        if len(vendor_section) > 1:
            vendor_text = vendor_section[1].split('\n\n')[0]  # Get until next section
            vendor_lines = [l.strip() for l in vendor_text.strip().split('\n') if ':' in l and l.strip()]
            for line in vendor_lines:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    vendor_name = parts[0].strip()
                    vendor_rule = parts[1].strip().lower()
                    
                    if 'exchanges only' in vendor_rule or 'no refunds' in vendor_rule:
                        rules['vendor_exceptions'][vendor_name] = {
                            'type': 'exchange_only',
                            'refund_allowed': False
                        }
                    
                    extended_match = re.search(r'(\d+)\s*days', vendor_rule)
                    if extended_match:
                        if vendor_name not in rules['vendor_exceptions']:
                            rules['vendor_exceptions'][vendor_name] = {}
                        rules['vendor_exceptions'][vendor_name]['return_days'] = int(extended_match.group(1))
        
        # Exchange rules
        if 'size exchanges allowed' in text.lower():
            rules['exchange_allowed'] = True
        if 'customer pays return shipping' in text.lower():
            rules['return_shipping'] = 'customer_pays'
        if 'unless defective' in text.lower():
            rules['defective_shipping'] = 'store_pays'
        
        return rules
    
    def search_products(self, filters: Dict[str, Any]) -> List[Dict]:
        """
        Search products based on filters
        
        Args:
            filters: Dict with keys like:
                - max_price: float
                - min_price: float
                - tags: list of tag values
                - size: str (e.g., "8")
                - is_sale: bool
                - is_clearance: bool
                - vendor: str
                - limit: int (max results)
        
        Returns:
            List of matching products
        """
        df = self.products_df.copy()
        
        # Apply price filters
        if 'max_price' in filters:
            df = df[df['price'] <= filters['max_price']]
        
        if 'min_price' in filters:
            df = df[df['price'] >= filters['min_price']]
        
        # Apply vendor filter
        if 'vendor' in filters:
            df = df[df['vendor'].str.lower() == filters['vendor'].lower()]
        
        if 'size' in filters:
            size = str(filters['size']).strip()
            
            # Use word-boundary matching to avoid "8" matching "18"
            def size_available(row):
                sizes = str(row['sizes_available'])
                # Split by comma and check exact match
                size_list = [s.strip() for s in sizes.split(',')]
                return size in size_list
            
            df = df[df.apply(size_available, axis=1)]
            
            # Check stock for that size
            def has_stock(row):
                try:
                    stock_str = str(row['stock_per_size']).replace("'", '"')
                    stock_dict = json.loads(stock_str)
                    return stock_dict.get(size, 0) > 0
                except (json.JSONDecodeError, AttributeError):
                    return False
            
            df = df[df.apply(has_stock, axis=1)]
        
        if 'tags' in filters:
            tag_list = filters['tags']
            def matches_tags(row):
                row_tags = str(row['tags']).lower()
                return any(tag.lower() in row_tags for tag in tag_list)
            
            df = df[df.apply(matches_tags, axis=1)]
        
        if 'is_sale' in filters and filters['is_sale']:
            df = df[df['is_sale'] == True]
        
        if 'is_clearance' in filters and filters['is_clearance']:
            df = df[df['is_clearance'] == True]
        
        # Sort: sale items first (if sale preference), then by bestseller score
        if 'bestseller_score' in df.columns:
            if 'is_sale' in filters and filters['is_sale']:
                df = df.sort_values(['is_sale', 'bestseller_score'], ascending=[False, False])
            else:
                df = df.sort_values('bestseller_score', ascending=False)
        
        # Limit results
        limit = filters.get('limit', 10)
        df = df.head(limit)
        
        if len(df) == 0:
            return []
        
        return df.to_dict('records')
    
    def get_product(self, product_id: str) -> Optional[Dict]:
        """
        Get specific product by ID
        
        Args:
            product_id: Product identifier
        
        Returns:
            Product dict or None if not found
        """
        product_id = str(product_id).strip()
        result = self.products_df[self.products_df['product_id'] == product_id]
        
        if len(result) == 0:
            return None
        
        return result.iloc[0].to_dict()
    
    def get_order(self, order_id: str) -> Optional[Dict]:
        """
        Get order information by ID
        
        Args:
            order_id: Order identifier (format: O0001, O0002, etc. or just 0001)
        
        Returns:
            Order dict with product info, or None if not found
        """
        order_id = str(order_id).strip()
        
        # Try exact match first
        result = self.orders_df[self.orders_df['order_id'] == order_id]
        
        # If no match and order_id doesn't start with 'O', try adding it
        if len(result) == 0 and not order_id.upper().startswith('O'):
            order_id_with_prefix = 'O' + order_id
            result = self.orders_df[self.orders_df['order_id'] == order_id_with_prefix]
        
        if len(result) == 0:
            return None
        
        order = result.iloc[0].to_dict()
        
        # Enrich with product information
        product = self.get_product(order['product_id'])
        if product:
            order['product_info'] = product
        
        return order
    
    def evaluate_return(self, order_id: str) -> Dict:
        """
        Evaluate if an order is eligible for return based on store policies
        
        Args:
            order_id: Order identifier (format: O0001, O0002, etc. or just 0001)
        
        Returns:
            Dict with eligibility details
        """
        try:
            order = self.get_order(order_id)
            
            if not order:
                return {
                    'eligible': False,
                    'error': 'NOT_FOUND',
                    'status': 'not_found',
                    'reason': f'Order "{order_id}" not found in our system. Please verify the order ID and try again.',
                    'days_since_order': None,
                    'policy_applied': None,
                    'refund_type': None
                }
            
            # Calculate days since order
            order_date = pd.to_datetime(order['order_date'])
            days_since = (datetime.now() - order_date).days
            
            # Get product info
            product = order.get('product_info', {})
            is_sale = product.get('is_sale', False)
            is_clearance = product.get('is_clearance', False)
            vendor = product.get('vendor', '')
            product_title = product.get('title', 'Unknown Product')
            
            result = {
                'order_id': order['order_id'],
                'product_title': product_title,
                'order_date': str(order['order_date']),
                'days_since_order': days_since,
                'is_sale': is_sale,
                'is_clearance': is_clearance,
                'vendor': vendor
            }
            
            # Check clearance first
            if is_clearance and not self.policy_rules['clearance_returnable']:
                result.update({
                    'eligible': False,
                    'reason': 'Clearance items are final sale and not eligible for return or exchange',
                    'policy_applied': 'clearance_policy',
                    'refund_type': None
                })
                return result
            
            # Check vendor exceptions
            if vendor in self.policy_rules['vendor_exceptions']:
                vendor_rule = self.policy_rules['vendor_exceptions'][vendor]
                
                # Vendor with exchange-only policy
                if vendor_rule.get('type') == 'exchange_only':
                    vendor_days = vendor_rule.get('return_days', self.policy_rules['normal_return_days'])
                    if days_since <= vendor_days:
                        result.update({
                            'eligible': True,
                            'reason': f'{vendor} policy: exchanges only, no refunds. Within {vendor_days}-day window ({days_since} days since order)',
                            'policy_applied': f'vendor_exception_{vendor}',
                            'refund_type': 'exchange_only'
                        })
                    else:
                        result.update({
                            'eligible': False,
                            'reason': f'Outside {vendor_days}-day exchange window for {vendor} ({days_since} days since order)',
                            'policy_applied': f'vendor_exception_{vendor}',
                            'refund_type': None
                        })
                    return result
                
                # Vendor with extended return window
                if 'return_days' in vendor_rule:
                    max_days = vendor_rule['return_days']
                    if days_since <= max_days:
                        result.update({
                            'eligible': True,
                            'reason': f'{vendor} extended return policy: within {max_days}-day window ({days_since} days since order)',
                            'policy_applied': f'vendor_exception_{vendor}',
                            'refund_type': 'full_refund'
                        })
                    else:
                        result.update({
                            'eligible': False,
                            'reason': f'Outside {max_days}-day return window for {vendor} ({days_since} days since order)',
                            'policy_applied': f'vendor_exception_{vendor}',
                            'refund_type': None
                        })
                    return result
            
            # Standard return policy
            if is_sale:
                max_days = self.policy_rules['sale_return_days']
                policy_name = 'sale_return_policy'
                refund_type = self.policy_rules.get('sale_refund_type', 'store_credit')
            else:
                max_days = self.policy_rules['normal_return_days']
                policy_name = 'normal_return_policy'
                refund_type = 'full_refund'
            
            if days_since <= max_days:
                result.update({
                    'eligible': True,
                    'reason': f'Within {max_days}-day return window ({days_since} days since order). Refund type: {refund_type}',
                    'policy_applied': policy_name,
                    'refund_type': refund_type
                })
            else:
                result.update({
                    'eligible': False,
                    'reason': f'Outside {max_days}-day return window ({days_since} days since order)',
                    'policy_applied': policy_name,
                    'refund_type': None
                })
            
            return result
        
        except Exception as e:
            # Catch any unexpected errors and return a safe response
            return {
                'eligible': False,
                'error': 'SYSTEM_ERROR',
                'status': 'error',
                'reason': f'Unable to evaluate return eligibility: {str(e)}. Please contact our support team.',
                'days_since_order': None,
                'policy_applied': None,
                'refund_type': None
            }


# Tool definitions for product search, browsing, and order management
TOOL_DEFINITIONS = [
    {
        "name": "search_products",
        "description": "Search for products in the inventory based on filter criteria (price, size, tags, vendor, sale/clearance status). Returns a list of matching products.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filters": {
                    "type": "object",
                    "properties": {
                        "max_price": {
                            "type": "number",
                            "description": "Maximum price (e.g., 300)"
                        },
                        "min_price": {
                            "type": "number",
                            "description": "Minimum price"
                        },
                        "tags": {
                            "type": "array",
                            "description": "List of tags to filter by (e.g., ['modest', 'evening', 'formal', 'sleeve', 'fitted'])"
                        },
                        "size": {
                            "type": "string",
                            "description": "Size needed (e.g., '6', '8', '10', '12', '14', '16')"
                        },
                        "is_sale": {
                            "type": "boolean",
                            "description": "Filter for sale items only"
                        },
                        "is_clearance": {
                            "type": "boolean",
                            "description": "Filter for clearance items only"
                        },
                        "vendor": {
                            "type": "string",
                            "description": "Filter by vendor name"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 10)"
                        }
                    },
                    "description": "Filter criteria for product search"
                }
            },
            "required": ["filters"]
        }
    },
    {
        "name": "get_product",
        "description": "Retrieve detailed information about a specific product by its product_id (e.g., 'P0001'). DO NOT guess or invent a product ID. If you need a product ID but don't have one, ask the user. Use this when you need full details.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "The unique product identifier (format: P0001, P0002, etc.)"
                }
            },
            "required": ["product_id"]
        }
    },
    {
        "name": "get_order",
        "description": "Retrieve information about a customer's order by order_id (e.g., 'O0001'). DO NOT INVENT OR GUESS THE ORDER ID. If the user asks about an order but doesn't provide the ID, you MUST ask them for their order number first. Do not call this tool without a real order ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The unique order identifier (format: O0001, O0002, etc.)"
                }
            },
            "required": ["order_id"]
        }
    },
    {
        "name": "evaluate_return",
        "description": "Evaluate whether an order is eligible for return based on store policies. DO NOT INVENT OR GUESS THE ORDER ID. If the user asks about returning an item but hasn't provided the order ID, ask them for the order number first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID to evaluate for return eligibility (format: O0001, O0002, etc.)"
                }
            },
            "required": ["order_id"]
        }
    }
]