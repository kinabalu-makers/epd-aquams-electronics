import requests
from git import Repo
import os
import json

current_directory = os.getcwd()
print("Current Directory:", current_directory)

repo = Repo(current_directory)

with open(os.path.join(current_directory, "config.json"), "r") as f:
    f.seek(0)  # Move to the beginning of the file
    config = json.loads(f.read())
    repo_owner = config['repo_owner']
    repo_name = config['repo_name']
    remote_branch_name = config['remote_branch_name']
    local_branch_name = config['local_branch_name']

def is_remote_ahead(repo_owner, repo_name, remote_branch_name, local_branch_name):
    # GitHub API endpoint to get the latest commit SHA of the remote branch
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/branches/{remote_branch_name}"

    local_commit_sha = get_commit_sha(local_branch_name)  # Replace with your local commit SHA
    
    # Send GET request to the GitHub API
    response = requests.get(url)
    
    if response.status_code == 200:
        remote_commit_sha = response.json()["commit"]["sha"]
        remote_commit_branch = response.json()["name"]
        print(f"Commit SHA of REMOTE:'{remote_commit_branch}': {remote_commit_sha}")
        
        # Compare the commit SHAs
        return remote_commit_sha != local_commit_sha
    else:
        print(f"Error: Unable to fetch remote branch information. Status code: {response.status_code}")
        return False

def get_commit_sha(local_branch_name):
    branch = repo.heads[local_branch_name]
    commit = branch.commit
    commit_sha = commit.hexsha
    print(f"Commit SHA of LOCAL: '{local_branch_name}': {commit_sha}")
    return commit_sha

def git_pull():

    result = is_remote_ahead(repo_owner, repo_name, remote_branch_name, local_branch_name)
    print(f"Is remote branch ahead of local branch? {result}")

    if result == True:
        print("Pulling...")
        repo.git.pull()
        print("Repository is up to date.")
    else:
        print("Already up to date")
    return result

git_pull()