# Retail AI Assistant

An intelligent agentic system that acts as both a Personal Shopper and Customer Support Assistant, powered by Groq Llama 3 (FREE API).

## 🎯 Project Overview

This project implements a retail AI assistant capable of:

- **Personal Shopping**: Recommending products based on customer preferences with multi-constraint reasoning
- **Customer Support**: Handling order inquiries and return/exchange requests using policy-based reasoning
- **OpenClaw Integration**: Automating first-response messaging on chat and WhatsApp channels

## ✨ Features

✅ **Function Calling**: Uses Groq/OpenAI native function calling for dynamic decision-making  
✅ **Hallucination Prevention**: Strict tool-only data access ensures accuracy  
✅ **Stock Awareness**: Real-time inventory checking for size availability  
✅ **Policy-Based Reasoning**: Automated return evaluation using structured rules  
✅ **Multi-Constraint Search**: Handles complex queries with multiple filters  
✅ **Automatic Escalation**: Routes complex queries to human agents  

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Groq API key (FREE from [Groq Console](https://console.groq.com/keys))

### Installation

1. **Clone or download this repository**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your API key**:
   
   Create a `.env` file in the project root:
   ```bash
   GROQ_API_KEY=your_api_key_here
   ```
   
   Or export it as an environment variable:
   ```bash
   export GROQ_API_KEY=your_api_key_here
   ```

4. **Run the application**:
   ```bash
   python main.py
   ```

## 📁 Project Structure

```
retail-ai-assistant/
├── main.py              # Main application with demo scenarios
├── agent.py             # RetailAgent and OpenClawChatbot classes
├── tools.py             # Tool implementations and definitions
├── requirements.txt     # Python dependencies
├── .env                 # API keys (create this file)
├── ARCHITECTURE.md      # Detailed architecture documentation
├── README.md            # This file
└── data/
    ├── products.csv     # Sample product inventory
    ├── orders.csv       # Sample customer orders
    └── policy.txt       # Return/exchange policies
```

## 🎮 Usage

### Main Menu Options

When you run `python main.py`, you'll see:

```
1. Run Personal Shopper Demo      # See product recommendations
2. Run Customer Support Demo       # See return/exchange handling
3. Run Edge Cases Demo             # See error handling
4. Run OpenClaw Chat Automation    # See chat automation
5. Run ALL Demos                   # Run everything
6. Interactive Mode                # Chat with the agent
7. Offline Verification            # Test tools without API key
8. Exit
```

### Demo Scenarios Included

#### 📦 Personal Shopper (2 scenarios)
- Modest evening gown under $300, size 8, on sale
- Professional work dress, size 10, with sleeves, ~$200 budget

#### Customer Support (2 scenarios)
- Return request for a sale item (Order O0005)
- Clearance item return attempt (Order O0012)

#### Edge Cases (3 scenarios)
- Invalid order ID (O9999)
- Product unavailable in requested size
- Vendor exception (Aurelia Couture - exchange only)

#### 💬 OpenClaw Automation
- Multi-turn WhatsApp conversation
- Escalation scenario demonstration

### Interactive Mode

Choose option 6 to chat directly with the agent:

```bash
You: I'm looking for an evening dress under $350
Assistant: [Searches products and provides recommendations]

You: Do you have it in size 8?
Assistant: [Checks stock availability for size 8]
```

## 🔧 Key Components

### 1. Tools (tools.py)

Four core tools that provide data access:

- **`search_products(filters)`**: Search inventory with multiple constraints
- **`get_product(product_id)`**: Retrieve specific product details
- **`get_order(order_id)`**: Get order information
- **`evaluate_return(order_id)`**: Check return eligibility based on policies

### 2. Agent (agent.py)

- **`RetailAgent`**: Main AI agent with Groq integration
- **`OpenClawChatbot`**: Specialized chatbot for automated responses

### 3. Data Files

- **`products.csv`**: 100 fashion products with pricing, sizes, stock levels
- **`orders.csv`**: 100 orders with dates and customer info
- **`policy.txt`**: Return/exchange policies with timeframes and exceptions

## 🏗️ Architecture Highlights

### Hallucination Prevention

The system prevents AI hallucination through:

1. **Tool-Only Data Access**: Agent cannot access data without calling tools
2. **Explicit None Handling**: Tools return None for missing data
3. **Structured Responses**: All tool outputs are validated and structured
4. **System Prompt Enforcement**: Clear instructions against making up data

### Agentic Loop

```
User Message → Agent Analyzes → Calls Tools → Processes Results → Responds
                    ↑                                              ↓
                    └──────────── Loop if more data needed ───────┘
```

### Tool Selection

Groq (Llama 3) automatically selects appropriate tools based on:
- User intent analysis
- Tool descriptions and schemas
- Current conversation context
- Data availability and requirements

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed technical documentation.

## 📊 Sample Data Overview

### Products
- 100 dresses ranging from $53 - $475
- Multiple vendors (Nocturne, Aurelia Couture, Velvet Rose, Metropolitan, etc.)
- Various styles (evening, cocktail, casual, formal)
- Size availability tracked per item
- Sale and clearance items included

### Orders
- 100 orders from January-February 2026
- Mix of regular, sale, and clearance purchases
- Includes recent and old orders for return testing

### Policies
- Normal items: 14-day return window (full refund)
- Sale items: 7-day return window (store credit only)
- Clearance items: Final sale (no returns)
- Vendor exceptions: Aurelia Couture (exchange only), Nocturne (21-day window)

## 🧪 Testing the System

### Test Case 1: Multi-Constraint Search
```
Query: "Modest evening gown under $300 in size 8, on sale"
Expected: Finds products matching ALL criteria
Verifies: Stock checking, price filtering, tag matching, sale prioritization
```

### Test Case 2: Return Evaluation
```
Query: "Order O0005 - Can I return it?"
Expected: Checks order date, product type, applies correct policy
Verifies: Order lookup, policy application, reasoning explanation
```

### Test Case 3: Edge Case Handling
```
Query: "Return order O9999"
Expected: "Order not found" - no hallucination
Verifies: Graceful error handling, no made-up information
```

## 🔐 Security & Best Practices

- API keys stored in `.env` (never commit this file!)
- Input validation in all tools
- Error handling with graceful degradation
- No customer data logging by default
- Stateless design for scalability

## 📝 Customization

### Adding Your Own Data

1. **Replace CSV files** in `data/` directory with your inventory/orders
2. **Update policy.txt** with your store's return policies
3. **Adjust tool parsing** in `tools.py` if your data format differs

### Adding New Tools

```python
# In tools.py
def your_new_tool(self, param):
    # Implementation
    pass

# Add tool definition to TOOL_DEFINITIONS
{
    "name": "your_new_tool",
    "description": "What this tool does",
    "input_schema": {...}
}

# In agent.py - add to process_tool_call()
elif tool_name == "your_new_tool":
    return self.tools.your_new_tool(tool_input['param'])
```

## 🤝 Assignment Deliverables

This project includes all required deliverables:

✅ **Working Implementation**: Fully functional CLI application  
✅ **Tool Implementations**: All 4 required tools (search, get_product, get_order, evaluate_return)  
✅ **Personal Shopper**: Multi-constraint reasoning with stock awareness  
✅ **Support Assistant**: Policy-based return evaluation  
✅ **Edge Cases**: Invalid order handling, missing product scenarios  
✅ **Architecture Document**: Detailed explanation of design decisions  
✅ **Demo Examples**: 2 shopping + 2 support + 1 edge case  
✅ **OpenClaw Integration**: Chat/WhatsApp automation with routing  

## 📚 Additional Resources

- [Groq API Documentation](https://console.groq.com/docs/quickstart)
- [Groq Function Calling Guide](https://console.groq.com/docs/tool-use)
- [ARCHITECTURE.md](ARCHITECTURE.md) - Deep dive into system design

## ⏱️ Development Time

This implementation represents approximately 8-10 hours of development:
- Planning & architecture: 2 hours
- Tool implementation: 2 hours
- Agent & function calling: 2 hours
- OpenClaw integration: 1 hour
- Testing & demos: 2 hours
- Documentation: 2 hours

## 📄 License

This is an educational project created for assignment purposes.

## 🙋 Questions?

Refer to the [ARCHITECTURE.md](ARCHITECTURE.md) document for:
- Detailed system design rationale
- Hallucination prevention strategies
- Tool selection mechanics
- OpenClaw integration details
- Extension guidelines

---

**Happy Testing! 🚀**