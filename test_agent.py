#!/usr/bin/env python3
"""
Regression tests for documentation agent.
"""

import subprocess
import json
import sys


def test_agent_basic():
    """Test that agent returns valid JSON with answer and tool_calls."""
    result = subprocess.run(
        [sys.executable, "agent.py", "What is 2+2?"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        assert False, "Output is not valid JSON"
    
    assert "answer" in output
    assert "source" in output
    assert "tool_calls" in output
    assert isinstance(output["tool_calls"], list)
    assert output["answer"].strip() != ""


def test_agent_merge_conflict():
    """Test merge conflict question - should use read_file."""
    result = subprocess.run(
        [sys.executable, "agent.py", "How do you resolve a merge conflict?"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"STDERR: {result.stderr}", file=sys.stderr)
        assert False, "Output is not valid JSON"
    
    # Debug output
    print(f"Source: {output.get('source', 'MISSING')}", file=sys.stderr)
    
    # Check that tool_calls contains read_file
    tool_names = [tc["tool"] for tc in output["tool_calls"]]
    assert "read_file" in tool_names, f"read_file not in tool calls: {tool_names}"
    
    # More flexible source check
    source = output.get("source", "").lower()
    assert any(term in source for term in ["git-workflow", "git workflow", "merge conflict"]), \
           f"Source '{source}' doesn't contain expected terms"

def test_agent_list_files():
    """Test listing files question - should use list_files."""
    result = subprocess.run(
        [sys.executable, "agent.py", "What files are in the wiki?"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        assert False, "Output is not valid JSON"
    
    # Check that tool_calls contains list_files
    tool_names = [tc["tool"] for tc in output["tool_calls"]]
    assert "list_files" in tool_names


if __name__ == "__main__":
    test_agent_basic()
    test_agent_merge_conflict()
    test_agent_list_files()
    print("All tests passed!")
