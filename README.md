# Azure DevOps ZIP Uploader

A Flask web application that allows users to upload ZIP files and commit their contents to Azure DevOps repositories.

## Features

- Upload ZIP files through a modern web interface
- Automatically extract ZIP contents to a temporary directory
- Create and commit to a "feature/initial" branch in Azure DevOps
- Secure authentication using Personal Access Tokens
- Comprehensive error handling and user feedback
- Support for drag-and-drop file uploads
- Responsive Bootstrap UI

## Setup Instructions

### Prerequisites

- Python 3.7 or higher
- Azure DevOps account with repository access
- Personal Access Token (PAT) with appropriate permissions

### Installation

1. **Clone or download the application files**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   ```bash
   # Required: Azure DevOps Personal Access Token
   export AZURE_DEVOPS_PAT="your_personal_access_token_here"
   
   # Optional: Flask configuration
   export FLASK_SECRET_KEY="your_secret_key_here"
   export FLASK_DEBUG="False"
   export PORT="5000"
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```

5. **Access the application:**
   Open your browser and navigate to `http://localhost:5000`

### Azure DevOps Personal Access Token Setup

1. Go to Azure DevOps: `https://dev.azure.com/{your-organization}`
2. Click on your profile picture → Personal access tokens
3. Click "New Token"
4. Configure the token:
   - **Name**: Give it a descriptive name (e.g., "ZIP Uploader")
   - **Organization**: Select your organization
   - **Expiration**: Set an appropriate expiration date
   - **Scopes**: Select "Custom defined" and choose:
     - **Code (read & write)** - Required for repository access and commits
     - **Code (status)** - Optional, for additional repository operations

5. Copy the generated token and set it as the `AZURE_DEVOPS_PAT` environment variable

## Usage

1. **Enter Repository URL**: Provide the full Azure DevOps repository URL in the format:
   ```
   https://dev.azure.com/{organization}/{project}/_git/{repository}
   ```

2. **Upload ZIP File**: Either click to select a ZIP file or drag and drop it onto the upload zone

3. **Submit**: Click "Upload and Commit" to process the upload

4. **Results**: The application will:
   - Create a "feature/initial" branch from main (if it doesn't exist)
   - Extract all files from the ZIP
   - Commit all files to the branch with the message "Initial commit from ZIP"
   - Display the commit ID and branch URL

## Error Handling

The application handles various error scenarios:

- Invalid Azure DevOps URL format
- Authentication failures
- Repository access issues
- Invalid or corrupted ZIP files
- Network connectivity problems
- File extraction errors

## Deployment Options

### Local Development
- Run directly with `python app.py`
- Access at `http://localhost:5000`

### Azure App Service
1. Create an Azure App Service (Python runtime)
2. Set environment variables in Application Settings:
   - `AZURE_DEVOPS_PAT`: Your Personal Access Token
   - `FLASK_SECRET_KEY`: A secure random string
3. Deploy the application files
4. The app will automatically start on the assigned URL

### Docker Deployment
Create a `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "app.py"]
```

Build and run:
```bash
docker build -t azure-devops-uploader .
docker run -p 5000:5000 -e AZURE_DEVOPS_PAT="your_token" azure-devops-uploader
```

## Security Considerations

- Personal Access Tokens are stored as environment variables, never in code
- ZIP file contents are extracted to temporary directories that are cleaned up automatically
- Input validation is performed on repository URLs
- File uploads are restricted to ZIP format only
- All user inputs are sanitized to prevent injection attacks

## File Structure

```
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
└── templates/            # HTML templates
    ├── base.html         # Base template with common layout
    ├── index.html        # Main upload form
    ├── 404.html          # 404 error page
    └── 500.html          # 500 error page
```

## Dependencies

- **Flask**: Web framework
- **azure-devops**: Azure DevOps Python SDK
- **msrest**: Authentication library for Azure services
- **requests**: HTTP library (used by azure-devops)

## Troubleshooting

### Common Issues

1. **"AZURE_DEVOPS_PAT environment variable is required"**
   - Ensure you've set the environment variable with your PAT

2. **"Invalid Azure DevOps URL format"**
   - Check that your URL follows the exact format: `https://dev.azure.com/{org}/{project}/_git/{repo}`

3. **Authentication errors**
   - Verify your PAT has the correct permissions (Code read & write)
   - Check that the PAT hasn't expired

4. **"No main or master branch found"**
   - Ensure the repository has at least one commit on the main/master branch

5. **File upload issues**
   - Verify the file is a valid ZIP archive
   - Check file size limits (depends on your deployment environment)

### Logging

The application uses Flask's built-in logging. For debugging, set `FLASK_DEBUG=True` in your environment variables.

## License

This project is provided as-is for educational and development purposes.