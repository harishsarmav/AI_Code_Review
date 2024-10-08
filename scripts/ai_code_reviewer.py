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
def review_code(diff, openai_api_key, retries=5):
    headers = {
        'Authorization': f'Bearer {openai_api_key}',
        'Content-Type': 'application/json'
    }
    data = {
        "model": "gpt-3.5-turbo-instruct-0914",  # Model with better request limits
        "messages": [
            {"role": "system", "content": "You are a code reviewer."},
            {"role": "user", "content": f"Review the following code diff and suggest improvements:\n{diff}"}
        ],
        "max_tokens": 1500,  # Monitor token usage to avoid hitting limits
        "temperature": 0.5
    }

    attempt = 0
    initial_delay = 60  # Start with a 60-second delay
    while attempt < retries:
        try:
            start_time = time.time()
            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
            end_time = time.time()

            response_time = end_time - start_time
            print(f"API Response Time: {response_time} seconds")

            if response.status_code == 200:
                ai_response = response.json()
                print(f"Used tokens: {ai_response['usage']['total_tokens']}")  # Monitor token usage
                return ai_response['choices'][0]['message']['content'].strip()
            elif response.status_code == 429:
                # Check the rate-limit reset time from headers, if available
                reset_time = response.headers.get('Retry-After', initial_delay)
                print(f"Received 429 error from OpenAI. Retrying after {reset_time} seconds (attempt {attempt + 1}/{retries}).")
                time.sleep(int(reset_time))  # Wait for the suggested time or fallback to initial delay
                attempt += 1
            else:
                print(f"Error from OpenAI: {response.status_code}, {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None

    print("Exceeded retry limit. Falling back to manual review suggestions.")
    return None

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
    
    # Get AI code review from OpenAI
    try:
        ai_review = review_code(diff, openai_api_key)
        if ai_review is None:
            ai_review = fallback_comment()
            print("Received 429 error from OpenAI. Providing fallback comments.")
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
