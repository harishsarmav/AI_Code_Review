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

# Split the diff into smaller parts for better processing
MAX_DIFF_SIZE = 3000  # Limit diff size per API call

def split_diff(diff, max_size):
    return [diff[i:i + max_size] for i in range(0, len(diff), max_size)]

# Send diff to OpenAI for review with retry mechanism and exponential backoff
def review_code_with_retry(diff, openai_api_key, retries=3, backoff_factor=1):
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

    attempt = 0
    while attempt < retries:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip(), None
        elif response.status_code == 429:
            attempt += 1
            wait_time = backoff_factor * (2 ** attempt)
            print(f"Rate limit hit. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
        else:
            return None, response  # Return None and response for further processing

    return None, response  # If all retries fail

# Post AI review comments back to the PR
def post_comment(pr_url, comment, github_token):
    headers = {
        'Authorization': f'token {github_token}',
        'Content-Type': 'application/json'
    }
    
    # Get the issue number from the PR URL
    issue_number = pr_url.split('/')[-1]  # Extract the PR number from the URL
    comments_url = f'https://api.github.com/repos/{os.getenv("GITHUB_REPOSITORY")}/issues/{issue_number}/comments'

    data = {
        "body": comment
    }

    response = requests.post(comments_url, headers=headers, json=data)
    
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

    # Split the diff if it's too large
    diffs = split_diff(diff, MAX_DIFF_SIZE)
    
    # Process each part of the diff
    full_ai_review = ""
    for idx, part in enumerate(diffs):
        print(f"Reviewing part {idx + 1}/{len(diffs)} of the diff.")
        # Get AI code review from OpenAI with retry
        try:
            ai_review, response = review_code_with_retry(part, openai_api_key)
            if ai_review is None:
                status_code = response.status_code
                if status_code == 429:
                    print("Received 429 error from OpenAI. Providing fallback comments.")
                    ai_review = fallback_comment()
                else:
                    print("Error getting AI review: ", response.json())
                    return
            else:
                print("AI review completed for part", idx + 1)
            full_ai_review += f"\nPart {idx + 1} Review:\n{ai_review}\n"
        except Exception as e:
            print(f"Error getting AI review for part {idx + 1}: {e}")
            return

    # Post AI review comments to the PR
    try:
        post_comment(pr_url, full_ai_review, github_token)
        print("AI review comments posted successfully.")
    except Exception as e:
        print(f"Error posting comment: {e}")

if __name__ == "__main__":
    main()