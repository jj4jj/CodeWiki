import re
from pathlib import Path
from typing import List, Tuple
import logging
import traceback
import math

try:
    import tiktoken
except Exception:  # pragma: no cover - optional runtime dependency
    tiktoken = None


logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# ---------------------- Complexity Check --------------------
# ------------------------------------------------------------

def is_complex_module(components: dict[str, any], core_component_ids: list[str]) -> bool:
    files = set()
    for component_id in core_component_ids:
        if component_id in components:
            files.add(components[component_id].file_path)

    result = len(files) > 1

    return result


# ------------------------------------------------------------
# ---------------------- Token Counting ---------------------
# ------------------------------------------------------------

_token_encoder = None
_token_encoder_init_attempted = False
_tokenizer_error_reason = ""
_fallback_warning_logged = False


def _get_token_encoder():
    """Lazily initialize tiktoken encoder to avoid startup-time network dependency."""
    global _token_encoder
    global _token_encoder_init_attempted
    global _tokenizer_error_reason

    if _token_encoder is not None:
        return _token_encoder
    if _token_encoder_init_attempted:
        return None

    _token_encoder_init_attempted = True

    if tiktoken is None:
        _tokenizer_error_reason = "tiktoken is not installed"
        return None

    candidates = (
        ("model", "gpt-4"),
        ("model", "gpt-4o"),
        ("encoding", "cl100k_base"),
    )

    last_error = ""
    for kind, name in candidates:
        try:
            if kind == "model":
                _token_encoder = tiktoken.encoding_for_model(name)
            else:
                _token_encoder = tiktoken.get_encoding(name)
            return _token_encoder
        except Exception as exc:
            last_error = str(exc)

    _tokenizer_error_reason = last_error or "unknown tokenizer initialization error"
    return None


def _estimate_tokens_fallback(text: str) -> int:
    """
    Estimate token count without tiktoken.

    Uses a conservative heuristic so module splitting remains on the safe side.
    """
    if not text:
        return 0

    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", text))
    ascii_count = max(0, len(text) - cjk_count)
    estimate = math.ceil(cjk_count * 1.1 + ascii_count / 3.2)
    return max(1, estimate)

def count_tokens(text: str) -> int:
    """
    Count the number of tokens in a text.
    """
    global _fallback_warning_logged

    encoder = _get_token_encoder()
    if encoder is not None:
        try:
            return len(encoder.encode(text))
        except Exception as exc:
            if not _fallback_warning_logged:
                logger.warning(
                    "Token encoding failed, falling back to heuristic estimation: %s",
                    exc,
                )
                _fallback_warning_logged = True
            return _estimate_tokens_fallback(text)

    if not _fallback_warning_logged:
        reason = _tokenizer_error_reason or "encoder unavailable"
        logger.warning(
            "tiktoken encoder unavailable (%s), using heuristic token estimation.",
            reason,
        )
        _fallback_warning_logged = True

    return _estimate_tokens_fallback(text)


# ------------------------------------------------------------
# ---------------------- Mermaid Validation -----------------
# ------------------------------------------------------------

async def validate_mermaid_diagrams(md_file_path: str, relative_path: str) -> str:
    """
    Validate all Mermaid diagrams in a markdown file.
    
    Args:
        md_file_path: Path to the markdown file to check
        relative_path: Relative path to the markdown file
    Returns:
        "All mermaid diagrams are syntax correct" if all diagrams are valid,
        otherwise returns error message with details about invalid diagrams
    """

    try:
        # Read the markdown file
        file_path = Path(md_file_path)
        if not file_path.exists():
            return f"Error: File '{md_file_path}' does not exist"
        
        content = file_path.read_text(encoding='utf-8')
        
        # Extract all mermaid code blocks
        mermaid_blocks = extract_mermaid_blocks(content)
        
        if not mermaid_blocks:
            return "No mermaid diagrams found in the file"
        
        # Validate each mermaid diagram sequentially to avoid segfaults
        errors = []
        for i, (line_start, diagram_content) in enumerate(mermaid_blocks, 1):
            error_msg = await validate_single_diagram(diagram_content, i, line_start)
            if error_msg:
                errors.append("\n")
                errors.append(error_msg)
        
        # if errors:
        #     logger.debug(f"Mermaid syntax errors found in file: {md_file_path}: {errors}")
        
        if errors:
            return "Mermaid syntax errors found in file: " + relative_path + "\n" + "\n".join(errors)
        else:
            return "All mermaid diagrams in file: " + relative_path + " are syntax correct"
            
    except Exception as e:
        return f"Error processing file: {str(e)}"


