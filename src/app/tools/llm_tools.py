import json
import re

def extract_json_from_llm_response(response_text):
    """
    Extract JSON from an LLM response text and convert it to a Python dictionary.
    
    Args:
        response_text (str): The text response from an LLM that contains JSON.
        
    Returns:
        dict: The extracted JSON as a Python dictionary.
              Returns an empty dict if no valid JSON is found.
    """
    # Find content between curly braces (simple JSON detection)
    json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}'
    json_match = re.search(json_pattern, response_text)
    
    if json_match:
        json_str = json_match.group(0)
        try:
            # Parse the extracted JSON string into a Python dictionary
            json_dict = json.loads(json_str)
            return json_dict
        except json.JSONDecodeError:
            # Return empty dict if JSON parsing fails
            return {}
    else:
        # Return empty dict if no JSON pattern is found
        return {}

