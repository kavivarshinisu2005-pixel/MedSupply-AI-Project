
from pathlib import Path
from dotenv import dotenv_values
from openai import OpenAI

env_path = Path(__file__).resolve().parent / ".env"
config = dotenv_values(env_path)

api_key = config["NEXUS_API_KEY"].strip()
base_url = config["NEXUS_API_BASE_URL"].strip()
model = config["NEXUS_MODEL"].strip()

client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

print("Testing model:", model)

response = client.chat.completions.create(
    model=model,
    messages=[
        {
            "role": "user",
            "content": "Reply only: MedSupply AI connected successfully"
        }
    ],
    max_tokens=60
)

print("AI Response:")
print(response.choices[0].message.content)
