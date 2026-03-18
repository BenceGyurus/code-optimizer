import json
import subprocess
from typing import List
from hunter import CodeMatch

def run_ruff_linter(file_path: str) -> List[CodeMatch]:
    """Runs ruff linter on the file and returns a list of CodeMatch objects."""
    try:
        # Run ruff check with JSON output
        result = subprocess.run(
            ["ruff", "check", "--format", "json", "--select", "ALL", file_path],
            capture_output=True,
            text=True
        )
        
        # If there are no issues, ruff will exit with 0, but we still parse the output
        if not result.stdout:
            return []
            
        issues = json.loads(result.stdout)
        matches = []
        
        # Load the source lines for snippet extraction
        with open(file_path, "r") as f:
            source_lines = f.readlines()
            
        for issue in issues:
            # We skip some very minor issues or issues that don't need fixing
            if issue["code"].startswith("D"): # Documentation
                continue
            
            # Extract line range (ruff usually gives single lines, we take 1 line context)
            start = issue["location"]["row"]
            end = issue["end_location"]["row"]
            
            # Ensure we get at least the line itself
            snippet = "".join(source_lines[start-1:end])
            indent = len(source_lines[start-1]) - len(source_lines[start-1].lstrip())

            matches.append(CodeMatch(
                rule_id=f"static_analysis_issue ({issue['code']}: {issue['message']})",
                start_line=start,
                end_line=end,
                snippet=snippet.strip(),
                indent=indent
            ))
            
        return matches
    except Exception as e:
        # If ruff is not installed or fails, return empty list
        print(f"Warning: Ruff linter failed: {e}")
        return []
