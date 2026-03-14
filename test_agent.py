#!/usr/bin/env python3
"""
Regression test for agent.py
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
    
    # Check exit code
    assert result.returncode == 0
    
    # Parse stdout as JSON
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        assert False, "Output is not valid JSON"
    
    # Check required fields
    assert "answer" in output
    assert "tool_calls" in output
    assert isinstance(output["tool_calls"], list)
    
    # Check that answer is not empty
    assert output["answer"].strip() != ""


if __name__ == "__main__":
    test_agent_basic()
    print("All tests passed!")
