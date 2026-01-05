import os
import json
from google import genai
from google.genai import types

# Path to the credentials file
creds_path = "google_credentials.json"

if not os.path.exists(creds_path):
    print(f"Error: {creds_path} not found.")
    exit(1)

# Extract project info manually for debug
with open(creds_path, 'r') as f:
    creds_data = json.load(f)
    print(f"Service Account Type: {creds_data.get('type')}")
    print(f"Project ID: {creds_data.get('project_id')}")
    print(f"Client Email: {creds_data.get('client_email')}")

# Set environment variable for SDK
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(creds_path)

# Initialize Client in Vertex mode
project_id = creds_data.get('project_id')
client = genai.Client(
    vertexai=True,
    project=project_id,
    location='us-central1'
)

print("\n--- Listing Vertex AI Models ---")
try:
    for m in client.models.list():
        if "imagen" in m.name.lower():
            print(f"  - {m.name}")
except Exception as e:
    print(f"Error listing Vertex AI models: {e}")

print("\n--- Trying a Test Generation (Vertex AI) ---")
try:
    # Try the standard imagen-3.0-generate-001
    response = client.models.generate_images(
        model='imagen-3.0-generate-001',
        prompt='a simple circle',
        config=types.GenerateImagesConfig(number_of_images=1)
    )
    print("Success! Generated image bytes received.")
except Exception as e:
    print(f"Error during test generation: {e}")
