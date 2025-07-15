import re
import json

def extract_json_from_llm_response(response_text):
    """
    Extract JSON (object or array) from an LLM response text and convert it to a Python value.
    
    Args:
        response_text (str): The text response from an LLM that contains JSON.
        
    Returns:
        object: The extracted JSON as a Python dict/list/etc.
                Returns None if no valid JSON is found.
    """
    # Find the first opening brace or bracket
    start_match = re.search(r'[\{\[]', response_text)
    if not start_match:
        return None
    
    start = start_match.start()
    opener = response_text[start]
    closer = '}' if opener == '{' else ']'
    
    # Walk forward, counting nested openers/closers
    depth = 0
    for i, ch in enumerate(response_text[start:], start):
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                candidate = response_text[start:i+1]
                break
    else:
        # never closed
        return None
    
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None