def extract_mermaid_blocks(content: str) -> List[Tuple[int, str]]:
    """
    Extract all mermaid code blocks from markdown content.
    
    Returns:
        List of tuples containing (line_number, diagram_content)
    """
    mermaid_blocks = []
    lines = content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for mermaid code block start
        if line == '```mermaid' or line.startswith('```mermaid'):
            start_line = i + 1
            diagram_lines = []
            i += 1
            
            # Collect lines until we find the closing ```
            while i < len(lines):
                if lines[i].strip() == '```':
                    break
                diagram_lines.append(lines[i])
                i += 1
            
            if diagram_lines:  # Only add non-empty diagrams
                diagram_content = '\n'.join(diagram_lines)
                mermaid_blocks.append((start_line, diagram_content))
        
        i += 1
    
    return mermaid_blocks


async def validate_single_diagram(diagram_content: str, diagram_num: int, line_start: int) -> str:
    """
    Validate a single mermaid diagram.
    
    Args:
        diagram_content: The mermaid diagram content
        diagram_num: Diagram number for error reporting
        line_start: Starting line number in the file
        
    Returns:
        Error message if invalid, empty string if valid
    """
    import sys
    import os
    from io import StringIO

    core_error = ""

    compat_errors = lint_mermaid_runtime_compat(diagram_content, diagram_num, line_start)
    if compat_errors:
        return "\n".join(compat_errors)
    
    try:
        from mermaid_parser.parser import parse_mermaid_py
        # logger.debug("Using mermaid-parser-py to validate mermaid diagrams")
    
        try:
            # Redirect stderr to suppress mermaid parser JavaScript errors
            old_stderr = sys.stderr
            sys.stderr = open(os.devnull, 'w')
            
            try:
                json_output = await parse_mermaid_py(diagram_content)
            finally:
                # Restore stderr
                sys.stderr.close()
                sys.stderr = old_stderr
        except Exception as e:
            error_str = str(e)
            
            # Extract the core error information from the exception message
            # Look for the pattern that contains "Parse error on line X:"
            error_pattern = r"Error:(.*?)(?=Stack Trace:|$)"
            match = re.search(error_pattern, error_str, re.DOTALL)
            
            if match:
                core_error = match.group(0).strip()
                core_error = core_error
            else:
                logger.error(f"No match found for error pattern, fallback to mermaid-py\n{error_str}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise Exception(error_str)

    except Exception as e:
        logger.warning("Using mermaid-py to validate mermaid diagrams")
        try:
            import mermaid as md
            # Create Mermaid object and check response
            render = md.Mermaid(diagram_content)
            core_error = render.svg_response.text
            
        except Exception as e:
            return f"  Diagram {diagram_num}: Exception during validation - {str(e)}"

    # Check if response indicates a parse error
    if core_error:
        # Extract line number from parse error and calculate actual line in markdown file
        line_match = re.search(r'line (\d+)', core_error)
        if line_match:
            error_line_in_diagram = int(line_match.group(1))
            actual_line_in_file = line_start + error_line_in_diagram
            newline = '\n'
            return f"Diagram {diagram_num}: Parse error on line {actual_line_in_file}:{newline}{newline.join(core_error.split(newline)[1:])}"
        else:
            return f"Diagram {diagram_num}: {core_error}"
    
    return ""  # No error


def lint_mermaid_runtime_compat(
    diagram_content: str,
    diagram_num: int,
    line_start: int,
) -> List[str]:
    """
    Lightweight lints for patterns that often fail in Mermaid 11.x runtime.

    These checks complement parser-based validation because older parser bindings
    may accept classDiagram signatures that fail in the browser renderer.
    """
    errors: List[str] = []
    lines = diagram_content.splitlines()

    first_non_empty = ""
    for line in lines:
        stripped = line.strip()
        if stripped:
            first_non_empty = stripped
            break

    if not first_non_empty.startswith("classDiagram"):
        return errors

    tuple_return_re = re.compile(r"^[+\-#~][A-Za-z_]\w*\([^)]*\)\s*\([^)]*,[^)]*\)")

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("%%"):
            continue

        if tuple_return_re.search(stripped):
            absolute_line = line_start + i - 1
            errors.append(
                f"Diagram {diagram_num}: Mermaid 11.x compatibility error on line {absolute_line}: "
                f"avoid tuple return signatures in classDiagram methods -> `{stripped}`"
            )

    return errors


if __name__ == "__main__":
    # Test with the provided file
    import asyncio
    test_file = "output/docs/SWE_agent-docs/agent_hooks.md"
    result = asyncio.run(validate_mermaid_diagrams(test_file, "agent_hooks.md"))
    print(result)
