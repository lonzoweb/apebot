import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("Error: GOOGLE_API_KEY not found in environment.")
    exit(1)

client = genai.Client(api_key=api_key)

print("Listing available models for your API key...")
try:
    models = client.models.list()
    found_imagen = False
    for m in models:
        if "imagen" in m.name.lower():
            print(f"  - {m.name}")
            found_imagen = True
    
    if not found_imagen:
        print("No Imagen models found via this API key.")
except Exception as e:
    print(f"Error listing models: {e}")
