from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
import os
import zipfile
import tempfile
import shutil
import re
from urllib.parse import urlparse
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from azure.devops.v7_1.git import GitRepositoryCreateOptions
from azure.devops.v7_1.git.models import GitRefUpdate, GitCommitRef, Change, ItemContent

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# Azure DevOps configuration
AZURE_DEVOPS_PAT = os.environ.get('AZURE_DEVOPS_PAT')
if not AZURE_DEVOPS_PAT:
    raise ValueError("AZURE_DEVOPS_PAT environment variable is required")

def parse_azure_devops_url(url):
    """
    Parse Azure DevOps repository URL and extract organization, project, and repository name.
    Expected format: https://dev.azure.com/{org}/{project}/_git/{repo}
    """
    pattern = r'https://dev\.azure\.com/([^/]+)/([^/]+)/_git/([^/]+)'
    match = re.match(pattern, url.strip())
    
    if not match:
        raise ValueError("Invalid Azure DevOps URL format. Expected: https://dev.azure.com/{org}/{project}/_git/{repo}")
    
    return {
        'organization': match.group(1),
        'project': match.group(2),
        'repository': match.group(3)
    }

def get_azure_devops_connection(organization):
    """Create Azure DevOps connection using PAT authentication."""
    credentials = BasicAuthentication('', AZURE_DEVOPS_PAT)
    organization_url = f'https://dev.azure.com/{organization}'
    return Connection(base_url=organization_url, creds=credentials)

def extract_zip_to_temp(zip_file):
    """Extract ZIP file to temporary directory and return the path."""
    temp_dir = tempfile.mkdtemp()
    
    try:
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        return temp_dir
    except zipfile.BadZipFile:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise ValueError("Invalid ZIP file")

def get_files_from_directory(directory):
    """Get all files from directory recursively for commit."""
    files = []
    
    for root, dirs, filenames in os.walk(directory):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            relative_path = os.path.relpath(file_path, directory)
            
            # Read file content
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                files.append({
                    'path': relative_path.replace('\\', '/'),  # Use forward slashes for Git
                    'content': content
                })
            except Exception as e:
                print(f"Warning: Could not read file {file_path}: {e}")
    
    return files

def commit_files_to_azure_devops(org, project, repo, files):
    """Commit files to Azure DevOps repository."""
    connection = get_azure_devops_connection(org)
    git_client = connection.clients.get_git_client()
    
    # Get repository
    repository = git_client.get_repository(project=project, repository_id=repo)
    
    # Get main branch reference
    try:
        main_ref = git_client.get_refs(
            repository_id=repository.id,
            project=project,
            filter='heads/main'
        )
        if not main_ref:
            # Try 'master' if 'main' doesn't exist
            main_ref = git_client.get_refs(
                repository_id=repository.id,
                project=project,
                filter='heads/master'
            )
        
        if not main_ref:
            raise ValueError("No main or master branch found")
        
        base_commit = main_ref[0].object_id
        base_branch = main_ref[0].name.split('/')[-1]  # Extract branch name
        
    except Exception as e:
        raise ValueError(f"Could not access repository or main branch: {e}")
    
    # Check if feature/initial branch exists
    feature_branch_name = 'feature/initial'
    feature_ref = None
    
    try:
        feature_refs = git_client.get_refs(
            repository_id=repository.id,
            project=project,
            filter=f'heads/{feature_branch_name}'
        )
        if feature_refs:
            feature_ref = feature_refs[0]
    except:
        pass
    
    # Create feature branch if it doesn't exist
    if not feature_ref:
        ref_update = GitRefUpdate(
            name=f'refs/heads/{feature_branch_name}',
            old_object_id='0000000000000000000000000000000000000000',
            new_object_id=base_commit
        )
        
        git_client.update_refs(
            ref_updates=[ref_update],
            repository_id=repository.id,
            project=project
        )
        
        # Get the newly created branch reference
        feature_ref = git_client.get_refs(
            repository_id=repository.id,
            project=project,
            filter=f'heads/{feature_branch_name}'
        )[0]
    
    # Prepare changes for commit
    changes = []
    for file_info in files:
        change = Change(
            change_type='add',
            item=file_info['path'],
            new_content={
                'content': file_info['content'],
                'content_type': 'rawtext' if file_info['path'].endswith(('.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.yml', '.yaml')) else 'base64encoded'
            }
        )
        changes.append(change)
    
    # Create commit
    commit = GitCommitRef(
        comment="Initial commit from ZIP",
        changes=changes,
        parents=[feature_ref.object_id]
    )
    
    # Push commit
    push_result = git_client.create_push(
        push={
            'ref_updates': [{
                'name': f'refs/heads/{feature_branch_name}',
                'old_object_id': feature_ref.object_id,
                'new_object_id': None  # Will be set by the service
            }],
            'commits': [commit]
        },
        repository_id=repository.id,
        project=project
    )
    
    return {
        'commit_id': push_result.commits[0].commit_id,
        'branch': feature_branch_name,
        'repository_url': f"https://dev.azure.com/{org}/{project}/_git/{repo}?version=GB{feature_branch_name}"
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        # Validate form data
        if 'repo_url' not in request.form or 'zip_file' not in request.files:
            flash('Repository URL and ZIP file are required', 'error')
            return redirect(url_for('index'))
        
        repo_url = request.form['repo_url'].strip()
        zip_file = request.files['zip_file']
        
        if not repo_url:
            flash('Repository URL is required', 'error')
            return redirect(url_for('index'))
        
        if zip_file.filename == '':
            flash('No ZIP file selected', 'error')
            return redirect(url_for('index'))
        
        # Parse Azure DevOps URL
        try:
            repo_info = parse_azure_devops_url(repo_url)
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('index'))
        
        # Extract ZIP file
        temp_dir = None
        try:
            temp_dir = extract_zip_to_temp(zip_file)
            files = get_files_from_directory(temp_dir)
            
            if not files:
                flash('No files found in ZIP archive', 'error')
                return redirect(url_for('index'))
            
            # Commit to Azure DevOps
            result = commit_files_to_azure_devops(
                repo_info['organization'],
                repo_info['project'],
                repo_info['repository'],
                files
            )
            
            flash(f'Successfully committed {len(files)} files to branch {result["branch"]}', 'success')
            flash(f'Commit ID: {result["commit_id"]}', 'info')
            flash(f'Branch URL: {result["repository_url"]}', 'info')
            
        except Exception as e:
            flash(f'Error processing upload: {str(e)}', 'error')
            return redirect(url_for('index'))
        
        finally:
            # Clean up temporary directory
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    except Exception as e:
        flash(f'Unexpected error: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Development server configuration
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)