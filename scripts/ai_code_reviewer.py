import os
import requests
import json
import time

def fetch_diff(pr_url, github_token):
    headers = {'Authorization': f'token {github_token}', 'Accept': 'application/vnd.github.v3+json'}
    response = requests.get(pr_url + "/files", headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch PR diff. Status: {response.status_code}, URL: {pr_url}, Response: {response.text}")
    files = response.json()
    return ''.join(file.get('patch', '') for file in files)

def review_code(diff, openai_api_key, retries=5):
    headers = {'Authorization': f'Bearer {openai_api_key}', 'Content-Type': 'application/json'}
    data = {
        "model": "gpt-3.5-turbo-instruct-0914",
        "messages": [{"role": "system", "content": "You are a code reviewer."},
                     {"role": "user", "content": f"Review the following code diff and suggest improvements:\n{diff}"}],
        "max_tokens": 800, "temperature": 0.5
    }
    for attempt in range(retries):
        try:
            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
            if response.status_code == 200:
                ai_response = response.json()
                print(f"OpenAI API Usage: {ai_response.get('usage', {})}")
                return ai_response['choices'][0]['message']['content'].strip()
            elif response.status_code == 429:
                wait_time = int(response.headers.get('Retry-After', 10))
                print(f"Rate limit exceeded. Retrying after {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise Exception(f"OpenAI Error: {response.status_code}, {response.text}")
        except Exception as e:
            print(f"Request failed: {e}")
    return "Fallback comments due to API issues."

def post_comment(pr_url, comment, github_token):
    issue_number = pr_url.split('/')[-1]
    comments_url = f"https://api.github.com/repos/{os.getenv('GITHUB_REPOSITORY')}/issues/{issue_number}/comments"
    headers = {'Authorization': f'token {github_token}', 'Content-Type': 'application/json'}
    response = requests.post(comments_url, headers=headers, json={"body": comment})
    if response.status_code != 201:
        raise Exception(f"Failed to post comment: {response.status_code}, {response.text}")

def main():
    pr_url = os.getenv("GITHUB_PR_URL")
    github_token = os.getenv("GITHUB_TOKEN")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    print(f"PR URL: {pr_url if pr_url else 'Not provided'}")
    print(f"GitHub Token: {'Provided' if github_token else 'Missing'}")
    print(f"OpenAI API Key: {'Provided' if openai_api_key else 'Missing'}")
    if not all([pr_url, github_token, openai_api_key]):
        print("Error: Missing environment variables.")
        return
    try:
        diff = fetch_diff(pr_url, github_token)
        ai_review = review_code(diff, openai_api_key) or "Fallback comments."
        post_comment(pr_url, ai_review, github_token)
        print("AI review posted successfully.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
