# Retail AI Assistant - Architecture Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Design](#architecture-design)
3. [Hallucination Prevention](#hallucination-prevention)
4. [Tool Selection Strategy](#tool-selection-strategy)
5. [OpenClaw Integration](#openclaw-integration)
6. [Technical Implementation](#technical-implementation)

---

## System Overview

The Retail AI Assistant is an agentic system that combines two specialized roles:
- **Personal Shopper**: Helps customers discover products based on preferences
- **Customer Support**: Handles order inquiries and return/exchange requests

The system uses Groq Llama 3 with function calling to ensure accurate, data-driven responses while preventing hallucination.

### Key Features
✅ Multi-constraint product search with stock awareness  
✅ Policy-based return evaluation  
✅ Automatic tool selection via Groq's native function calling  
✅ Hallucination prevention through strict tool-only data access  
✅ OpenClaw integration for automated chat/WhatsApp responses  

---

## Architecture Design

### Design Philosophy

**Why This Architecture?**

We chose a **tool-based agentic architecture** for several critical reasons:

1. **Separation of Concerns**
   - **Data Layer** (tools.py): Pure data access functions
   - **Agent Layer** (agent.py): LLM reasoning and orchestration
   - **Presentation Layer** (main.py): User interface

2. **Reliability Through Constraints**
   - LLM cannot make up data - must use tools
   - Tools return structured, validated data
   - Clear success/failure states (None for not found)

3. **Extensibility**
   - Adding new data sources = adding new tools
   - No changes to agent logic needed
   - Tools can be versioned and tested independently

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        User Interface                        │
│                      (CLI / Interactive)                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                      Retail Agent                            │
│  ┌────────────────────────────────────────────────────┐     │
│  │   Groq Llama 3 (Function Calling)                 │     │
│  │   - Interprets user intent                         │     │
│  │   - Selects appropriate tools                      │     │
│  │   - Reasons over tool results                      │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                       Tool Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   search_    │  │  get_order   │  │  evaluate_   │      │
│  │   products   │  │              │  │   return     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐                                           │
│  │ get_product  │                                           │
│  └──────────────┘                                           │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                       Data Layer                             │
│    products.csv  │  orders.csv  │  policy.txt               │
└─────────────────────────────────────────────────────────────┘
```

### Agentic Loop

The agent operates in a **loop-until-answer** pattern:

```python
1. User sends message
2. Agent receives message + available tools
3. Agent decides: 
   - Call tool(s) → Execute → Return to step 2
   - OR respond with text → End
4. User receives final response
```

This allows the agent to:
- Chain multiple tool calls (e.g., get_order → get_product → evaluate_return)
- Gather information progressively
- Make decisions based on accumulated data

---

## Hallucination Prevention

### The Hallucination Problem

LLMs can "hallucinate" - generate plausible-sounding but false information. In retail, this is catastrophic:
- Recommending out-of-stock products
- Approving invalid returns
- Citing non-existent policies

### Our Prevention Strategy

**1. Tool-Only Data Access**

```python
# System prompt enforces this rule:
"NEVER make up product information - only use data from tools"
"NEVER hallucinate order or policy information"
```

The agent literally cannot access product/order data without calling tools.

**2. Explicit None Handling**

```python
def get_product(product_id: str) -> Optional[Dict]:
    result = self.products_df[self.products_df['product_id'] == product_id]
    if len(result) == 0:
        return None  # Explicit "not found"
    return result.iloc[0].to_dict()
```

Tools return `None` for missing data, forcing the agent to acknowledge gaps.

**3. Structured Tool Responses**

```python
{
    "eligible": False,
    "reason": "Outside 14-day return window (25 days since order)",
    "days_since_order": 25,
    "policy_applied": "sale_policy"
}
```

Tools return structured data with clear semantics. No ambiguity.

**4. Validation at Tool Level**

```python
# Size availability check
def has_stock(row):
    stock_dict = json.loads(row['stock_per_size'])
    return stock_dict.get(size, 0) > 0

df = df[df.apply(has_stock, axis=1)]
```

Business logic lives in tools, not in LLM reasoning.

**5. Error Propagation**

```python
if not order:
    return {
        'eligible': False,
        'reason': 'Order not found',
        'days_since_order': None,
        'policy_applied': None
    }
```

Errors are explicit, not hidden.

### Testing Hallucination Prevention

We include edge cases to verify:
- Invalid order IDs → Agent says "Order not found", doesn't guess
- Unavailable sizes → Agent says "Not in stock", doesn't recommend anyway
- Missing products → Agent acknowledges gap, doesn't invent alternatives

---

## Tool Selection Strategy

### How Tools Are Selected

Groq uses **native function calling** to decide which tools to use. We don't hardcode rules.

**Tool Definitions Include:**
1. **Name**: `search_products`, `get_order`, etc.
2. **Description**: When to use this tool
3. **Schema**: Required/optional parameters

Example:
```python
{
    "name": "search_products",
    "description": "Search for products in inventory based on filters. 
                    Use when customer is looking for recommendations.",
    "input_schema": {
        "type": "object",
        "properties": {
            "filters": {
                "type": "object",
                "properties": {
                    "max_price": {"type": "number"},
                    "size": {"type": "string"},
                    "tags": {"type": "array"},
                    # ... more filters
                }
            }
        }
    }
}
```

### Decision Examples

**User**: "I need a modest evening gown under $300 in size 8"

**Agent Reasoning**:
1. Customer wants product recommendations
2. Has specific constraints: price, tags, size
3. **Calls**: `search_products(filters={max_price: 300, tags: ["modest", "evening"], size: "8"})`

**User**: "Order 1043 — Can I return it?"

**Agent Reasoning**:
1. Customer asking about return eligibility
2. Mentions specific order ID
3. **Calls**: `evaluate_return(order_id="1043")`

### Multi-Step Reasoning

For complex queries, the agent chains tools:

**User**: "I bought a dress last week, order 1043. It doesn't fit. Can I return it?"

**Agent Steps**:
1. Calls `get_order("1043")` → Gets order details
2. Sees product is on sale
3. Calls `evaluate_return("1043")` → Checks policy
4. Returns decision with explanation

### Why This Approach Works

✅ **Flexible**: Agent adapts to varied phrasings  
✅ **Accurate**: Always uses correct tool for task  
✅ **Transparent**: Tool calls are visible and debuggable  
✅ **Maintainable**: Adding tools doesn't require retraining  

---

## OpenClaw Integration

### Purpose

OpenClaw provides **automated first-response** for customer-facing channels (chat, WhatsApp).

### Architecture

```
Customer Message
    ↓
Classify Inquiry Type
    ↓
┌─────────┬──────────┬─────────┬──────────┐
│ Sizing  │  Order   │ General │ Escalate │
│         │  Status  │   FAQ   │          │
└─────────┴──────────┴─────────┴──────────┘
    ↓         ↓          ↓          ↓
  Agent     Agent      Agent    Route to
 Response  Response  Response    Human
```

### Features

**1. Inquiry Classification**

```python
def classify_inquiry(message: str) -> str:
    if 'speak to human' in message:
        return "escalate"
    if 'size' in message:
        return "sizing"
    if 'order' in message:
        return "order_status"
    return "general"
```

**2. Automatic Routing**

```python
if inquiry_type == "escalate":
    return {
        "action": "route_to_human",
        "response": "Connecting you with an agent..."
    }
```

**3. Channel Support**

Handles both:
- **Web Chat**: Real-time messaging
- **WhatsApp**: Asynchronous messaging

**4. Response Formatting**

Responses are professional and context-aware:
- Sizing: Provides measurement guide or product-specific info
- Order Status: Looks up order and provides tracking details
- General: Answers FAQs or routes appropriately

### Benefits

✅ **24/7 Availability**: No human needed for common queries  
✅ **Fast Response**: Instant replies to customer messages  
✅ **Smart Escalation**: Complex issues go to humans  
✅ **Consistent Quality**: Same professional tone always  

---

## Technical Implementation

### Technology Stack

- **Language**: Python 3.10+
- **LLM Provider**: Groq (via API - FREE tier)
- **Model**: llama-3.3-70b-versatile
- **Data Processing**: Pandas
- **Environment Management**: python-dotenv

### Key Files

```
retail-ai-assistant/
├── main.py              # CLI application & demos
├── agent.py             # RetailAgent & OpenClawChatbot classes
├── tools.py             # Tool implementations & definitions
├── requirements.txt     # Python dependencies
├── .env                 # API keys (not in repo)
├── data/
│   ├── products.csv     # Product inventory
│   ├── orders.csv       # Customer orders
│   └── policy.txt       # Return/exchange policies
└── ARCHITECTURE.md      # This document
```

### Setup Instructions

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up API key
echo "GROQ_API_KEY=your_key_here" > .env

# 3. Run application
python main.py
```

### Extending the System

**Adding a New Tool:**

1. Implement function in `tools.py`:
```python
def check_inventory_location(self, product_id: str) -> Dict:
    # Your logic here
    pass
```

2. Add tool definition:
```python
{
    "name": "check_inventory_location",
    "description": "Check which warehouse has a product",
    "input_schema": {...}
}
```

3. Add to `process_tool_call()`:
```python
elif tool_name == "check_inventory_location":
    return self.tools.check_inventory_location(tool_input['product_id'])
```

That's it! Groq will automatically use it when appropriate.

### Performance Considerations

- **Latency**: 2-5 seconds per response (includes LLM + tool execution)
- **Cost**: FREE (Groq Free Tier)
- **Scalability**: Stateless design allows horizontal scaling

### Security & Privacy

- API keys stored in environment variables
- No customer data logged by default
- Tools validate all inputs
- Error messages don't leak sensitive data

---

## Conclusion

This architecture achieves the assignment goals through:

1. **Reliability**: Tool-based data access prevents hallucination
2. **Intelligence**: Groq Llama 3's reasoning provides natural interactions
3. **Maintainability**: Clear separation of concerns
4. **Extensibility**: New capabilities via new tools

The system demonstrates that LLMs + structured tools = powerful, trustworthy agents.

