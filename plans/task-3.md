# Task 3: The System Agent

## New tool: query_api
- **Parameters**: method (GET/POST), path, body (optional)
- **Authentication**: using LMS_API_KEY from .env.docker.secret
- **Returns**: JSON with status_code and body

## Update system prompt
Let's teach LLM to distinguish between three types of queries:
1. **Wiki questions** → use list_files/read_file
2. **System facts** (framework, ports) → read the code via read_file
3. **API requests** (item count, scores) → use query_api

## Environment variables
We read all configurations from variables:
- LLM_API_KEY, LLM_API_BASE, LLM_MODEL → from .env.agent.secret
- LMS_API_KEY → from .env.docker.secret
- AGENT_API_BASE_URL → optional, default http://localhost:42002

## Iteration plan
1. First, I'll implement the query_api
2. I will launch run_eval.py , I'll write down the results
3. I will fix one mistake at a time.
4. Goal: Pass all 10 local tests
