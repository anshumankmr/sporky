import re
import json
from typing import Dict, Any, Optional, Union, List, Tuple


def extract_json_from_llm(text: str) -> Dict[str, Any]:
    """
    Extract and parse JSON from LLM-generated text, handling common pitfalls.
    
    Args:
        text (str): The text containing JSON, potentially with various issues
        
    Returns:
        Dict[str, Any]: The parsed JSON as a Python dictionary
        
    Raises:
        ValueError: If no valid JSON could be extracted after all attempts
    """
    # Strip any markdown code block formatting
    text = strip_code_blocks(text)
    
    # Try to extract JSON from the text if it's embedded in other content
    json_str = extract_json_string(text)
    
    # Series of cleanup and correction attempts
    cleaning_functions = [
        try_direct_parse,              # Try parsing as-is first
        fix_trailing_commas,           # Fix trailing commas in objects/arrays
        fix_missing_quotes_on_keys,    # Fix unquoted dictionary keys
        fix_single_quotes,             # Replace single quotes with double quotes
        fix_javascript_booleans,       # Convert True/False to true/false
        fix_dangling_commas,           # Fix commas before closing brackets
        fix_multi_line_strings,        # Handle improper line breaks in strings
        fix_incorrect_escaping,        # Fix common escaping issues
        fix_non_json_content,          # Try more aggressive extraction
        reconstruct_minimal_json       # Last resort: build minimal valid JSON
    ]
    
    last_error = None
    for clean_func in cleaning_functions:
        try:
            result = clean_func(json_str)
            if result is not None:
                return result
        except Exception as e:
            last_error = e
            continue
    
    # If we've made it here, we couldn't parse the JSON
    raise ValueError(f"Could not extract valid JSON after all attempts. Last error: {last_error}")


def strip_code_blocks(text: str) -> str:
    """Remove markdown code block markers."""
    # Remove ```json and ``` markers
    text = re.sub(r'```(?:json|javascript|js|)\s*\n', '', text)
    text = re.sub(r'\n\s*```\s*$', '', text)
    return text.strip()


def extract_json_string(text: str) -> str:
    """Extract JSON string from text, looking for the largest {...} or [...] block."""
    # Look for the outermost JSON object or array
    object_matches = list(re.finditer(r'({(?:[^{}]|(?R))*})', text, re.DOTALL))
    array_matches = list(re.finditer(r'(\[(?:[^\[\]]|(?R))*\])', text, re.DOTALL))
    
    # If regex with recursion isn't supported, fall back to simpler but less reliable method
    if not object_matches:
        object_matches = list(re.finditer(r'{[^{}]*(?:{[^{}]*}[^{}]*)*}', text, re.DOTALL))
    if not array_matches:
        array_matches = list(re.finditer(r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]', text, re.DOTALL))
    
    # Combine matches and find the longest one
    all_matches = object_matches + array_matches
    if all_matches:
        longest_match = max(all_matches, key=lambda match: len(match.group(0)))
        return longest_match.group(0)
    
    return text  # Return the whole text if no clear JSON block is found


def try_direct_parse(json_str: str) -> Optional[Dict[str, Any]]:
    """Attempt to parse the string directly."""
    try:
        return json.loads(json_str)
    except:
        return None


def fix_trailing_commas(json_str: str) -> Optional[Dict[str, Any]]:
    """Fix trailing commas in objects and arrays."""
    # Replace ",}" with "}" and ",]" with "]"
    corrected = re.sub(r',\s*}', '}', json_str)
    corrected = re.sub(r',\s*\]', ']', corrected)
    
    try:
        return json.loads(corrected)
    except:
        return None


def fix_missing_quotes_on_keys(json_str: str) -> Optional[Dict[str, Any]]:
    """Fix unquoted dictionary keys."""
    # Match keys that aren't quoted
    corrected = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)
    
    try:
        return json.loads(corrected)
    except:
        return None


def fix_single_quotes(json_str: str) -> Optional[Dict[str, Any]]:
    """Replace single quotes with double quotes."""
    # This is more complex than a simple replacement to handle escaped quotes
    # First, replace all unescaped double quotes with a placeholder
    placeholder = "___DOUBLEQUOTE___"
    corrected = json_str.replace('\\"', placeholder)
    
    # Replace all single quotes with double quotes
    corrected = corrected.replace("'", '"')
    
    # Restore the original escaped double quotes
    corrected = corrected.replace(placeholder, '\\"')
    
    try:
        return json.loads(corrected)
    except:
        return None


