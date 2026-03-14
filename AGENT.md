## Task 2: Documentation Agent

### Tools
The agent now has two tools:
- **read_file(path)** - reads a file from the project
- **list_files(path)** - lists contents of a directory

### Agentic Loop
1. Send question + tool definitions to LLM
2. If LLM requests tools → execute them, add results to history, repeat
3. If LLM gives text answer → extract answer and source, output JSON
4. Maximum 10 tool calls to prevent infinite loops

### Security
Both tools prevent directory traversal attacks by checking that all paths are within the project root directory.

### Output Format
```json
{
  "answer": "The answer text",
  "source": "wiki/filename.md#section",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "file listing..."},
    {"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": "file content..."}
  ]
}
