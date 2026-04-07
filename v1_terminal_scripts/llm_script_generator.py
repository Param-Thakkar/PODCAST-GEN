import os
import fitz 
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

INPUT_FILE = "source_material.pdf"
OUTPUT_FILE = "dialogue.txt"

def extract_text_from_pdf(pdf_file):
    try:
        doc = fitz.open(pdf_file)
        text = "".join(page.get_text() + "\n" for page in doc)
        return text
    except Exception as e:
        print(f"Error extracting text from PDF {pdf_file}: {e}")
        return None

def generate_podcast_script(text_content):
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY")
    )

    system_prompt = """Task: Generate a podcast-style conversation based on the topic text.
    Speakers: [SPEAKER 1] (Allen, male host) and [SPEAKER 2] (Ava, female host).
    Format: Start with [SPEAKER X] for each turn. 
    Requirements: At least 15 turns each. Break down complex ideas step-by-step. Use real-world analogies. Keep it conversational and educational. NEVER use emojis."""

    final_prompt = f"TOPIC:\n{text_content}"

    try:
        print("Sending request to LLM...")
        response = client.chat.completions.create(
            model="google/gemini-2.5-flash", 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": final_prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"API Error: {e}")
        return None

if __name__ == "__main__":
    print(f"Extracting text from {INPUT_FILE}...")
    source_text = extract_text_from_pdf(INPUT_FILE)
    
    if source_text:
        print("Generating podcast dialogue...")
        script = generate_podcast_script(source_text)
        
        if script:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                f.write(script)
            print(f"Successfully generated script and saved to {OUTPUT_FILE}")
