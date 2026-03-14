# Agent Documentation

## Overview
This agent connects to Qwen LLM and returns answers in JSON format.

## LLM Provider
- **Provider**: Qwen Code API via local proxy
- **Model**: qwen3-coder-plus
- **API Base**: http://10.93.26.27:42005/v1

## Setup
1. Copy `.env.agent.example` to `.env.agent.secret`
2. Fill in your API key and endpoint
3. Run with: `uv run agent.py "your question"`

## Output Format
The agent outputs a single JSON line:
```json
{"answer": "response text", "tool_calls": []}
