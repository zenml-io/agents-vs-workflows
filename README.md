# Agent or Workflow? The Great AI Debate

A Streamlit app that helps users understand the difference between AI agents and workflows through an interactive quiz.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up Google Sheets integration:

   a. Create a Google Cloud Project:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Click "Select a project" at the top
   - Click "New Project"
   - Name it (e.g., "zenml-quiz")
   - Click "Create"

   b. Enable the Google Sheets API:
   - In your project, go to "APIs & Services" > "Library"
   - Search for "Google Sheets API"
   - Click "Enable"

   c. Create a Service Account:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Name it (e.g., "zenml-quiz-sa")
   - Click "Create and Continue"
   - Skip role assignment (click "Continue")
   - Click "Done"

   d. Create and Download Service Account Key:
   - In the Service Accounts list, find your new service account
   - Click the three dots (⋮) > "Manage keys"
   - Click "Add Key" > "Create new key"
   - Choose "JSON"
   - Click "Create" (this will download your credentials)

   e. Create and Share Google Sheet:
   - Go to [Google Sheets](https://sheets.google.com)
   - Create a new sheet named "ZenML Quiz Votes"
   - Click "Share" button
   - Add your service account email (found in the JSON file as "client_email")
   - Give it "Editor" access
   - Click "Share"

   f. Set up credentials:
   - Copy `.streamlit/secrets.toml.template` to `.streamlit/secrets.toml`
   - Open the downloaded JSON file
   - Copy each value from the JSON to the corresponding field in `secrets.toml`:
     - `project_id` → `project_id`
     - `private_key_id` → `private_key_id`
     - `private_key` → `private_key`
     - `client_email` → `client_email`
     - `client_id` → `client_id`
     - `client_x509_cert_url` → `client_x509_cert_url`
   - The other fields (`auth_uri`, `token_uri`, `auth_provider_x509_cert_url`) can stay as they are

3. Run the app:
```bash
streamlit run app.py
```

## Deployment to Streamlit Cloud

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click "New app" and connect your GitHub repository
4. In the app settings, go to "Secrets" and add your Google Sheets credentials:
   ```toml
   [gsheets]
   type = "service_account"
   project_id = "your-project-id"
   private_key_id = "your-private-key-id"
   private_key = "your-private-key"
   client_email = "your-service-account@your-project.iam.gserviceaccount.com"
   client_id = "your-client-id"
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "your-client-cert-url"
   ```
5. Make sure your Google Sheet is shared with the service account email
6. Deploy the app

## Development

- The app uses Streamlit's built-in Google Sheets connection for storing quiz votes
- Quiz data is stored in `QUIZ_DATA` in `app.py`
- Styling is defined in the custom CSS section of `app.py`

## Security Note

Never commit `.streamlit/secrets.toml` to version control. This file contains sensitive credentials that should be kept private. For Streamlit Cloud deployment, add the secrets through the dashboard instead.