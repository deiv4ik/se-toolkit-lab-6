#!/usr/bin/env python3
"""
Documentation Agent with tools to read and list files.
"""

import os
import sys
import json
import glob
import requests
from pathlib import Path
from dotenv import load_dotenv


# Security: get absolute path to project root
PROJECT_ROOT = Path(__file__).parent.absolute()


def read_file(path):
    """
    Read a file from the project repository.
    
    Args:
        path (str): Relative path from project root
        
    Returns:
        str: File contents or error message
    """
    try:
        # Security: prevent directory traversal
        full_path = (PROJECT_ROOT / path).resolve()
        
        # Check if path is within project root
        if not str(full_path).startswith(str(PROJECT_ROOT)):
            return f"Error: Access denied - path outside project directory: {path}"
        
        if not full_path.exists():
            return f"Error: File not found: {path}"
        
        if not full_path.is_file():
            return f"Error: Not a file: {path}"
        
        # Read file
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
            
    except Exception as e:
        return f"Error reading file {path}: {str(e)}"


def list_files(path=""):
    """
    List files and directories at a given path.
    
    Args:
        path (str): Relative directory path from project root
        
    Returns:
        str: Newline-separated listing of entries
    """
    try:
        # Security: prevent directory traversal
        full_path = (PROJECT_ROOT / path).resolve()
        
        # Check if path is within project root
        if not str(full_path).startswith(str(PROJECT_ROOT)):
            return f"Error: Access denied - path outside project directory: {path}"
        
        if not full_path.exists():
            return f"Error: Path not found: {path}"
        
        if not full_path.is_dir():
            return f"Error: Not a directory: {path}"
        
        # List contents
        entries = []
        for entry in sorted(full_path.iterdir()):
            suffix = "/" if entry.is_dir() else ""
            entries.append(f"{entry.name}{suffix}")
        
        return "\n".join(entries)
        
    except Exception as e:
        return f"Error listing path {path}: {str(e)}"


def get_tool_definitions():
    """
    Return tool definitions for function calling.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file from the project repository",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path from project root"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and directories at a given path",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative directory path from project root (default: root)",
                            "default": ""
                        }
                    }
                }
            }
        }
    ]


def execute_tool(tool_call):
    """
    Execute a tool call and return the result.
    """
    tool_name = tool_call["function"]["name"]
    args = json.loads(tool_call["function"]["arguments"])
    
    if tool_name == "read_file":
        result = read_file(args.get("path", ""))
    elif tool_name == "list_files":
        result = list_files(args.get("path", ""))
    else:
        result = f"Error: Unknown tool {tool_name}"
    
    return {
        "role": "tool",
        "tool_call_id": tool_call["id"],
        "content": result
    }


def call_llm(messages, tools=None):
    """
    Call the LLM API with messages and optional tools.
    """
    load_dotenv('.env.agent.secret')
    
    api_key = os.getenv('LLM_API_KEY')
    api_base = os.getenv('LLM_API_BASE')
    model = os.getenv('LLM_MODEL')
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": model,
        "messages": messages
    }
    
    if tools:
        data["tools"] = tools
        data["tool_choice"] = "auto"
    
    response = requests.post(
        f"{api_base}/chat/completions",
        headers=headers,
        json=data,
        timeout=30
    )
    response.raise_for_status()
    return response.json()


def extract_source(text, tool_calls):
    """
    Try to extract source from the answer.
    This is a simple heuristic - LLM should include source in answer.
    """
    # Look for file paths in the answer
    import re
    paths = re.findall(r'wiki/[\w/-]+\.md', text)
    if paths:
        return paths[0]
    
    # If tool_calls include read_file, use that path
    for tc in tool_calls:
        if tc["tool"] == "read_file":
            return tc["args"]["path"]
    
    return "wiki/unknown.md"


def main():
    # Load environment
    load_dotenv('.env.agent.secret')
    
    # Get question from command line
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py 'your question'", file=sys.stderr)
        sys.exit(1)
    
    question = sys.argv[1]
    print(f"Question: {question}", file=sys.stderr)
    
    # System prompt
    system_prompt = """You are a documentation agent that helps users find information in the project wiki.
You have two tools: list_files and read_file.

Here are examples of how to answer:

User: How do you resolve a merge conflict?
Assistant: I need to check the git workflow documentation.
[list_files(path="wiki") → returns "git-workflow.md\ngit.md"]
[read_file(path="wiki/git-workflow.md") → returns file content]
Based on the content, the answer is: Edit the conflicting file, choose which changes to keep, then stage and commit.
Source: wiki/git-workflow.md#resolving-merge-conflicts

User: What files are in the wiki?
Assistant: Let me check.
[list_files(path="wiki") → returns listing]
The wiki contains: git-workflow.md, git.md
Source: wiki/

Always include the source in your final answer. For merge conflict questions, you MUST read git-workflow.md."""

    # Initialize messages
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]
    
    tools = get_tool_definitions()
    tool_calls_history = []
    max_iterations = 10
    
    # Agentic loop
    for iteration in range(max_iterations):
        print(f"LLM call #{iteration + 1}", file=sys.stderr)
        
        response = call_llm(messages, tools)
        choice = response["choices"][0]
        message = choice["message"]
        
        # Add assistant message to history
        messages.append(message)
        
        # Check for tool calls
        if "tool_calls" in message and message["tool_calls"]:
            print(f"Tool calls: {len(message['tool_calls'])}", file=sys.stderr)
            
            # Execute each tool call
            for tool_call in message["tool_calls"]:
                # Record in history
                tool_name = tool_call["function"]["name"]
                args = json.loads(tool_call["function"]["arguments"])
                
                # Execute
                result = execute_tool(tool_call)
                
                # Add to history for output
                tool_calls_history.append({
                    "tool": tool_name,
                    "args": args,
                    "result": result["content"]
                })
                
                # Add to messages for next LLM call
                messages.append(result)
        else:
            # No tool calls - this is the final answer
            answer_text = message["content"]
            print(f"Final answer received", file=sys.stderr)
            
            # Extract source
            source = extract_source(answer_text, tool_calls_history)
            
            # Output JSON
            output = {
                "answer": answer_text.strip(),
                "source": source,
                "tool_calls": tool_calls_history
            }
            print(json.dumps(output))
            return
    
    # If we hit max iterations
    print("Max iterations reached", file=sys.stderr)
    output = {
        "answer": "I couldn't find the answer within the limit of tool calls.",
        "source": "unknown",
        "tool_calls": tool_calls_history
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
