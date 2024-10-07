import os
import requests
import json
import time

# Fetch the PR diff using GitHub API
def fetch_diff(pr_url, github_token):
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    response = requests.get(pr_url + "/files", headers=headers)
    
    if response.status_code == 200:
        files = response.json()
        diff_content = ""
        for file in files:
            diff_content += file.get('patch', '')
        return diff_content
    else:
        raise Exception(f"Failed to fetch PR diff: {response.status_code}, {response.text}")

# Send diff to OpenAI for review
def review_code(diff, openai_api_key):
    headers = {
        'Authorization': f'Bearer {openai_api_key}',
        'Content-Type': 'application/json'
    }
    data = {
        "model": "gpt-3.5-turbo",  # Updated model
        "messages": [
            {"role": "system", "content": "You are a code reviewer."},
            {"role": "user", "content": f"Review the following code diff and suggest improvements:\n{diff}"}
        ],
        "max_tokens": 150,
        "temperature": 0.5
    }

    payload_size = len(json.dumps(data))
    print(f"Payload Size: {payload_size} bytes")

    start_time = time.time()
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
    end_time = time.time()

    response_time = end_time - start_time
    print(f"API Response Time: {response_time} seconds")

    if response.status_code == 200:
        ai_response = response.json()
        return ai_response['choices'][0]['message']['content'].strip()
    else:
        return None, response  # Return None and response for further processing

# Post AI review comments back to the PR
def post_comment(pr_url, comment, github_token):
    headers = {
        'Authorization': f'token {github_token}',
        'Content-Type': 'application/json'
    }
    data = {
        "body": comment
    }

    response = requests.post(f'{pr_url}/comments', headers=headers, json=data)
    
    if response.status_code != 201:
        raise Exception(f"Failed to post comment: {response.status_code}, {response.text}")

# Fallback function for basic syntax checks
def fallback_comment():
    return (
        "I couldn't analyze the code due to API limits or other issues. "
        "Here are some common areas to check for errors:\n"
        "- Ensure there are no missing semicolons or parentheses.\n"
        "- Check for uninitialized variables.\n"
        "- Look out for memory leaks, especially with dynamic memory allocation.\n"
        "- Review your function declarations and definitions for consistency.\n"
        "Please review your code and try again!"
    )

def main():
    # Fetch necessary environment variables
    pr_url = os.getenv("GITHUB_PR_URL")
    github_token = os.getenv("GITHUB_TOKEN")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    # Debug prints
    print(f"PR URL: {pr_url}")
    print(f"GitHub Token: {github_token[:4]}...")  # Print partial token for security
    print(f"OpenAI API Key: {openai_api_key[:4]}...")

    if not all([pr_url, github_token, openai_api_key]):
        print("Error: Missing environment variables")
        return
    
    # Fetch the PR diff
    try:
        diff = fetch_diff(pr_url, github_token)
        print("PR diff fetched successfully.")
    except Exception as e:
        print(f"Error fetching PR diff: {e}")
        return
    
    # Get AI code review from OpenAI
    try:
        ai_review, response = review_code(diff, openai_api_key)
        if ai_review is None:
            status_code = response.status_code
            if status_code == 429:
                print("Received 429 error from OpenAI. Providing fallback comments.")
                ai_review = fallback_comment()
            else:
                print("Error getting AI review: ", response.json())
                return
        else:
            print("AI review completed.")
    except Exception as e:
        print(f"Error getting AI review: {e}")
        return
    
    # Post AI review comments to the PR
    try:
        post_comment(pr_url, ai_review, github_token)
        print("AI review comments posted successfully.")
    except Exception as e:
        print(f"Error posting comment: {e}")

if __name__ == "__main__":
    main()
