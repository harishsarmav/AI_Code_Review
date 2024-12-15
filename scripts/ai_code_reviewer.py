import os
import requests
import json
import time

def fetch_diff(pr_url, github_token):
    """Fetches the diff of the pull request from GitHub."""
    headers = {'Authorization': f'token {github_token}', 'Accept': 'application/vnd.github.v3+json'}
    try:
        response = requests.get(f"{pr_url}/files", headers=headers)
        response.raise_for_status()
        files = response.json()
        diff = ''.join(file.get('patch', '') for file in files)
        return diff
    except requests.RequestException as e:
        raise Exception(f"Error fetching PR diff: {e}")

def review_code(diff, openai_api_key, retries=3, delay=10):
    """Sends the diff to the OpenAI API for review and retrieves comments."""
    headers = {'Authorization': f'Bearer {openai_api_key}', 'Content-Type': 'application/json'}
    data = {
        "model": "gpt-3.5-turbo-instruct-0914",
        "messages": [
            {"role": "system", "content": "You are a code reviewer."},
            {"role": "user", "content": f"Review the following code diff and suggest improvements:\n{diff}"}
        ],
        "max_tokens": 800,
        "temperature": 0.5
    }

    for attempt in range(1, retries + 1):
        try:
            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)

            # Print the response headers to help debug rate limits
            print("Response Headers:", response.headers)

            if response.status_code == 200:
                ai_response = response.json()
                print(f"OpenAI API Usage: {ai_response.get('usage', {})}")
                return ai_response['choices'][0]['message']['content'].strip()
            elif response.status_code == 429:
                # Check rate limit and calculate wait time
                remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
                reset_time = int(response.headers.get('X-RateLimit-Reset', time.time()))
                
                if remaining == 0:
                    wait_time = max(reset_time - time.time(), delay)
                    print(f"Rate limit exceeded. Retrying in {wait_time}s...")
                    time.sleep(wait_time)  # Wait until the rate limit resets
                else:
                    print(f"Rate limit exceeded. Retrying in {delay}s...")
                    time.sleep(delay)  # Wait for a fixed delay before retrying
            else:
                raise Exception(f"OpenAI Error: {response.status_code}, {response.text}")
        except Exception as e:
            print(f"Attempt {attempt}/{retries} failed: {e}")

     # Fallback response when API fails after retries
    return (
        "AI review unavailable at the moment. Here are some general suggestions:\n\n"
        "1. Ensure proper error handling is in place for edge cases.\n"
        "2. Refactor complex functions into smaller, reusable methods.\n"
        "3. Add comments where the logic might be unclear to others.\n"
        "4. Check for any potential memory leaks or performance issues.\n"
        "5. Follow coding standards and naming conventions for consistency."
    )

def post_comment(pr_url, comment, github_token):
    """Posts a comment to the pull request on GitHub."""
    try:
        repo = os.getenv('GITHUB_REPOSITORY')
        issue_number = pr_url.split('/')[-1]
        comments_url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
        headers = {'Authorization': f'token {github_token}', 'Content-Type': 'application/json'}
        response = requests.post(comments_url, headers=headers, json={"body": comment})
        response.raise_for_status()
        print("Comment posted successfully.")
    except requests.RequestException as e:
        raise Exception(f"Error posting comment: {e}")

def validate_environment_variables(*vars):
    """Validates the presence of required environment variables."""
    missing_vars = [var for var in vars if not os.getenv(var)]
    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

def main():
    """Main function to fetch PR diff, review code, and post comments."""
    try:
        validate_environment_variables("GITHUB_PR_URL", "GITHUB_TOKEN", "OPENAI_API_KEY")
        pr_url = os.getenv("GITHUB_PR_URL")
        github_token = os.getenv("GITHUB_TOKEN")
        openai_api_key = os.getenv("OPENAI_API_KEY")

        print(f"PR URL: {pr_url}")
        print(f"GitHub Token: {'Provided' if github_token else 'Missing'}")
        print(f"OpenAI API Key: {'Provided' if openai_api_key else 'Missing'}")

        # Fetch PR diff
        print("Fetching PR diff...")
        diff = fetch_diff(pr_url, github_token)

        # Review code
        print("Sending diff to OpenAI for review...")
        ai_review = review_code(diff, openai_api_key)
        if not ai_review:
            ai_review = "No significant suggestions provided."

        # Post review comment
        print("Posting review comment...")
        post_comment(pr_url, ai_review, github_token)

        print("AI review process completed successfully.")

    except EnvironmentError as env_err:
        print(f"Environment Error: {env_err}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
