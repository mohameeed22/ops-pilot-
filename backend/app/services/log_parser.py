import re
import os
import logging

logger = logging.getLogger("log_parser")

# Regex compilation
PYTHON_TRACEBACK_RE = re.compile(
    r'(Traceback \(most recent call last\):.*?\n)(?P<error>(?P<error_type>\w+Error|AssertionError|Exception|KeyError|IndexError|TypeError): (?P<error_msg>[^\n]*))',
    re.DOTALL
)
PYTHON_FILE_RE = re.compile(
    r'File "(?P<filename>[^"]+)", line (?P<line>\d+), in (?P<func>.*)'
)
PYTEST_FAILURE_RE = re.compile(
    r'={3,}\s+FAILURES\s+={3,}\n.*?_+\s+(?P<test_name>test_\w+)\s+_+\n(?P<body>.*?)\n(?P<summary>[a-zA-Z0-9_\-\./\\]+\.py):(?P<line>\d+): (?P<error_type>\w+Error|AssertionError)(?:: (?P<error_msg>.*))?',
    re.DOTALL
)
PYTEST_SIMPLE_SUMMARY_RE = re.compile(
    r'^(?P<filename>[a-zA-Z0-9_\-\./\\]+\.py):(?P<line>\d+):\s*(?P<error_type>\w+Error|AssertionError|Exception)(?::\s*(?P<error_msg>.*))?$',
    re.MULTILINE
)

NODE_STACK_RE = re.compile(
    r'(?P<error_type>\w*Error|Error|TypeError|ReferenceError): (?P<error_msg>.*?)\n(?P<stack>(?:\s+at .*?\n)+)',
    re.DOTALL
)
NODE_FRAME_RE = re.compile(
    r'at (?P<func>[^\s(]+)?\s*\(?(?P<filename>[^:]+):(?P<line>\d+):(?P<col>\d+)\)?'
)

# e.g., src/main.go:12:3: undefined: fmt.Println
# e.g., src/main.cpp:25: error: expected ';' before '}'
COMPILER_ERROR_RE = re.compile(
    r'^(?P<filename>[a-zA-Z0-9_\-\./\\]+\.[a-zA-Z0-9]+):(?P<line>\d+):(?P<col>\d+)?:?\s*(?:error|FAIL|failed):\s*(?P<error_msg>.*)$',
    re.MULTILINE
)


def parse_python_error(log_text: str) -> dict | None:
    """Parses standard Python tracebacks or Pytest failure logs."""
    # Try Pytest summary first (more specific for test runners)
    pytest_summary_matches = list(PYTEST_SIMPLE_SUMMARY_RE.finditer(log_text))
    if pytest_summary_matches:
        # Get the last match, which usually points to the actual test assert
        match = pytest_summary_matches[-1]
        return {
            "language": "python",
            "filename": match.group("filename"),
            "line_number": int(match.group("line")),
            "error_type": match.group("error_type"),
            "error_message": (match.group("error_msg") or "").strip(),
            "traceback": match.group(0),
        }

    # Try standard Python Tracebacks
    tb_matches = list(PYTHON_TRACEBACK_RE.finditer(log_text))
    if tb_matches:
        # Get the last traceback (most likely the culprit exception)
        tb_match = tb_matches[-1]
        traceback_text = tb_match.group(0)
        
        # Search for file entries in the traceback
        file_matches = list(PYTHON_FILE_RE.finditer(traceback_text))
        if file_matches:
            # The last file match in Python traceback points to the exact failing line
            file_match = file_matches[-1]
            return {
                "language": "python",
                "filename": file_match.group("filename"),
                "line_number": int(file_match.group("line")),
                "error_type": tb_match.group("error_type"),
                "error_message": tb_match.group("error_msg").strip(),
                "traceback": traceback_text.strip(),
            }
            
    return None


def parse_node_error(log_text: str) -> dict | None:
    """Parses V8 / Node.js error tracebacks."""
    node_matches = list(NODE_STACK_RE.finditer(log_text))
    if node_matches:
        node_match = node_matches[-1]
        stack_text = node_match.group("stack")
        
        # Parse the frames in the stack
        frame_matches = list(NODE_FRAME_RE.finditer(stack_text))
        if frame_matches:
            # We want to ignore frames inside node_modules or node internals
            target_frame = None
            for frame in frame_matches:
                filename = frame.group("filename")
                if "node_modules" not in filename and "node:" not in filename and "<anonymous>" not in filename:
                    target_frame = frame
                    break
            
            # Fallback to the first frame if all are external/internal
            if not target_frame:
                target_frame = frame_matches[0]
                
            return {
                "language": "javascript",
                "filename": target_frame.group("filename"),
                "line_number": int(target_frame.group("line")),
                "error_type": node_match.group("error_type"),
                "error_message": node_match.group("error_msg").strip(),
                "traceback": node_match.group(0).strip(),
            }
            
    return None


def parse_compiler_error(log_text: str) -> dict | None:
    """Parses GCC, Go, Clang compiler errors or generic file:line failures."""
    compiler_matches = list(COMPILER_ERROR_RE.finditer(log_text))
    if compiler_matches:
        # Return the first compiler error (since compiler cascade causes subsequent ones)
        match = compiler_matches[0]
        filename = match.group("filename")
        
        # Simple cleanup to exclude common build tool summaries
        if "Makefile" in filename or "package.json" in filename:
            if len(compiler_matches) > 1:
                match = compiler_matches[1]
                filename = match.group("filename")
            else:
                return None

        return {
            "language": "compiler",
            "filename": filename,
            "line_number": int(match.group("line")),
            "error_type": "CompileError",
            "error_message": match.group("error_msg").strip(),
            "traceback": match.group(0).strip(),
        }
        
    return None


def parse_log_text(log_text: str) -> dict | None:
    """Scans raw log text and attempts to parse it using standard formats."""
    # Clean control characters (like ansi color codes ESC[31m etc) which break regexes
    clean_text = re.sub(r'\x1b\[[0-9;]*[mGKH]', '', log_text)

    # 1. Try Python
    result = parse_python_error(clean_text)
    if result:
        return result

    # 2. Try Node.js
    result = parse_node_error(clean_text)
    if result:
        return result

    # 3. Try Compiler Errors (Go, GCC, etc)
    result = parse_compiler_error(clean_text)
    if result:
        return result

    return None
