import openai
import os
from github import Github

# Set up GitHub and OpenAI
g = Github(os.getenv('GITHUB_TOKEN'))
repo = g.get_repo('user/repo-name')
pr = repo.get_pull(123)  # Replace with your PR number

# Get the diff of the pull request
diff = pr.diff()

# Make a call to OpenAI to analyze the diff
openai.api_key = os.getenv('OPENAI_API_KEY')
response = openai.Completion.create(
    model="gpt-4",
    prompt=f"Review the following code and suggest improvements or errors:\n\n{diff}",
    max_tokens=500
)

# Post the review as a comment on the pull request
pr.create_issue_comment(response.choices[0].text.strip())
