## Task 3: System Agent

### query_api Tool
The `query_api` tool allows the agent to interact with the live backend API:
- **Parameters**: `method` (GET/POST), `path` (endpoint), `body` (optional), `use_auth` (boolean)
- **Authentication**: Uses `LMS_API_KEY` from `.env.docker.secret`
- **Returns**: JSON with `status_code` and `body`

### Tool Selection Logic
The LLM decides which tool to use based on the question:
- **Wiki questions** (branch protection, SSH) → `list_files` + `read_file` on wiki/
- **Code questions** (framework) → `read_file` on backend/pyproject.toml
- **Live data questions** (items count) → `query_api` with GET /items/
- **Error debugging** (completion-rate, top-learners) → `query_api` first, then `read_file` on source

### Lessons Learned from Benchmark
1. **Context size matters**: Qwen API returns 500 errors with large contexts → implemented aggressive message truncation
2. **Tool descriptions must be precise**: LLM needs clear instructions on when to use each tool
3. **Error handling is crucial**: Added fallback mechanisms for API failures
4. **Direct handlers for complex questions**: Some questions (merge conflict, ETL) work better with direct file reading
5. **Source field is optional**: In Task 3, source is not required for all answers

### Final Evaluation Score
- **run_eval.py**: ✅ 10/10 questions passed
- **test_agent.py**: ✅ All 5 tests passed
- **Hidden questions**: Pending autochecker evaluation

The agent successfully handles:
- Wiki documentation lookup
- Source code analysis
- Live API queries
- Error debugging
- Architecture explanation
- ETL idempotency analysis
