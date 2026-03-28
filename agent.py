import os
import json
import time
from typing import List, Dict, Any, Optional
from groq import Groq
from openai import OpenAI
from tools import RetailTools, TOOL_DEFINITIONS


def _convert_tool_defs_to_groq(tool_defs):
    """Convert our tool definitions to Groq/OpenAI tool format"""
    declarations = []
    for tool in tool_defs:
        declarations.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"]
            }
        })
    return declarations


class RetailAgent:
    """Main AI agent for retail assistance -- supports Groq or OpenRouter"""
    
    def __init__(self, api_key: str = None, tools: RetailTools = None, use_openrouter: bool = False):
        self.tools = tools
        self.use_openrouter = use_openrouter
        
        # Initialize the appropriate API client
        if use_openrouter or api_key and "sk-" in api_key:
            # OpenRouter setup
            self.client = OpenAI(
                api_key=api_key or os.getenv("OPENROUTER_API_KEY"),
                base_url="https://openrouter.ai/api/v1"
            )
            self.model = "meta-llama/llama-3.3-70b-instruct"  # Popular model on OpenRouter
            self.use_openrouter = True
            print("[INFO] Using OpenRouter API")
        else:
            # Groq setup (default)
            self.client = Groq(api_key=api_key or os.getenv("GROQ_API_KEY"))
            self.model = "llama-3.3-70b-versatile"
            self.use_openrouter = False
            print("[INFO] Using Groq API")
        
        # Convert tool definitions to OpenAI-compatible format
        self.groq_tools = _convert_tool_defs_to_groq(TOOL_DEFINITIONS)
        
        # System prompts for different roles
        self.personal_shopper_prompt = """You are an expert personal shopper for a fashion retail store called OpenClaw.

Your role is to:
- Help customers find the perfect products based on their needs
- Consider multiple constraints: price, size, style, occasion
- Prioritize items that are in stock in the requested size
- Recommend sale items when appropriate to provide value
- Consider bestseller_score when ranking recommendations
- Explain your reasoning clearly -- why does this product fit their needs?

Key principles:
- NEVER make up product information -- only use data returned by tools
- Always use search_products to find items, then explain what you found
- MUST use native JSON tool calling. DO NOT output <function> or XML tags.
- If requesting a specific size, always verify stock_per_size shows stock > 0
- If no products match ALL criteria, explain what's available and suggest alternatives
- Justify recommendations based on the customer's stated constraints
- NEVER invent or guess an order ID or product ID. If you need it to call a tool, ask the customer first.
- Product IDs use format P0001, P0002, etc.
- Order IDs use format O0001, O0002, etc. (or just 0001, the system will handle both)

Store policies for context:
""" + tools.policy_text

        self.support_assistant_prompt = """You are a customer support specialist for a fashion retail store called OpenClaw.

Your role is to:
- Help customers with order inquiries and return requests
- Evaluate return/exchange eligibility using the evaluate_return tool
- Provide clear, policy-based decisions with explanations
- Handle order status questions professionally

TOOL USAGE -- ALWAYS FOLLOW THIS:
1. IF customer provides an order ID (like "0001", "O0002", "order 5") → IMMEDIATELY call get_order with that order_id
2. IF customer asks about returning something → IMMEDIATELY call evaluate_return with their order_id
3. DO NOT ask for more information if you already have the order ID
4. ALWAYS use the tools to look up real data before responding

Key principles:
- NEVER make up order or policy information -- only use data from tools
- You MUST call get_order or evaluate_return whenever a customer mentions an order ID
- MUST use native JSON tool calling. DO NOT output <function> or XML tags.
- Apply policies consistently and explain the reasoning
- Be empathetic but clear about policy limitations
- If an order doesn't exist, clearly state that and ask for verification
- Product IDs use format P0001, P0002, etc.
- Order IDs use format O0001, O0002, etc. (system accepts both with and without the 'O' prefix)

Store policies:
""" + tools.policy_text

        self.unified_prompt = """You are a versatile retail AI assistant for OpenClaw that handles both shopping assistance and customer support.

CONVERSATION STYLE:
- Be friendly, warm, and helpful
- Feel free to acknowledge casual greetings like "hi", "hello", "ok", "thanks", etc.
- Only use tools when the customer specifically wants to look up order info or product details
- Many messages don't require tool calls - just respond conversationally

PERSONAL SHOPPING:
- Help customers find products based on their preferences
- Consider price, size, style, occasion, and availability
- Recommend items that genuinely match their needs
- Explain why your recommendations fit their requirements
- Use search_products to find matching items

CUSTOMER SUPPORT:
- For ORDER STATUS INQUIRIES (where, when, what, status): Use get_order() to show delivery info, product details, prices, dates
- For RETURN/EXCHANGE ELIGIBILITY (can I return, is it returnable): Use evaluate_return() to show policy details
- DO NOT MIX THEM UP - they are completely different tools for different questions
- Apply store policies consistently
- Provide clear explanations for decisions

SIZING GUIDANCE:
- When a customer asks about sizing, use search_products to find the specific product
- Provide the available sizes and stock information
- If they mention general sizing (S/M/L), map approximately: S=4-6, M=8-10, L=12-14, XL=16

🔴 TOOL USAGE -- CLEAR RULES:

USE get_order WHEN customer asks about:
  - "where is my order?"
  - "what's my order status?"
  - "can you look up order 0003?"
  - "tell me about order X"
  - "what did I order?"
  → Use this to GET ORDER INFORMATION (delivery status, product details, price, etc)

USE evaluate_return ONLY WHEN customer explicitly asks about:
  - "can I return this order?"
  - "is this returnable?"
  - "I want to return order X"
  - "can I get a refund?"
  → Use this ONLY for RETURN ELIGIBILITY questions, NOT for order status

DO NOT call tools for:
  - Casual messages like "hi", "ok", "thanks", "fine"
  - Generic questions without order ID
  - Just respond conversationally to these

DO NOT ASSUME OR GUESS ORDER IDs (CRITICAL RULE):
  - If a user asks "where is my order?" or "can I return this?" BUT DOES NOT provide an Order ID (like O0005) in their message, YOU MUST ASK THEM FOR IT.
  - DO NOT call `get_order` or `evaluate_return` with a random, guessed, or placeholder ID (e.g. do not guess '0001').
  - ONLY use a tool if the user explicitly typed the ID in the chat!

CRITICAL: "where is my order?" = ORDER STATUS = use get_order, NOT evaluate_return
CRITICAL: "can I return my order?" = RETURN ELIGIBILITY = use evaluate_return

EXAMPLE SCENARIOS:
1. User: "order id = 0003"
   → This is asking for ORDER DETAILS
   → YOU MUST call get_order("0003") 
   → Do NOT call evaluate_return
   
2. User: "where is my shipment?"
   → This is asking for ORDER STATUS
   → YOU MUST call get_order with the order ID
   → Do NOT call evaluate_return
   
3. User: "can I return order 0003?"
   → This is asking for RETURN ELIGIBILITY
   → YOU MUST call evaluate_return("0003")
   → Do NOT call get_order
   
4. User: "I dont want this item"
   → If paired with an order ID, this asks for RETURN ELIGIBILITY
   → Call evaluate_return, NOT get_order

CRITICAL RULES:
- NEVER hallucinate -- only use data returned by the tools
- Always use tools to fetch real data before responding
- MUST use native JSON tool calling. DO NOT output <function> or XML tags.
- If a product or order doesn't exist, clearly state that
- Be professional, clear, and helpful
- NEVER guess or invent an order ID or product ID. If you don't have it, ask the user! If a user simply says "Where is my order" YOU MUST ASK "What is your order ID?"
- Product IDs use format P0001, P0002, etc.
- Order IDs use format O0001, O0002, etc. (or just 0001, system accepts both formats)

Store policies:
""" + tools.policy_text

    def process_tool_call(self, tool_name: str, tool_input: Dict) -> Any:
        """Execute a tool call and return results"""
        if tool_name == "search_products":
            result = self.tools.search_products(tool_input.get('filters', {}))
            if not result:
                return {
                    "error": "NO_DATA_FOUND",
                    "message": "No products found matching the given filters. Please try different criteria.",
                    "results": [],
                    "status": "no_results"
                }
            return {"results": result, "count": len(result), "status": "success"}
        
        elif tool_name == "get_product":
            result = self.tools.get_product(tool_input['product_id'])
            if result is None:
                return {
                    "error": "NOT_FOUND",
                    "message": f"Product '{tool_input['product_id']}' not found in our inventory",
                    "product_id": tool_input['product_id'],
                    "status": "not_found"
                }
            return {**result, "status": "success"}
        
        elif tool_name == "get_order":
            if not tool_input.get('customer_provided_id', False):
                return {
                    "error": "HALLUCINATION_DETECTED",
                    "message": "You tried to search for an order ID without the customer providing one. Stop and ask the customer for their order ID.",
                    "status": "error"
                }

            result = self.tools.get_order(tool_input['order_id'])
            if result is None:
                return {
                    "error": "NOT_FOUND",
                    "message": f"Order '{tool_input['order_id']}' not found in our system. Please check the order ID and try again.",
                    "order_id": tool_input['order_id'],
                    "status": "not_found"
                }
            return {**result, "status": "success"}
        
        elif tool_name == "evaluate_return":
            if not tool_input.get('customer_provided_id', False):
                return {
                    "error": "HALLUCINATION_DETECTED",
                    "message": "You tried to evaluate a return without the customer providing an order ID. Stop and ask the customer for their order ID.",
                    "status": "error"
                }

            result = self.tools.evaluate_return(tool_input['order_id'])
            # Check if order was not found
            if result.get('status') == 'not_found' or 'not found' in result.get('reason', '').lower():
                result['error'] = 'NOT_FOUND'
                result['status'] = 'not_found'
            else:
                result['status'] = 'success'
            return result
        
        else:
            return {
                "error": "UNKNOWN_TOOL",
                "message": f"Unknown tool: {tool_name}",
                "status": "error"
            }
    
    def _call_llm_with_retry(self, messages, max_retries=3):
        """Call LLM API (Groq or OpenRouter) with automatic retry on rate limit errors"""
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.groq_tools,
                    tool_choice="auto",
                    max_tokens=4096
                )
                return response
            except Exception as e:
                error_str = str(e).lower()
                
                # Handle Rate Limit
                if "429" in error_str or "rate limit" in error_str:
                    wait_time = 15 * (attempt + 1)
                    print(f"\n   [Rate limit hit. Waiting {wait_time}s before retry {attempt+1}/{max_retries}...]", flush=True)
                    time.sleep(wait_time)
                
                # Handle tool call validation errors
                elif "tool call validation failed" in error_str or "failed to call a function" in error_str:
                    print(f"\n   [Tool call error - retrying with proper format...]\n", flush=True)
                    
                    # Add strict instruction to use tools properly
                    if not any("STRICT FORMAT" in msg.get("content", "") for msg in messages if msg.get("role") == "user"):
                        messages.append({
                            "role": "user", 
                            "content": "STRICT FORMAT: If you need to call a tool, use ONLY the native tool calling - don't output JSON text. Call the tool through the system, not as text output. Try again now."
                        })
                else:
                    raise e
        
        raise Exception("API rate limit exceeded after retries. Please wait a minute and try again.")
    
    def chat(self, user_message: str, mode: str = "unified") -> str:
        """
        Process a user message and return AI response.
        Uses an agentic loop that handles tool calls via Groq native function calling.
        Includes safeguards against hallucination and proper error handling.
        """
        # Select system prompt
        if mode == "personal_shopper":
            system_prompt = self.personal_shopper_prompt
        elif mode == "support":
            system_prompt = self.support_assistant_prompt
        else:
            system_prompt = self.unified_prompt
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # Agentic loop -- keeps going until model returns text (not tool calls)
        max_iterations = 10
        iteration = 0
        has_data_error = False  # Track if we got a data not found error
        
        while iteration < max_iterations:
            iteration += 1
            
            response = self._call_llm_with_retry(messages)
            response_message = response.choices[0].message
            
            # Check if response has function calls
            if response_message.tool_calls:
                # Add the assistant's message to the history (including tool calls)
                messages.append(response_message)
                
                # Execute each tool and return the output
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    try:
                        function_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        function_args = {}
                        
                    tool_result = self.process_tool_call(function_name, function_args)
                    
                    # Check for data not found errors
                    if tool_result.get('error') == 'NOT_FOUND' or tool_result.get('status') == 'not_found':
                        has_data_error = True
                    
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(tool_result, default=str)
                    })
            else:
                # No function calls -- model returned its final text answer
                response_text = response_message.content or "I'm sorry, I couldn't generate a response."
                
                # Validate response doesn't hallucinate about missing data
                if has_data_error and response_text and not any(phrase in response_text.lower() for phrase in ['not found', 'not available', 'doesnt exist', "doesn't exist", 'no matching', 'unable to find', 'could not find']):
                    # LLM may have hallucinated despite getting error message
                    return self._get_fallback_response(messages, has_data_error)
                
                return response_text
        
        # Max iterations exceeded
        return "I apologize, but I wasn't able to complete your request after multiple attempts. Please try again or contact our support team."
    
    def _get_fallback_response(self, messages: List[Dict], has_data_error: bool = False) -> str:
        """
        Generate fallback response to prevent hallucination when data is not found.
        """
        if has_data_error:
            # Check what kind of tool was called by looking at message history
            for msg in reversed(messages):
                if msg.get('role') == 'tool':
                    content = msg.get('content', '')
                    if 'order' in content.lower() and 'not found' in content.lower():
                        return f"I couldn't find that order in our system. Could you please double-check the order ID and try again? Order IDs typically look like 'O0001' or just '0001'."
                    elif 'product' in content.lower() and 'not found' in content.lower():
                        return "That product doesn't appear to be in our inventory. Would you like me to search for similar items instead?"
                    elif 'no products found' in content.lower():
                        return "No products match those criteria. Would you like me to try searching with different filters?"
            
            return "I don't have information available for that request. Could you provide more details or clarify your question?"
        
        return "I'm sorry, I couldn't process your request. Please try again."
    
    def chat_interactive(self, mode: str = "unified"):
        """Run an interactive chatbot session"""
        print(f"\n{'='*60}")
        print(f"  OpenClaw AI Chatbot -- {mode.replace('_', ' ').title()} Mode")
        print(f"{'='*60}")
        print("  Type your message and press Enter.")
        print("  Type 'quit' to exit.\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if not user_input:
                continue
            
            print("\nAssistant: ", end="", flush=True)
            try:
                response = self.chat(user_input, mode=mode)
                print(response)
            except Exception as e:
                print(f"[Error: {e}]")
            print()


class OpenClawChatbot:
    """
    OpenClaw chatbot for customer-facing channels (chat & WhatsApp).
    Classifies inquiries, generates automated responses, and routes
    complex queries to human agents.
    """
    
    def __init__(self, retail_agent: RetailAgent):
        self.agent = retail_agent
        self.human_escalation_keywords = [
            'speak to human', 'talk to person', 'manager', 'complaint',
            'escalate', 'not satisfied', 'disappointed', 'angry',
            'terrible', 'worst', 'sue', 'lawyer', 'legal'
        ]
        # Track conversation state per channel/conversation
        self.conversation_state = {}  # session_id -> {'last_order_id': '0001', 'conversation_topic': 'return', etc}
    
    def _extract_order_id(self, message: str) -> Optional[str]:
        """Extract order ID from message (handles formats like 0001, O0001, order 0001, etc.)"""
        import re
        # Match patterns: O0123, 0123 (with optional 'order' prefix)
        patterns = [
            r'order\s*(?:id)?\s*[=:]?\s*O?(\d{4})',      # "order id = 0001" or "order 0001"
            r'O(\d{4})',                                   # "O0001"
            r'\b(\d{4})\b'                                # just "0001"
        ]
        for pattern in patterns:
            match = re.search(pattern, message.lower())
            if match:
                order_num = match.group(1)
                return order_num
        return None
    
    def _get_session_id(self, channel: str, user_id: Optional[str] = None) -> str:
        """Get or create a session ID for conversation history"""
        # In a real system, this would use actual user/session IDs
        # For now, use channel as a simple session identifier
        return channel
    
    def classify_inquiry(self, message: str) -> str:
        """Classify the type of customer inquiry"""
        message_lower = message.lower()
        
        if any(keyword in message_lower for keyword in self.human_escalation_keywords):
            return "escalate"
        if any(word in message_lower for word in ['return', 'exchange', 'refund', 'send back']):
            return "return_request"
        if any(word in message_lower for word in ['size', 'sizing', 'fit', 'fits', 'measurements']):
            return "sizing"
        if any(word in message_lower for word in ['order', 'tracking', 'delivery', 'shipped', 'status']):
            return "order_status"
        return "general"
    
    def handle_message(self, message: str, channel: str = "chat", user_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle incoming message from chat or WhatsApp"""
        session_id = self._get_session_id(channel, user_id)
        
        # Initialize or get conversation state
        if session_id not in self.conversation_state:
            self.conversation_state[session_id] = {'last_order_id': None}
        
        state = self.conversation_state[session_id]
        
        # Extract order ID from current message
        current_order_id = self._extract_order_id(message)
        if current_order_id:
            state['last_order_id'] = current_order_id
        
        # Classify the inquiry
        inquiry_type = self.classify_inquiry(message)
        
        if inquiry_type == "escalate":
            return {
                "response": "I understand you'd like to speak with someone from our team. "
                           "Let me connect you with a human agent who can better assist you. "
                           "Please hold for a moment.",
                "action": "route_to_human",
                "inquiry_type": inquiry_type,
                "channel": channel
            }
        
        # If it's a return/exchange request and no order ID in current message,
        # use the last known order ID from conversation history
        enhanced_message = message
        if inquiry_type in ["return_request"] and not current_order_id and state['last_order_id']:
            enhanced_message = f"{message} (order {state['last_order_id']})"
        
        # If it's an order status inquiry with order ID, add explicit instruction
        if inquiry_type == "order_status" and (current_order_id or state['last_order_id']):
            order_id = current_order_id or state['last_order_id']
            enhanced_message = f"{message}\n[INSTRUCTION: This is an order STATUS query. Call get_order with order_id={order_id}. Do NOT call evaluate_return.]"
        
        try:
            response = self.agent.chat(enhanced_message, mode="unified")
            
            # Validate response (fallback for potential hallucination)
            if not response or response.startswith("I'm sorry") or response.startswith("I apologize"):
                # Check if this might be a not-found scenario
                if inquiry_type in ["order_status", "return_request"] and (current_order_id or state['last_order_id']):
                    fallback_msg = f"I couldn't retrieve information for order {current_order_id or state['last_order_id']}. "
                    fallback_msg += "Please verify the order ID is correct and try again, or contact our support team."
                    return {
                        "response": fallback_msg,
                        "action": "fallback_response",
                        "inquiry_type": inquiry_type,
                        "channel": channel
                    }
            
            return {
                "response": response,
                "action": "automated_response",
                "inquiry_type": inquiry_type,
                "channel": channel
            }
        except Exception as e:
            return {
                "response": "I apologize, but I'm having trouble processing your request. "
                           "Let me connect you with a team member who can help.",
                "action": "route_to_human",
                "inquiry_type": "error",
                "channel": channel,
                "error": str(e)
            }
    
    def simulate_conversation(self, messages: List[str], channel: str = "chat"):
        """Simulate a multi-turn conversation for demo/testing"""
        print(f"\n{'='*60}")
        print(f"  OpenClaw Chatbot Simulation -- {channel.upper()}")
        print(f"{'='*60}\n")
        
        for i, msg in enumerate(messages):
            if i > 0:
                # Add delay between messages to avoid rate limiting
                print("  [waiting 5s to avoid rate limit...]")
                time.sleep(5)
            
            print(f"  Customer [{channel}]: {msg}")
            result = self.handle_message(msg, channel)
            print(f"  Bot: {result['response']}")
            print(f"  [Action: {result['action']} | Type: {result['inquiry_type']}]")
            print("-" * 60)
    
    def run_interactive(self, channel: str = "chat"):
        """Run an interactive chatbot simulating a channel"""
        print(f"\n{'='*60}")
        print(f"  OpenClaw Chatbot -- {channel.upper()} Channel")
        print(f"{'='*60}")
        print("  Type your message and press Enter.")
        print("  Type 'quit' to exit.\n")
        
        while True:
            try:
                user_input = input(f"  Customer [{channel}]: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n  Session ended.")
                break
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("  Session ended.")
                break
            
            if not user_input:
                continue
            
            result = self.handle_message(user_input, channel)
            print(f"  Bot: {result['response']}")
            print(f"  [Action: {result['action']} | Type: {result['inquiry_type']}]")
            print()