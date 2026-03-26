import ast
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class CodeMatch:
    rule_id: str
    start_line: int
    end_line: int
    snippet: str
    indent: int

class CodeHunter(ast.NodeVisitor):
    def __init__(self, source_code: str, rules_config: Dict):
        self.source_lines = source_code.splitlines()
        self.rules_config = rules_config
        self.matches: List[CodeMatch] = []

    def visit_For(self, node: ast.For):
        # RULE PRECEDENCE:
        # 1. Nested Loops (Big Impact: Algorithmic)
        # 2. List Comprehension (Medium Impact: Pythonic)
        # 3. Loop Invariant (Low Impact: Redundancy)

        if any(isinstance(child, ast.For) for child in node.body):
            self._add_match("unnecessary_nested_loops", node)
            return # Skip lower-priority rules for this block

        if self._is_uniqueness_pattern(node):
            self._add_match("unnecessary_nested_loops", node)
            return

        if self._is_list_append_pattern(node):
            self._add_match("list_comprehension", node)
            return 

        self._check_loop_invariants(node)

        self.generic_visit(node)

    def _check_loop_invariants(self, node: ast.For):
        """Simple heuristic for loop invariants."""
        # Loop variables
        loop_vars = set()
        if isinstance(node.target, ast.Name):
            loop_vars.add(node.target.id)
        elif isinstance(node.target, ast.Tuple):
            for elt in node.target.elts:
                if isinstance(elt, ast.Name):
                    loop_vars.add(elt.id)

        for child in node.body:
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        loop_vars.add(target.id)
            elif isinstance(child, ast.AugAssign) and isinstance(child.target, ast.Name):
                loop_vars.add(child.target.id)

        # Walk the body (EXCLUDING the header) and find invariant calls
        for child in node.body:
            for sub_node in ast.walk(child):
                if isinstance(sub_node, ast.Call):
                    if self._is_invariant(sub_node, loop_vars):
                        # Tag the whole loop for the LLM to hoist it
                        self._add_match("loop_invariant_redundancy", node)
                        return # One match per loop is enough

    def _is_invariant(self, node: ast.AST, loop_vars: set) -> bool:
        """Check if an expression uses any of the loop variables."""
        for sub_node in ast.walk(node):
            if isinstance(sub_node, ast.Name) and sub_node.id in loop_vars:
                return False
        return True

    def _is_list_append_pattern(self, node: ast.For) -> bool:
        # Simplistic heuristic: body has 1 statement, or 1 if with 1 append
        body = node.body
        if len(body) == 1:
            if isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Call):
                return self._is_append_call(body[0].value)
            if isinstance(body[0], ast.If) and len(body[0].body) == 1:
                inner = body[0].body[0]
                if isinstance(inner, ast.Expr) and isinstance(inner.value, ast.Call):
                    return self._is_append_call(inner.value)
        return False

    def _is_uniqueness_pattern(self, node: ast.For) -> bool:
        body = node.body
        if len(body) != 1:
            return False
        if_node = body[0]
        if not isinstance(if_node, ast.If) or if_node.orelse:
            return False
        if len(if_node.body) != 1:
            return False
        test = if_node.test
        if not isinstance(test, ast.Compare) or len(test.ops) != 1:
            return False
        if not isinstance(test.ops[0], ast.NotIn):
            return False
        if len(test.comparators) != 1:
            return False
        left = test.left
        right = test.comparators[0]
        if not isinstance(left, ast.Name) or not isinstance(right, ast.Name):
            return False
        inner = if_node.body[0]
        if not isinstance(inner, ast.Expr) or not isinstance(inner.value, ast.Call):
            return False
        call = inner.value
        if not (isinstance(call.func, ast.Attribute) and call.func.attr == "append"):
            return False
        if not isinstance(call.func.value, ast.Name):
            return False
        if call.func.value.id != right.id:
            return False
        return True

    def _is_append_call(self, call: ast.Call) -> bool:
        return (isinstance(call.func, ast.Attribute) and 
                call.func.attr == 'append')

    def _add_match(self, rule_id: str, node: ast.AST):
        start = node.lineno
        end = node.end_lineno
        snippet = "\n".join(self.source_lines[start-1:end])
        indent = len(self.source_lines[start-1]) - len(self.source_lines[start-1].lstrip())
        
        self.matches.append(CodeMatch(
            rule_id=rule_id,
            start_line=start,
            end_line=end,
            snippet=snippet,
            indent=indent
        ))

def scan_file(file_path: str, rules_config: Dict) -> List[CodeMatch]:
    with open(file_path, "r") as f:
        source = f.read()
    
    tree = ast.parse(source)
    hunter = CodeHunter(source, rules_config)
    hunter.visit(tree)
    return hunter.matches
