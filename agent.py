#!/usr/bin/env python3
"""
Agent that calls LLM and returns JSON response.
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv


def main():
    # Load environment variables
    load_dotenv('.env.agent.secret')
    
    api_key = os.getenv('LLM_API_KEY')
    api_base = os.getenv('LLM_API_BASE')
    model = os.getenv('LLM_MODEL')
    
    # Debug output to stderr
    print(f"Using model: {model}", file=sys.stderr)
    
    # Get question from command line
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py 'your question'", file=sys.stderr)
        sys.exit(1)
    
    question = sys.argv[1]
    print(f"Question: {question}", file=sys.stderr)
    
    # Prepare API request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": model,
        "messages": [
            {"role": "user", "content": question}
        ]
    }
    
    # Call LLM API
    try:
        response = requests.post(
            f"{api_base}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        answer = result['choices'][0]['message']['content']
        
        # Output JSON to stdout
        output = {
            "answer": answer.strip(),
            "tool_calls": []
        }
        print(json.dumps(output))
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
