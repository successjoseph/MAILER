import os
from groq import Groq

# Initialize Groq Client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_draft(manifesto, email_content):
    """
    Uses Llama-3.3-70b to draft a response based on the User's Manifesto.
    """
    prompt = f"Follow this Manifesto: {manifesto}\n\nEmail to reply to: {email_content}"
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1024,
    )
    
    return completion.choices[0].message.content

def fetch_emails():
    # Backend devs will implement Google API logic here
    pass
