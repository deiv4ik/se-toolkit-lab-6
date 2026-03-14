# Task 1: Call an LLM from Code

## LLM Provider
- I use the Qwen Code API via a local proxy
- Model: QWEN3-coder-plus
- API Base: http://10.93.26.27:42005/v1

## Agent structure
1. Reads variables from .env.agent.secret
2. Gets a question from the command line
3. Sends a request to the LLM API
4. Outputs JSON with the answer and tool_calls fields
5. All debug output goes to stderr

## Running
uv run agent.py "the question"
