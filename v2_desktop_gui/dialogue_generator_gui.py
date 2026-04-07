import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import fitz
from openai import OpenAI

def get_content(path):
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == '.pdf':
            doc = fitz.open(path)
            return "\n".join([page.get_text() for page in doc])
        elif ext in ['.txt', '.md']:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        return None
    except Exception as e:
        return f"Error: {e}"

class PodcastApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Podcast Generator V2")
        self.root.geometry("600x600")

        self.mode = tk.StringVar(value="file")
        self.selected_path = tk.StringVar(value="No file/folder selected")
        
        tk.Label(root, text="Step 1: API Key", font=('Arial', 10, 'bold')).pack(pady=(15, 5))
        self.api_entry = tk.Entry(root, width=40, show="*")
        self.api_entry.pack()

        tk.Label(root, text="Step 2: Podcast Name", font=('Arial', 10, 'bold')).pack(pady=(15, 5))
        self.podcast_name_entry = tk.Entry(root, width=40)
        self.podcast_name_entry.pack()

        tk.Label(root, text="Step 3: Choose Mode", font=('Arial', 10, 'bold')).pack(pady=(15, 5))
        tk.Radiobutton(root, text="Single File", variable=self.mode, value="file").pack()
        tk.Radiobutton(root, text="Entire Folder", variable=self.mode, value="folder").pack()

        tk.Button(root, text="Browse", command=self.browse_path).pack(pady=5)
        tk.Label(root, textvariable=self.selected_path, wraplength=500, fg="blue").pack()

        tk.Label(root, text="Step 4: Model Selection", font=('Arial', 10, 'bold')).pack(pady=(15, 5))
        
        self.model_var = tk.StringVar()
        self.model_dropdown = ttk.Combobox(root, textvariable=self.model_var, width=37, state="readonly")
        self.model_dropdown['values'] = (
            "google/gemini-3.1-pro-preview",
            "deepseek/deepseek-v3.2",
            "google/gemini-2.5-flash",
            "google/gemini-3-flash-preview"
        )
        self.model_dropdown.current(2)
        self.model_dropdown.pack()

        self.run_btn = tk.Button(root, text="Generate Podcast", bg="green", fg="white", 
                                 command=self.start_process, font=('Arial', 10, 'bold'))
        self.run_btn.pack(pady=20)

        self.log_area = scrolledtext.ScrolledText(root, height=10, width=70, font=('Consolas', 9))
        self.log_area.pack(pady=10)

    def log(self, message):
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.root.update_idletasks()

    def browse_path(self):
        if self.mode.get() == "file":
            path = filedialog.askopenfilename(filetypes=[("Documents", "*.pdf *.txt *.md")])
        else:
            path = filedialog.askdirectory()
        
        if path:
            self.selected_path.set(path)

    def start_process(self):
        path = self.selected_path.get()
        api_key = self.api_entry.get()
        model = self.model_var.get()
        Podcast_Name = self.podcast_name_entry.get().strip()

        if not api_key or "selected" in path:
            messagebox.showerror("Error", "Please provide an API key and select a path.")
            return

        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        
        files = []
        if self.mode.get() == "file":
            files.append(path)
        else:
            for f in os.listdir(path):
                if f.lower().endswith(('.pdf', '.txt', '.md')):
                    files.append(os.path.join(path, f))

        self.log(f"Found {len(files)} file to process.")

        for file_path in files:
            self.process_single_file(client, file_path, model, Podcast_Name)

    def process_single_file(self, client, file_path, model, Podcast_Name):
        name = os.path.basename(file_path)
        self.log(f"Processing {name} with {model}")
        
        content = get_content(file_path)
        if not content or "Error" in content:
            self.log(f"Skipping {name}: Extraction failed.")
            return

        sys_prompt = f"""System Prompt: Deep-Dive Podcast Transcript Generation

Podcast Name:
[{Podcast_Name}] 

Task:
Generate a comprehensive, deep-dive podcast-style conversation based on the topic text provided.

Objective:
Create an engaging, highly detailed podcast episode where two hosts thoroughly explore, deconstruct, and explain the provided concepts. Do not settle for a high-level summary. The dialogue must peel back the layers of the topic, exploring the underlying mechanics, nuances, and "why" behind the facts, all while maintaining a natural, conversational tone.

Speakers:
[Allen] – Host 1
[Ava] – Host 2

Dialogue Format:
Use exactly this structure for speaking turns:
[Allen]:
[Ava]:

Requirements:
The Intro: Start with a short, friendly introduction welcoming listeners to the podcast by name. Clearly state the episode's topic and hook the listener by explaining the deeper value or hidden complexity of what you are about to discuss.
Length: Each speaker must have at least 15 speaking turns.
Probing Questions: The conversation must feature relentless curiosity. Hosts should ask follow-up questions.
Deconstruct the Complex: Do not just define terms. Dedicate significant portions of the conversation to unpacking the most advanced or dense parts of the text.
Analogies with Depth: Use real-world analogies to anchor abstract ideas.
Explore Edge Cases: Go beyond the happy path. Discuss edge cases, potential failures, or historical context.
Accessible but Smart: Break down all technical ideas in plain English.
Tone: Keep it professional, educational, and friendly.

STRICT RULE: NEVER use emojis EVER.
STRICT RULE: Avoid heavy jargon without immediate explanation.

Input Format:
TOPIC:
[INSERT TEXT HERE]"""

        msgs = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"TOPIC:\n{content}"}
        ]

        try:
            self.log("Sending request to AI.")
            response = client.chat.completions.create(model=model, messages=msgs)
            answer = response.choices[0].message.content

            self.log("Success. Podcast generated.")

            out_path = os.path.splitext(file_path)[0] + "_podcast.txt"
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(answer)

        except Exception as e:
            self.log(f"API Error on {name}: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PodcastApp(root)
    root.mainloop()
