import asyncio
import edge_tts
import re
import os
import shutil
import random
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pydub import AudioSegment
from mutagen.easyid3 import EasyID3

def parse_dialogue(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    dialogues = []
    current_speaker = None
    current_text = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        match = re.match(r"^\[(.*?)\]:?\s*", line)
        if match:
            if current_speaker and current_text:
                raw_text = ' '.join(current_text).strip()
                clean_text = re.sub(r"\(.*?\)", "", raw_text).strip()
                dialogues.append((current_speaker, clean_text))
                current_text = []
                
            current_speaker = match.group(1).strip()
            
            rest_of_line = line[match.end():].strip()
            if rest_of_line:
                current_text.append(rest_of_line)
        else:
            current_text.append(line)

    if current_speaker and current_text:
        raw_text = ' '.join(current_text).strip()
        clean_text = re.sub(r"\(.*?\)", "", raw_text).strip()
        dialogues.append((current_speaker, clean_text))

    return dialogues

async def text_to_speech(text, voice, output_file, rate="+150%", retries=3):
    for attempt in range(retries):
        try:
            await asyncio.sleep(random.uniform(0.1, 0.6))
            tts = edge_tts.Communicate(text, voice=voice, rate=rate)
            await tts.save(output_file)
            return
        except Exception:
            if attempt < retries - 1:
                await asyncio.sleep(2 ** (attempt + 1))
            else:
                raise

async def generate_podcast(file_path, output_combined, metadata=None, concurrency_limit=5, update_callback=None, cancel_event=None):
    if cancel_event and cancel_event.is_set():
        return False

    base_name = os.path.splitext(os.path.basename(file_path))[0]
    temp_dir = f"temp_audio_{base_name}"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        dialogues = parse_dialogue(file_path)
        
        voice_map = {
            "Allen": "en-US-RogerNeural",
            "Ava": "en-US-AvaNeural",
            "Christopher": "en-US-ChristopherNeural"
        }
        
        speaker_panning = {
            "Allen": -0.2,  
            "Ava": 0.2,   
            "Christopher": 0      
        }

        semaphore = asyncio.Semaphore(concurrency_limit)
        dialogue_with_files = []

        async def process_dialogue(index, speaker, text):
            if cancel_event and cancel_event.is_set():
                return None
            
            voice = voice_map.get(speaker, "en-US-ChristopherNeural")
            output_file = os.path.join(temp_dir, f"chunk_{index:04d}.mp3")
            
            async with semaphore:
                if cancel_event and cancel_event.is_set():
                    return None
                await text_to_speech(text, voice, output_file)
            return (index, output_file, speaker)

        tasks = [process_dialogue(i, speaker, text) for i, (speaker, text) in enumerate(dialogues)]
        total = len(tasks)

        if update_callback:
            update_callback(f"Generating {total} speech chunks for {base_name}.")

        completed = 0
        for coro in asyncio.as_completed(tasks):
            if cancel_event and cancel_event.is_set():
                raise InterruptedError("Process cancelled by user.")
                
            result = await coro
            if result:
                dialogue_with_files.append(result)
                completed += 1
                if update_callback:
                    update_callback(f"Processed chunk {completed}/{total} for {base_name}.")

        if update_callback:
            update_callback("Combining audio and applying spatial panning.")

        combined = AudioSegment.empty()
        dialogue_with_files.sort(key=lambda x: x[0])

        pause = AudioSegment.silent(duration=300)

        for i, (_, file, speaker) in enumerate(dialogue_with_files):
            if cancel_event and cancel_event.is_set():
                raise InterruptedError("Process cancelled by user during audio compilation.")
                
            audio = AudioSegment.from_file(file, format="mp3")
            pan_value = speaker_panning.get(speaker, 0)
            audio = audio.pan(pan_value)
            
            combined += audio
            if i < len(dialogue_with_files) - 1:
                combined += pause

        combined = combined.set_channels(2)
        combined.export(output_combined, format="mp3", bitrate="320k")

        if metadata:
            try:
                audio_tags = EasyID3(output_combined)
            except Exception:
                audio_tags = EasyID3()
            for key, value in metadata.items():
                if value and value != "[Auto-from-filename]": 
                    audio_tags[key] = value
            audio_tags.save(output_combined)

        if update_callback:
            update_callback(f"Finished: {os.path.basename(output_combined)}")
        return True

    except InterruptedError:
        if update_callback:
            update_callback("Process was stopped.")
        return False
        
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

async def process_inputs(input_path, output_dir, is_file, update_callback, metadata, naming_format, custom_title, concurrency, cancel_event):
    os.makedirs(output_dir, exist_ok=True)

    try:
        if is_file:
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            
            if naming_format:
                final_name = naming_format if naming_format.lower().endswith(".mp3") else f"{naming_format}.mp3"
            else:
                final_name = f"{base_name}.mp3"
                
            output_file = os.path.join(output_dir, final_name)
            
            file_metadata = metadata.copy()
            file_metadata["title"] = custom_title if custom_title and custom_title != "[Auto-from-filename]" else base_name

            await generate_podcast(input_path, output_file, metadata=file_metadata, concurrency_limit=concurrency, update_callback=update_callback, cancel_event=cancel_event)

        else:
            files_to_process = [os.path.join(input_path, f) for f in os.listdir(input_path) if f.lower().endswith(".txt")]
            
            for file_path in files_to_process:
                if cancel_event and cancel_event.is_set():
                    break
                    
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                suffix = naming_format if naming_format else ""
                output_file = os.path.join(output_dir, f"{base_name}{suffix}.mp3")
                
                file_metadata = metadata.copy()
                file_metadata["title"] = base_name

                success = await generate_podcast(file_path, output_file, metadata=file_metadata, concurrency_limit=concurrency, update_callback=update_callback, cancel_event=cancel_event)
                if not success:
                    break

        if not cancel_event.is_set():
            update_callback("All processing complete.")
            
    except Exception as e:
        if not cancel_event.is_set():
            raise e

class PodcastGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Podcast TTS Audio Engine V2")
        self.root.geometry("550x580") 
        self.root.resizable(False, False)

        self.input_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.is_file_mode = tk.BooleanVar(value=True)
        self.show_advanced = tk.BooleanVar(value=False)
        
        self.cancel_event = threading.Event()

        self.name_format = tk.StringVar(value="")
        self.meta_title = tk.StringVar(value="")
        self.meta_artist = tk.StringVar(value="Param")
        self.meta_album = tk.StringVar(value="Security +")
        self.meta_genre = tk.StringVar(value="Podcast")
        self.meta_date = tk.StringVar(value="2026")
        self.concurrency_limit = tk.IntVar(value=5) 

        self.setup_ui()

    def setup_ui(self):
        frame_input = ttk.LabelFrame(self.root, text="Input", padding=(10, 10))
        frame_input.pack(fill="x", padx=10, pady=5)

        ttk.Radiobutton(frame_input, text="Single File", variable=self.is_file_mode, value=True, command=self.update_mode_ui).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(frame_input, text="Entire Folder", variable=self.is_file_mode, value=False, command=self.update_mode_ui).grid(row=0, column=1, sticky="w")

        ttk.Entry(frame_input, textvariable=self.input_path, width=50).grid(row=1, column=0, columnspan=2, pady=5)
        ttk.Button(frame_input, text="Browse", command=self.browse_input).grid(row=1, column=2, padx=5)

        frame_output = ttk.LabelFrame(self.root, text="Output Directory", padding=(10, 10))
        frame_output.pack(fill="x", padx=10, pady=5)

        ttk.Entry(frame_output, textvariable=self.output_dir, width=50).grid(row=0, column=0, pady=5)
        ttk.Button(frame_output, text="Browse", command=self.browse_output).grid(row=0, column=1, padx=5)

        ttk.Checkbutton(self.root, text="Advanced Settings", variable=self.show_advanced, command=self.toggle_advanced).pack(pady=5, anchor="w", padx=15)

        self.frame_advanced = ttk.LabelFrame(self.root, text="Advanced Options", padding=(10, 10))
        
        self.lbl_name_format = ttk.Label(self.frame_advanced, text="Exact Filename:")
        self.lbl_name_format.grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(self.frame_advanced, textvariable=self.name_format, width=30).grid(row=0, column=1, sticky="w", pady=2)

        self.lbl_title = ttk.Label(self.frame_advanced, text="Track Title:")
        self.lbl_title.grid(row=1, column=0, sticky="w", pady=2)
        self.entry_title = ttk.Entry(self.frame_advanced, textvariable=self.meta_title, width=30)
        self.entry_title.grid(row=1, column=1, sticky="w", pady=2)

        ttk.Label(self.frame_advanced, text="Artist:").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(self.frame_advanced, textvariable=self.meta_artist, width=30).grid(row=2, column=1, sticky="w", pady=2)

        ttk.Label(self.frame_advanced, text="Album:").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Entry(self.frame_advanced, textvariable=self.meta_album, width=30).grid(row=3, column=1, sticky="w", pady=2)

        ttk.Label(self.frame_advanced, text="Genre:").grid(row=4, column=0, sticky="w", pady=2)
        ttk.Entry(self.frame_advanced, textvariable=self.meta_genre, width=30).grid(row=4, column=1, sticky="w", pady=2)

        ttk.Label(self.frame_advanced, text="Year:").grid(row=5, column=0, sticky="w", pady=2)
        ttk.Entry(self.frame_advanced, textvariable=self.meta_date, width=15).grid(row=5, column=1, sticky="w", pady=2)

        ttk.Label(self.frame_advanced, text="Max Concurrent TTS Workers:").grid(row=6, column=0, sticky="w", pady=(10, 2))
        spinbox_workers = ttk.Spinbox(self.frame_advanced, from_=1, to=30, textvariable=self.concurrency_limit, width=5)
        spinbox_workers.grid(row=6, column=1, sticky="w", pady=(10, 2))
        ttk.Label(self.frame_advanced, text="(Higher = Faster)").grid(row=6, column=1, sticky="w", padx=(50, 0), pady=(10, 2))

        self.status_label = ttk.Label(self.root, text="Ready", foreground="blue")
        self.status_label.pack(pady=10)

        self.frame_buttons = ttk.Frame(self.root)
        self.frame_buttons.pack(pady=5)

        self.start_btn = ttk.Button(self.frame_buttons, text="Start Generation", command=self.start_processing)
        self.start_btn.grid(row=0, column=0, padx=5)

        self.stop_btn = ttk.Button(self.frame_buttons, text="Stop", command=self.stop_processing, state="disabled")
        self.stop_btn.grid(row=0, column=1, padx=5)

        self.update_mode_ui()

    def update_mode_ui(self):
        if self.is_file_mode.get():
            self.lbl_name_format.config(text="Exact Filename:")
            if self.name_format.get() == "_FINAL":
                self.name_format.set("")
            self.entry_title.config(state="normal")
            if self.meta_title.get() == "[Auto-from-filename]":
                self.meta_title.set("")
        else:
            self.lbl_name_format.config(text="File Suffix:")
            if not self.name_format.get().startswith("_"):
                self.name_format.set("_FINAL")
            self.meta_title.set("[Auto-from-filename]")
            self.entry_title.config(state="disabled")

    def toggle_advanced(self):
        if self.show_advanced.get():
            self.frame_advanced.pack(fill="x", padx=10, pady=5, before=self.status_label)
        else:
            self.frame_advanced.pack_forget()

    def browse_input(self):
        if self.is_file_mode.get():
            path = filedialog.askopenfilename(parent=self.root, filetypes=[("Text Files", "*.txt")])
        else:
            path = filedialog.askdirectory(parent=self.root)
        
        if path:
            self.input_path.set(path)

    def browse_output(self):
        path = filedialog.askdirectory(parent=self.root)
        if path:
            self.output_dir.set(path)

    def update_status(self, message):
        self.root.after(0, lambda: self.status_label.config(text=message))

    def stop_processing(self):
        self.cancel_event.set()
        self.stop_btn.config(state="disabled")
        self.status_label.config(text="Stopping process.")

    def run_async_loop(self, input_p, output_d, is_file, meta, naming_format, custom_title, concurrency):
        try:
            asyncio.run(process_inputs(input_p, output_d, is_file, self.update_status, meta, naming_format, custom_title, concurrency, self.cancel_event))
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
        finally:
            self.root.after(0, lambda: self.start_btn.config(state="normal"))
            self.root.after(0, lambda: self.stop_btn.config(state="disabled"))

    def start_processing(self):
        in_path = self.input_path.get()
        out_dir = self.output_dir.get()

        if not in_path or not out_dir:
            messagebox.showwarning("Missing Info", "Please select both input and output paths.")
            return

        custom_metadata = {
            "artist": self.meta_artist.get(),
            "album": self.meta_album.get(),
            "genre": self.meta_genre.get(),
            "date": self.meta_date.get()
        }
        
        naming_format = self.name_format.get()
        custom_title = self.meta_title.get()
        concurrency = self.concurrency_limit.get()

        self.cancel_event.clear()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_label.config(text="Starting process.")

        threading.Thread(
            target=self.run_async_loop, 
            args=(in_path, out_dir, self.is_file_mode.get(), custom_metadata, naming_format, custom_title, concurrency), 
            daemon=True
        ).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = PodcastGeneratorApp(root)
    root.mainloop()