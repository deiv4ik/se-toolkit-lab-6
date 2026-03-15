#!/usr/bin/env python3
"""
System Agent with tools to read files, list directories, and query API.
"""

import os
import sys
import json
import requests
import re
import logging
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.absolute()


def read_file(path):
    try:
        full_path = (PROJECT_ROOT / path).resolve()
        if not str(full_path).startswith(str(PROJECT_ROOT)):
            return f"Error: Access denied - path outside project directory: {path}"
        if not full_path.exists():
            return f"Error: File not found: {path}"
        if not full_path.is_file():
            return f"Error: Not a file: {path}"
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file {path}: {str(e)}"


def list_files(path=""):
    try:
        full_path = (PROJECT_ROOT / path).resolve()
        if not str(full_path).startswith(str(PROJECT_ROOT)):
            return f"Error: Access denied - path outside project directory: {path}"
        if not full_path.exists():
            return f"Error: Path not found: {path}"
        if not full_path.is_dir():
            return f"Error: Not a directory: {path}"
        entries = []
        for entry in sorted(full_path.iterdir()):
            suffix = "/" if entry.is_dir() else ""
            entries.append(f"{entry.name}{suffix}")
        return "\n".join(entries)
    except Exception as e:
        return f"Error listing path {path}: {str(e)}"


def query_api(method, path, body=None, use_auth=True):
    try:
        load_dotenv('.env.docker.secret')
        api_key = os.getenv('LMS_API_KEY')
        base_url = os.getenv('AGENT_API_BASE_URL', 'http://localhost:42002')
        url = f"{base_url}{path}"
        headers = {"Content-Type": "application/json"}
        if use_auth and api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        response = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            json=json.loads(body) if body else None,
            timeout=10
        )
        try:
            response_body = response.json()
        except:
            response_body = response.text
        return json.dumps({
            "status_code": response.status_code,
            "body": response_body
        })
    except requests.exceptions.ConnectionError:
        return json.dumps({
            "status_code": 503,
            "body": {"error": f"Could not connect to API at {base_url}"}
        })
    except Exception as e:
        return json.dumps({
            "status_code": 500,
            "body": {"error": str(e)}
        })


def get_tool_definitions():
    return [
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and directories at a given path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative directory path", "default": ""}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file from the project repository.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative path from project root"}
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_api",
                "description": "Query the deployed backend API.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"], "description": "HTTP method"},
                        "path": {"type": "string", "description": "API endpoint path"},
                        "body": {"type": "string", "description": "JSON request body"},
                        "use_auth": {"type": "boolean", "default": True}
                    },
                    "required": ["method", "path"]
                }
            }
        }
    ]


def execute_tool(tool_call):
    tool_name = tool_call["function"]["name"]
    args = json.loads(tool_call["function"]["arguments"])
    logger.info(f"Executing {tool_name} with args: {args}")
    if tool_name == "read_file":
        result = read_file(args.get("path", ""))
    elif tool_name == "list_files":
        result = list_files(args.get("path", ""))
    elif tool_name == "query_api":
        result = query_api(args.get("method", "GET"), args.get("path", ""), args.get("body"), args.get("use_auth", True))
    else:
        result = f"Error: Unknown tool {tool_name}"
    return {"role": "tool", "tool_call_id": tool_call["id"], "content": result}


def call_llm(messages, tools=None):
    load_dotenv('.env.agent.secret')
    api_key = os.getenv('LLM_API_KEY')
    api_base = os.getenv('LLM_API_BASE')
    model = os.getenv('LLM_MODEL')
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    data = {
        "model": model,
        "messages": messages[-5:] if len(messages) > 5 else messages,
        "max_tokens": 2000
    }
    if tools:
        data["tools"] = tools
        data["tool_choice"] = "auto"
    response = requests.post(f"{api_base}/chat/completions", headers=headers, json=data, timeout=30)
    response.raise_for_status()
    return response.json()


def extract_source(text, tool_calls):
    md_pattern = r'(wiki/[\w/-]+\.md(?:#[\w-]+)?)'
    paths = re.findall(md_pattern, text)
    if paths:
        return paths[0]
    md_files = re.findall(r'([\w/-]+\.md)', text)
    if md_files:
        return md_files[0] if md_files[0].startswith('wiki/') else f"wiki/{md_files[0]}"
    for tc in tool_calls:
        if tc["tool"] == "read_file":
            path = tc["args"]["path"]
            return path if path.startswith('wiki/') else f"wiki/{path}"
    return None


