import os
import sys
from typing import Annotated, TypedDict, Union, List
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from tools import tools

# Load environment variables
load_dotenv()

def create_market_watcher():
    """
    Creates a manually constructed LangGraph agent to demonstrate 
    Transparent Flow and Human-in-the-loop (HITL) control.
    """
    # Initialize Gemini 3 Pro Preview
    llm = ChatGoogleGenerativeAI(
        model="gemini-3-pro-preview", 
        temperature=0.2,
        google_api_key=os.getenv("GOOGLE_API_KEY")
    ).bind_tools(tools)
    
    # Updated system prompt with Thought Process, HITL, Discovery, and No-Advice Rules
    system_prompt = """You are 'Market Watcher', a professional financial data analyst.
You have four specialized tools at your disposal that return structured JSON data.

STRICT FINANCIAL ADVICE POLICY:
1. NEVER provide explicit "Buy", "Sell", or "Hold" recommendations.
2. NEVER use subjective labels like "safe to buy", "great bet", "risky", or "stable zone".
3. NEVER provide a "Verdict" on a stock's investability.
4. Your role is strictly to interpret DATA and identify RISK FACTORS (e.g., "Price is near 6-month support").
5. If a user asks for advice (e.g., "Should I buy?"), explicitly state that you provide data insights only, then present the objective metrics for the user to make their own informed decision.

DISCOVERY RULE (CRITICAL):
If the user provides a ticker symbol (e.g., "AAPL" or "NVDA") but does NOT ask a specific question, DO NOT call any tools. 
Instead, acknowledge the ticker and ask the user which type of analysis they prefer. Present these options clearly:
1. NEWS: Why is it moving? (Catalysts & News)
2. LEVELS: What are the price floors? (Support/Resistance)
3. TRENDS: Is the sentiment driving the chart? (Sentiment/Technical Correlation)
4. COMPARISON: What changed recently? (7-30 Day Performance)

TRANSPARENCY & REASONING RULES:
1. BEFORE proposing any tool calls, you must explain your THOUGHT PROCESS. 
2. In your response, clearly state WHY you are choosing specific tools and what you hope to find.
3. If you have enough information to answer partially, share that thought first.

HUMAN INTERACTION RULES:
1. If the user mentions a company but not a ticker (e.g., "Apple"), ASK for the ticker or confirm if they mean "AAPL".
2. If the user's request is vague, ASK which stock they are interested in.
3. If the user denies a tool call or provides feedback/refinement (e.g., "skip news"), ACKNOWLEDGE it and pivot your strategy.

DATA PRESENTATION RULES:
1. ALWAYS present financial data in a clean, professional format.
2. Use Markdown TABLES for price levels, historical changes, and technical indicators.
3. Use bullet points for news headlines and catalysts.
4. Summarize the "Market Context" based on the news snippets provided by the tools instead of giving a "Verdict".

TOOLS:
1. 'why_stock_moved': Explains catalysts, news, and 1-day price moves.
2. 'analyze_price_trend_news_correlation': Shows how news sentiment drives technical trends (SMA20/50).
3. 'what_changed_recently': Compares current data vs last 7-30 days (Price, Volume, Volatility).
4. 'get_market_alerts_and_levels': Provides support/resistance levels and upcoming calendar events.

Be professional, objective, and data-driven."""

    # Node: The Reasoning LLM
    def call_model(state: MessagesState):
        messages = state["messages"]
        # Prepend system prompt to the context for the LLM
        response = llm.invoke([{"role": "system", "content": system_prompt}] + messages)
        return {"messages": [response]}

    # Node: The Tool Executor
    tool_node = ToolNode(tools)

    # Define the Logic/Flow
    def should_continue(state: MessagesState):
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    # Build the Graph
    workflow = StateGraph(MessagesState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", should_continue, ["tools", END])
    workflow.add_edge("tools", "agent")

    # Add memory and INTERRUPT before tools for HITL
    memory = MemorySaver()
    agent_graph = workflow.compile(
        checkpointer=memory,
        interrupt_before=["tools"]
    )
    
    return agent_graph


def run_terminal_interface():
    """
    Run the terminal-based interface with LangGraph HITL interrupt logic.
    """
    if sys.platform == "win32":
        import subprocess
        try:
            subprocess.run(["chcp", "65001"], capture_output=True, check=True)
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    print("=" * 60)
    print(" MARKET WATCHER AGENT - Transparent HITL Mode ")
    print("=" * 60)
    print("Ask about any stock. I will show my thoughts and ask for approval.")
    print("Type 'exit' to quit.")
    print("-" * 60)
    
    agent_graph = create_market_watcher()
    config = {"configurable": {"thread_id": "market_watcher_user"}}
    
    while True:
        try:
            user_input = input("\nMarket Watcher > ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\nGoodbye!")
                break
            
            if not user_input:
                continue
            
            # Start/Continue the graph
            # 1. Provide user input
            for event in agent_graph.stream(
                {"messages": [{"role": "user", "content": user_input}]},
                config,
                stream_mode="values"
            ):
                pass
            
            # 2. Check if we are interrupted (waiting for tool approval)
            snapshot = agent_graph.get_state(config)
            
            while snapshot.next:
                # We are at an interrupt (likely before 'tools' node)
                last_msg = snapshot.values["messages"][-1]
                
                # Display Thoughts
                thought_content = last_msg.content
                if isinstance(thought_content, list):
                    thought_content = "\n".join([part["text"] for part in thought_content if isinstance(part, dict) and "text" in part])
                
                if thought_content:
                    print(f"\n[AGENT THOUGHTS]:\n{thought_content}")
                
                print("\n[PROPOSED ACTIONS]:")
                for call in last_msg.tool_calls:
                    print(f" -> {call['name']} (Args: {call['args']})")
                
                confirm = input("\nApprove? (y/n or feedback): ").strip().lower()
                
                if confirm == 'y':
                    # Resume execution
                    for event in agent_graph.stream(None, config, stream_mode="values"):
                        pass
                else:
                    # Provide feedback and go back to agent node
                    feedback = confirm if confirm != 'n' else "I don't want you to use those tools. Please adjust your plan."
                    print(f"[SYSTEM]: Feedback sent: '{feedback}'")
                    
                    agent_graph.update_state(
                        config,
                        {"messages": [{"role": "user", "content": feedback}]},
                        as_node="agent" 
                    )
                    # Re-run agent node with feedback
                    for event in agent_graph.stream(None, config, stream_mode="values"):
                        pass
                
                snapshot = agent_graph.get_state(config)

            # Final response
            final_state = agent_graph.get_state(config)
            response_text = final_state.values["messages"][-1].content
            
            if isinstance(response_text, list):
                response_text = "\n".join([part["text"] for part in response_text if isinstance(part, dict) and "text" in part])
            
            if response_text:
                print(f"\n[ANALYSIS]:\n{response_text}")
                
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\n[ERROR]: {str(e)}")


if __name__ == "__main__":
    if not os.getenv("GOOGLE_API_KEY"):
        print("Error: GOOGLE_API_KEY environment variable is not set.")
        exit(1)
    
    run_terminal_interface()
