import os
import requests
import json

# Fetch the PR diff using GitHub API
def fetch_diff(pr_url, github_token):
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    response = requests.get(pr_url + "/files", headers=headers)  # Corrected endpoint for files
    
    if response.status_code == 200:
        files = response.json()
        diff_content = ""
        for file in files:
            diff_content += file.get('patch', '')  # Fetch the diff/patch for each file
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
        "model": "text-davinci-003",
        "prompt": f"Review the following code diff and suggest improvements:\n{diff}",
        "max_tokens": 150,
        "temperature": 0.5
    }

    response = requests.post("https://api.openai.com/v1/completions", headers=headers, json=data)
    
    if response.status_code == 200:
        ai_response = response.json()
        return ai_response['choices'][0]['text'].strip()  # Stripping leading/trailing whitespace
    else:
        raise Exception(f"Failed to get AI review: {response.status_code}, {response.text}")

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
