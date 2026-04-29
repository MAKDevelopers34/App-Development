import requests
import re
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

SUPPORTED_EXTENSIONS = ['.py', '.js', '.java', '.cpp', '.c', '.ts', '.jsx', '.tsx']

def parse_github_url(url):
    """
    Converts GitHub URL to owner and repo name
    Example: https://github.com/facebook/react → ('facebook', 'react')
    """
    pattern = r'github\.com/([^/]+)/([^/]+)'
    match = re.search(pattern, url)
    if match:
        owner = match.group(1)
        repo = match.group(2).replace('.git', '')
        return owner, repo
    return None, None


def get_headers():
    """
    Returns headers with GitHub token if available
    """
    headers = {'Accept': 'application/vnd.github.v3+json'}
    if GITHUB_TOKEN and GITHUB_TOKEN != 'your_github_token_here':
        headers['Authorization'] = f'token {GITHUB_TOKEN}'
    return headers


def get_all_files(owner, repo, path=''):
    """
    Recursively gets all files in a GitHub repository
    """
    url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
    headers = get_headers()

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return []

        items = response.json()
        files = []

        for item in items:
            if item['type'] == 'file':
                ext = os.path.splitext(item['name'])[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    files.append(item)
            elif item['type'] == 'dir':
                # Skip common non-code folders
                skip_folders = ['node_modules', '.git', '__pycache__', 
                               'venv', 'dist', 'build', '.next']
                if item['name'] not in skip_folders:
                    files.extend(get_all_files(owner, repo, item['path']))

        return files

    except Exception as e:
        print(f'Error fetching files: {e}')
        return []


def fetch_file_content(download_url):
    """
    Downloads and returns the content of a single file
    """
    try:
        response = requests.get(download_url, timeout=10)
        if response.status_code == 200:
            return response.text
        return None
    except Exception:
        return None


def fetch_github_code(url):
    """
    Main function — takes a GitHub URL and returns list of files with code
    """
    owner, repo = parse_github_url(url)

    if not owner or not repo:
        return []

    print(f'Fetching repository: {owner}/{repo}')

    # Get all code files in the repo
    all_files = get_all_files(owner, repo)

    if not all_files:
        return []

    # Limit to first 20 files to avoid rate limiting
    all_files = all_files[:20]

    result = []
    for file_info in all_files:
        code = fetch_file_content(file_info['download_url'])
        if code and code.strip():
            result.append({
                'filename': file_info['path'],
                'code': code
            })

    print(f'Successfully fetched {len(result)} files')
    return result