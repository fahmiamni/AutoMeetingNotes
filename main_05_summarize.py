import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenAI API Key from environment
API_KEY = os.getenv('OPENAI_API_KEY')
if not API_KEY:
    print("Error: OPENAI_API_KEY not found in environment variables.")
    exit(1)

# Input and output directories
input_file = os.path.join('output', '02_transcription.md')
output_dir = 'output'

# Read the content
if not os.path.isfile(input_file):
    print(f"No transcription file found at {input_file}.")
    exit(1)

with open(input_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Prepare the API request for summarization
url = 'https://api.openai.com/v1/chat/completions'
headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
}
data = {
    'model': 'gpt-4o-mini',  # Using OpenAI's GPT-4o mini model
    'messages': [
        {'role': 'user', 'content': f'Please summarize the following text:\n\n{content}'}
    ],
    'max_tokens': 1000  # Adjust as needed
}

# Make the API call
response = requests.post(url, headers=headers, json=data)

if response.status_code == 200:
    result = response.json()
    summary = result['choices'][0]['message']['content']
    
    # Save the summary to a fixed output filename
    output_filename = '05_summarize.md'
    output_file = os.path.join(output_dir, output_filename)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(summary)
    
    print(f"Summary generated and saved to {output_file}")
else:
    print(f"Error: {response.status_code} - {response.text}")