def fix_javascript_booleans(json_str: str) -> Optional[Dict[str, Any]]:
    """Convert Python True/False to JSON true/false."""
    # Convert Python-style booleans and None to JSON format
    corrected = re.sub(r'\bTrue\b', 'true', json_str)
    corrected = re.sub(r'\bFalse\b', 'false', corrected)
    corrected = re.sub(r'\bNone\b', 'null', corrected)
    
    try:
        return json.loads(corrected)
    except:
        return None


def fix_dangling_commas(json_str: str) -> Optional[Dict[str, Any]]:
    """Fix commas that appear before closing brackets."""
    # More aggressive comma fixing - looking at newlines
    lines = json_str.split('\n')
    for i in range(len(lines)):
        # Fix comma at the end of a line followed by a closing bracket
        if i < len(lines) - 1 and re.search(r',\s*$', lines[i]) and \
           re.match(r'\s*[\}\]]', lines[i+1]):
            lines[i] = re.sub(r',\s*$', '', lines[i])
    
    corrected = '\n'.join(lines)
    
    try:
        return json.loads(corrected)
    except:
        return None


def fix_multi_line_strings(json_str: str) -> Optional[Dict[str, Any]]:
    """Handle improper line breaks in strings."""
    # Find potential multi-line strings and join them
    # This is a simplistic approach; more sophisticated parsing might be needed
    in_string = False
    escape_next = False
    lines = []
    current_line = ""
    
    for char in json_str:
        if char == '\\' and not escape_next:
            escape_next = True
            current_line += char
        elif char == '"' and not escape_next:
            in_string = not in_string
            current_line += char
        elif char == '\n' and in_string:
            current_line += '\\n'  # Replace newline in string with escaped \n
        else:
            escape_next = False
            current_line += char
            if char == '\n' and not in_string:
                lines.append(current_line)
                current_line = ""
    
    if current_line:
        lines.append(current_line)
    
    corrected = ''.join(lines)
    
    try:
        return json.loads(corrected)
    except:
        return None


def fix_incorrect_escaping(json_str: str) -> Optional[Dict[str, Any]]:
    """Fix common escaping issues."""
    # Replace common incorrectly escaped characters
    escapes = {
        r'\\n': r'\n',  # Literal \n to newline
        r'\\t': r'\t',  # Literal \t to tab
        r'\\r': r'\r',  # Literal \r to carriage return
        r'\"': r'"',    # Fix redundant escaping inside already quoted strings
    }
    
    corrected = json_str
    for old, new in escapes.items():
        # Only replace when inside quoted strings
        parts = []
        in_string = False
        current = ""
        i = 0
        
        while i < len(corrected):
            if corrected[i] == '"' and (i == 0 or corrected[i-1] != '\\'):
                if in_string:
                    current = current.replace(old, new)
                parts.append(current)
                current = '"'
                in_string = not in_string
                i += 1
            else:
                current += corrected[i]
                i += 1
        
        if current:
            if in_string:
                current = current.replace(old, new)
            parts.append(current)
        
        corrected = ''.join(parts)
    
    try:
        return json.loads(corrected)
    except:
        return None


def fix_non_json_content(json_str: str) -> Optional[Dict[str, Any]]:
    """Try more aggressive extraction of JSON content."""
    # Look for text that most resembles JSON objects
    candidates = re.findall(r'{[^{]*}', json_str, re.DOTALL)
    
    # Try each candidate
    for candidate in sorted(candidates, key=len, reverse=True):
        try:
            return json.loads(candidate)
        except:
            continue
    
    # Try array candidates too
    candidates = re.findall(r'\[[^\[]*\]', json_str, re.DOTALL)
    for candidate in sorted(candidates, key=len, reverse=True):
        try:
            return json.loads(candidate)
        except:
            continue
    
    return None


def reconstruct_minimal_json(json_str: str) -> Optional[Dict[str, Any]]:
    """Last resort: extract key-value pairs and rebuild a minimal valid JSON."""
    # Extract patterns that look like "key": value pairs
    key_value_pairs = re.findall(r'["\']\s*([^"\']+)\s*["\']\s*:\s*([^,}\]]+)', json_str)
    
    if not key_value_pairs:
        return None
    
    # Build a new JSON object with the extracted pairs
    reconstructed = {}
    
    for key, value in key_value_pairs:
        # Clean the key and value
        key = key.strip()
        value = value.strip()
        
        # Try to convert value to appropriate type
        try:
            # Check if it's a number
            if re.match(r'^-?\d+(\.\d+)?$', value):
                if '.' in value:
                    value = float(value)
                else:
                    value = int(value)
            # Check if it's a boolean or null
            elif value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            elif value.lower() in ('null', 'none'):
                value = None
            # Check if it's a string (with or without quotes)
            elif (value.startswith('"') and value.endswith('"')) or \
                 (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
        except:
            # If conversion fails, keep as string
            pass
        
        reconstructed[key] = value
    
    return reconstructed
