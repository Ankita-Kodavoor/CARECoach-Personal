#!/usr/bin/env python3
"""
Subskill classifier that loads the prompt from a YAML file but keeps the simple implementation. This always assumes that the user made a mistake.
"""

import sys
import os
import yaml
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def load_system_prompt():
    """Load the system prompt from the YAML file"""

    prompt_path = "./prompts/subskill.yml"
    
    if not os.path.exists(prompt_path):
        print(f"Error: Could not find subskill.yml at {prompt_path}", file=sys.stderr)
        raise FileNotFoundError("subskill.yml not found")
        
    print(f"Loading prompt from: {prompt_path}", file=sys.stderr)
    
    with open(prompt_path, 'r') as file:
        yaml_content = yaml.safe_load(file)
        return yaml_content['system_prompt']


def subskill_classifier(utterance_rewind, feedback):
    """Determines the most relevant subskill based on user's utterance."""
    try:
        # Format prompt and make API call
        formatted_prompt = load_system_prompt().format(skill="asking questions", utterance=utterance_rewind, feedback=feedback)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": formatted_prompt},
                {"role": "user", "content": utterance_rewind}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return f"Error determining subskill: {str(e)}"

if __name__ == "__main__":
    # Check if a target utterance was provided
    if len(sys.argv) < 3:
        print("Error: No utterance rewind provided", file=sys.stderr)
        sys.exit(1)
    
    # Get the target utterance
    utterance_rewind = sys.argv[1]
    feedback = sys.argv[2]      
    # Classify and print the result
    subskill = subskill_classifier(utterance_rewind, feedback)
    print(subskill)