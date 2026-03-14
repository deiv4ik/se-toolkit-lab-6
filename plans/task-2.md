# Task 2: The Documentation Agent

## Agentic Loop Design
1. We are sending a question + definitions of tools to LLM
2. Check the answer:
- If there are `tool_calls` → execute each tool, add the results to the history, repeat
- If there are no `tool_calls` → this is the final answer, extract the answer and source
3. Maximum of 10 tool calls to prevent endless loops

## Tool Schemas
### read_file
- Reads a file from a project
- Parameters: `path' (string)
- Security: checking for `..` and going beyond the project

### list_files
- Writes off the contents of the directory
- Parameters: `path' (string)
- Security: checking for `..` and going beyond the project

## System Prompt
Instructing LLM:
1. Use `list_files' to explore wiki
2. Use `read_file` to read specific files
3. In the response, specify the source (file path + section)