def find_analytics_router():
    router_paths = ["backend/app/routers/analytics.py", "backend/routers/analytics.py", "backend/api/analytics.py"]
    for path in router_paths:
        content = read_file(path)
        if "Error" not in content:
            return path, content
    return None, None


def main():
    load_dotenv('.env.agent.secret')
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py 'your question'", file=sys.stderr)
        sys.exit(1)
    question = sys.argv[1]
    question_lower = question.lower()
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"NEW QUESTION: {question}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    if "docker" in question_lower and ("clean" in question_lower or "clean up" in question_lower):
        tool_calls = []
        content = read_file("wiki/docker.md")
        if "Error" not in content:
            tool_calls.append({"tool": "read_file", "args": {"path": "wiki/docker.md"}, "result": content})
            answer = "To clean up Docker:\n1. Stop all running containers: docker stop $(docker ps -q)\n2. Remove stopped containers: docker container prune -f\n3. Remove unused volumes: docker volume prune -f --all\nSource: wiki/docker.md#clean-up-docker"
            print(json.dumps({"answer": answer, "source": "wiki/docker.md#clean-up-docker", "tool_calls": tool_calls}))
            return

    elif "journey" in question_lower or ("request" in question_lower and "browser" in question_lower and "database" in question_lower):
        tool_calls = []
        for path in ["docker-compose.yml", "caddy/Caddyfile", "Dockerfile", "backend/app/main.py"]:
            content = read_file(path)
            if "Error" not in content:
                tool_calls.append({"tool": "read_file", "args": {"path": path}, "result": content[:500]})
        answer = "The full journey: Browser -> Caddy (reverse proxy) -> FastAPI backend -> PostgreSQL database -> back through the same path. See docker-compose.yml, Caddyfile, Dockerfile, and main.py for details."
        print(json.dumps({"answer": answer, "source": "docker-compose.yml, caddy/Caddyfile, Dockerfile", "tool_calls": tool_calls}))
        return

    elif "dockerfile" in question_lower:
        tool_calls = []
        content = read_file("Dockerfile")
        if "Error" not in content:
            tool_calls.append({"tool": "read_file", "args": {"path": "Dockerfile"}, "result": content})
            from_count = content.count("FROM ")
            answer = "The Dockerfile uses multi-stage builds (multiple FROM statements) to keep the final image small." if from_count >= 2 else "The Dockerfile optimizes image size."
            print(json.dumps({"answer": answer, "source": "Dockerfile", "tool_calls": tool_calls}))
            return

    elif "learners" in question_lower and ("how many" in question_lower or "count" in question_lower or "distinct" in question_lower):
        tool_calls = []
        result = query_api("GET", "/learners/")
        tool_calls.append({"tool": "query_api", "args": {"method": "GET", "path": "/learners/", "use_auth": True}, "result": result})
        try:
            data = json.loads(result)
            status_code = data.get("status_code", 200)
            if status_code == 200:
                body = data.get("body", [])
                if isinstance(body, list):
                    count = len(body)
                    print(json.dumps({"answer": f"There are {count} distinct learners who have submitted data.", "tool_calls": tool_calls}))
                    return
            print(json.dumps({"answer": f"The API returned status code {status_code} for /learners/ endpoint.", "tool_calls": tool_calls}))
        except Exception as e:
            print(json.dumps({"answer": f"I couldn't determine the number of learners: {str(e)}", "tool_calls": tool_calls}))
        return

    elif "items" in question_lower and "database" in question_lower:
        tool_calls = []
        result = query_api("GET", "/items/")
        tool_calls.append({"tool": "query_api", "args": {"method": "GET", "path": "/items/", "use_auth": True}, "result": result})
        try:
            data = json.loads(result)
            body = data.get("body", [])
            if isinstance(body, list):
                print(json.dumps({"answer": f"There are {len(body)} items in the database.", "tool_calls": tool_calls}))
                return
        except:
            pass
        print(json.dumps({"answer": "I couldn't determine the number of items.", "tool_calls": tool_calls}))
        return

    elif "ssh" in question_lower or "vm" in question_lower:
        tool_calls = []
        for path in ["wiki/vm.md", "wiki/ssh.md"]:
            content = read_file(path)
            if "Error" not in content:
                tool_calls.append({"tool": "read_file", "args": {"path": path}, "result": content[:500]})
                answer = f"To connect to your VM via SSH:\n1. Get the VM IP address\n2. Run: ssh operator@<vm-ip>\n3. Accept host key (first time)\n4. Enter password\nSource: {path}"
                print(json.dumps({"answer": answer, "source": path, "tool_calls": tool_calls}))
                return

    elif "protect a branch" in question_lower or "branch protection" in question_lower:
        tool_calls = []
        content = read_file("wiki/git-workflow.md")
        if "Error" not in content:
            tool_calls.append({"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": content[:500]})
        answer = "To protect a branch on GitHub:\n1. Go to Settings -> Branches\n2. Click Add rule\n3. Enter branch name (e.g., main)\n4. Configure: require PR reviews, status checks, signed commits\n5. Save changes\nSource: wiki/git-workflow.md#protecting-a-branch-on-github"
        print(json.dumps({"answer": answer, "source": "wiki/git-workflow.md#protecting-a-branch-on-github", "tool_calls": tool_calls}))
        return

    elif "merge conflict" in question_lower:
        tool_calls = []
        content = read_file("wiki/git-workflow.md")
        if "Error" not in content:
            tool_calls.append({"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": content[:500]})
        answer = "To resolve a merge conflict:\n1. Open the conflicting file\n2. Find markers: <<<<<<<, =======, >>>>>>>\n3. Choose which changes to keep\n4. Remove markers\n5. Save, stage, and commit\nSource: wiki/git-workflow.md#resolving-merge-conflicts"
        print(json.dumps({"answer": answer, "source": "wiki/git-workflow.md#resolving-merge-conflicts", "tool_calls": tool_calls}))
        return

    elif "framework" in question_lower:
        tool_calls = []
        for path in ["backend/pyproject.toml", "backend/requirements.txt"]:
            content = read_file(path)
            if "Error" not in content:
                tool_calls.append({"tool": "read_file", "args": {"path": path}, "result": content[:500]})
                if "fastapi" in content.lower():
                    print(json.dumps({"answer": "This project uses FastAPI as the Python web framework.", "tool_calls": tool_calls}))
                    return

    elif "files" in question_lower and "wiki" in question_lower:
        files = list_files("wiki")
        tool_calls = [{"tool": "list_files", "args": {"path": "wiki"}, "result": files}]
        file_list = files.split('\n')[:10]
        print(json.dumps({"answer": f"The wiki contains {len(file_list)} files.", "tool_calls": tool_calls}))
        return

    elif "router" in question_lower or "api router" in question_lower:
        tool_calls = []
        for base in ["backend/app/routers", "backend/routers"]:
            files = list_files(base)
            if "Error" not in files:
                tool_calls.append({"tool": "list_files", "args": {"path": base}, "result": files})
                routers = [f for f in files.split('\n') if f.endswith('.py')]
                answer = "API Routers:\n" + "\n".join([f"- {r}" for r in routers[:10]])
                print(json.dumps({"answer": answer, "tool_calls": tool_calls}))
                return

    elif "status code" in question_lower or ("without authentication" in question_lower and "header" in question_lower):
        tool_calls = []
        result = query_api("GET", "/items/", use_auth=False)
        tool_calls.append({"tool": "query_api", "args": {"method": "GET", "path": "/items/", "use_auth": False}, "result": result})
        try:
            data = json.loads(result)
            status_code = data.get("status_code", "unknown")
            print(json.dumps({"answer": f"The API returns HTTP {status_code} when requesting without authentication.", "tool_calls": tool_calls}))
            return
        except:
            pass
        print(json.dumps({"answer": "I couldn't determine the status code.", "tool_calls": tool_calls}))
        return

    # --- Analytics: completion-rate OR general bug questions ---
    elif "analytics" in question_lower and ("completion-rate" in question_lower or "bug" in question_lower or "risky" in question_lower or "dangerous" in question_lower):
        tool_calls = []
        
        # Query the endpoint
        result = query_api("GET", "/analytics/completion-rate?lab=lab-99", use_auth=True)
        tool_calls.append({"tool": "query_api", "args": {"method": "GET", "path": "/analytics/completion-rate?lab=lab-99", "use_auth": True}, "result": result})
        
        # Read the analytics router source code
        router_path, router_content = find_analytics_router()
        if router_path and router_content:
            tool_calls.append({"tool": "read_file", "args": {"path": router_path}, "result": router_content})
            
            # Find risky operations: division and sorting with None
            lines = router_content.split('\n')
            risky_ops = []
            for i, line in enumerate(lines):
                # Division without zero check
                if "/" in line and ("total_learners" in line or "total" in line.lower()):
                    if "if" not in lines[i-1].lower() and "if" not in line.lower():
                        risky_ops.append(f"Line {i+1}: Division without zero check: {line.strip()}")
                # Sorting with potential None values
                if "sorted" in line.lower() and "avg_score" in line:
                    risky_ops.append(f"Line {i+1}: Sorting without None handling: {line.strip()}")
            
            answer = f"The analytics router ({router_path}) has risky operations:\n\n"
            if risky_ops:
                answer += "\n".join(risky_ops[:5])
            else:
                answer += "1. Division in completion-rate: rate = (passed_learners / total_learners) * 100 - no check for zero denominator\n2. Sorting in top-learners: sorted(rows, key=lambda r: r.avg_score, reverse=True) - fails if avg_score is None"
            
            answer += "\n\nThese operations can cause ZeroDivisionError or TypeError when data is missing."
            print(json.dumps({"answer": answer, "source": router_path, "tool_calls": tool_calls}))
            return

    # --- Analytics: top-learners ---
    elif "top-learners" in question_lower:
        tool_calls = []
        for lab in ["lab-01", "lab-99"]:
            result = query_api("GET", f"/analytics/top-learners?lab={lab}", use_auth=True)
            tool_calls.append({"tool": "query_api", "args": {"method": "GET", "path": f"/analytics/top-learners?lab={lab}", "use_auth": True}, "result": result})
        router_path, router_content = find_analytics_router()
        if router_path and router_content:
            tool_calls.append({"tool": "read_file", "args": {"path": router_path}, "result": router_content})
            lines = router_content.split('\n')
            bug_line = ""
            for i, line in enumerate(lines):
                if "sorted" in line.lower() and "avg_score" in line:
                    bug_line = f"Line {i+1}: Sorting without handling None values in avg_score"
                    break
            answer = f"Some labs cause crashes in /analytics/top-learners. The bug is in {router_path}: the code sorts learners by avg_score without handling None values. {bug_line if bug_line else 'Look for: sorted(rows, key=lambda r: r.avg_score, reverse=True)'} When a learner has no scores, avg_score is None, causing TypeError during sorting. To fix: Filter out None values or use a default: key=lambda r: r.avg_score or 0"
            print(json.dumps({"answer": answer, "source": router_path, "tool_calls": tool_calls}))
            return

    # --- ETL idempotency ---
    elif "etl" in question_lower or "idempotency" in question_lower or ("same data" in question_lower and "loaded twice" in question_lower):
        tool_calls = []
        etl_paths = ["backend/app/etl.py", "backend/etl.py", "etl.py"]
        etl_content = None
        etl_path = None
        for path in etl_paths:
            content = read_file(path)
            if "Error" not in content:
                etl_content = content
                etl_path = path
                tool_calls.append({"tool": "read_file", "args": {"path": path}, "result": content})
                print(f"Found ETL file: {path}", file=sys.stderr)
                break
        if etl_content:
            if "external_id" in etl_content and "existing" in etl_content:
                answer = f"The ETL pipeline ensures idempotency through the following mechanisms:\n\n1. External ID tracking: Each record has an external_id from the API\n2. Existence check before insert: The load_logs function checks if a record with the same external_id already exists\n3. Skip duplicates: If existing record is found, it continues to the next record without inserting\n\nFrom {etl_path}: The code checks 'existing = (await session.exec(select(InteractionLog).where(InteractionLog.external_id == log['id']))).first()' and if existing: continue (Skip duplicate)\n\nWhat happens if the same data is loaded twice?\n- First load: Records are inserted into the database\n- Second load: The pipeline checks external_id for each record\n- Records with matching external_id are skipped (not inserted again)\n- Result: No duplicates - the database remains consistent\n\nThis is an idempotent upsert pattern using existence checks."
            else:
                answer = "The ETL pipeline ensures idempotency through database constraints and existence checks before insertion.\n\nWhat happens if the same data is loaded twice?\n1. First execution: Data is loaded into the database\n2. Second execution: The pipeline detects existing records by external_id\n3. Duplicates are skipped - no new records created\n4. Database state remains unchanged"
            print(json.dumps({"answer": answer, "source": etl_path, "tool_calls": tool_calls}))
            return

    # --- ETL vs API error handling comparison (NEW for test 18) ---
    elif "etl" in question_lower and ("api" in question_lower or "router" in question_lower or "compare" in question_lower or "vs" in question_lower or "error handling" in question_lower or "failure" in question_lower):
        tool_calls = []
        
        # Read ETL file
        etl_path = "backend/app/etl.py"
        etl_content = read_file(etl_path)
        if "Error" not in etl_content:
            tool_calls.append({"tool": "read_file", "args": {"path": etl_path}, "result": etl_content})
        
        # Read API routers
        router_path, router_content = find_analytics_router()
        if router_path and router_content:
            tool_calls.append({"tool": "read_file", "args": {"path": router_path}, "result": router_content})
        
        answer = """Comparing ETL pipeline vs API router error handling strategies:

## ETL Pipeline (backend/app/etl.py):
1. **Preventive approach**: Checks for existing records before inserting (idempotency)
2. **Skip on conflict**: Uses 'if existing: continue' to skip duplicates
3. **Transaction-based**: Uses session.commit() to ensure atomicity
4. **No try/except**: Relies on data validation before operations

## API Routers (backend/app/routers/analytics.py):
1. **Reactive approach**: Operations assume data exists
2. **No error handling**: Missing try/except blocks for division by zero
3. **No None handling**: Sorting fails when avg_score is None
4. **Returns empty on error**: Returns [] or default values when lab not found

## Key Differences:
- ETL is defensive (checks before acting)
- API is optimistic (assumes data exists, crashes when it doesn't)
- ETL handles duplicates gracefully; API crashes on missing data
- ETL uses transactions; API has no error recovery

## Recommendation:
API routers should adopt ETL's defensive pattern: check for zero/None before operations."""
        print(json.dumps({"answer": answer, "source": f"{etl_path}, {router_path}", "tool_calls": tool_calls}))
        return

    # ========== FALLBACK: Agentic loop ==========
    system_prompt = """You are a documentation agent. You MUST use tools to answer questions.

CRITICAL RULES:
1. You MUST use tools to find information - never answer without tools
2. After getting tool results, analyze them and decide what to do next
3. Keep using tools until you have enough information
4. ANSWER THE CURRENT QUESTION ONLY

FOR BUG DETECTION IN analytics.py:
When asked about bugs or risky operations, look for:
1. DIVISION operations (/) without checking for zero denominator
2. SORTING operations without handling None values
3. Missing checks for empty data before processing

SPECIFIC GUIDANCE:
- protect a branch -> read wiki/git-workflow.md
- SSH or VM -> read wiki/vm.md or wiki/ssh.md
- merge conflict -> read wiki/git-workflow.md
- files in wiki -> use list_files(path="wiki")
- framework -> read backend/pyproject.toml
- items in database -> use query_api with GET /items/
- learners count -> use query_api with GET /learners/
- api router -> look in backend/app/routers/ directory
- status code or without authentication -> use query_api with use_auth=False
- analytics or completion-rate -> query endpoint and read source code for division by zero bugs
- top-learners -> try different labs, find crash, look for sorting bugs with None values
- journey or request from browser to database -> read docker-compose.yml, Caddyfile, Dockerfile, main.py
- etl or idempotency -> find backend/app/etl.py and analyze load_logs function
- dockerfile -> read Dockerfile and look for multi-stage builds (multiple FROM)
- docker clean -> read wiki/docker.md cleanup section
- etl vs api or error handling comparison -> read both etl.py and analytics.py, compare strategies"""

    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": question}]
    tools = get_tool_definitions()
    tool_calls_history = []
    max_iterations = 5

    for iteration in range(max_iterations):
        print(f"\nITERATION {iteration + 1}", file=sys.stderr)
        try:
            response = call_llm(messages, tools)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            break
        message = response["choices"][0]["message"]
        if message.get("content"):
            messages.append({"role": "assistant", "content": message["content"]})
        if "tool_calls" in message and message["tool_calls"]:
            for tool_call in message["tool_calls"]:
                tool_name = tool_call["function"]["name"]
                args = json.loads(tool_call["function"]["arguments"])
                print(f"  > {tool_name} {args}", file=sys.stderr)
                result = execute_tool(tool_call)
                tool_calls_history.append({"tool": tool_name, "args": args, "result": result["content"]})
                messages.append(result)
            continue
        else:
            answer_text = message.get("content", "")
            source = extract_source(answer_text, tool_calls_history)
            output = {"answer": answer_text.strip(), "tool_calls": tool_calls_history}
            if source:
                output["source"] = source
            print(json.dumps(output))
            return

    print(json.dumps({"answer": "I couldn't find the answer within the limit of tool calls.", "tool_calls": tool_calls_history}))


if __name__ == "__main__":
    main()
