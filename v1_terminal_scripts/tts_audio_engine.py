import asyncio
import edge_tts
import re
import os
from pydub import AudioSegment
from pydub.effects import speedup

def parse_dialogue(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        text = file.read()
    
    pattern = re.findall(r"\[(SPEAKER \d)\](.*?)(?=\[SPEAKER \d\]|$)", text, re.DOTALL)
    return [(speaker.strip(), dialogue.strip()) for speaker, dialogue in pattern]

async def text_to_speech(text, voice, output_file):
    tts = edge_tts.Communicate(text, voice)
    await tts.save(output_file)

async def generate_podcast(file_path, output_combined, speed_factor=1.25):
    dialogues = parse_dialogue(file_path)
    voice_map = {
        "SPEAKER 1": "en-US-RogerNeural",
        "SPEAKER 2": "en-US-AvaNeural"
    }
    
    temp_dir = "temp_audio"
    os.makedirs(temp_dir, exist_ok=True)
    temp_files = []
    
    for index, (speaker, text) in enumerate(dialogues):
        voice = voice_map.get(speaker, "en-US-ChristopherNeural") 
        output_file = os.path.join(temp_dir, f"temp_speech_{index + 1}.mp3")
        
        await text_to_speech(text, voice, output_file)
        temp_files.append(output_file)
        print(f"Generated audio for {speaker} -> Segment {index + 1}")
    
    print("Stitching and processing audio speed...")
    combined = AudioSegment.empty()
    for file in temp_files:
        audio = AudioSegment.from_file(file, format="mp3")
        if speed_factor != 1.0:
            audio = speedup(audio, playback_speed=speed_factor)
        combined += audio

    combined.export(output_combined, format="mp3")
    print(f"Podcast successfully exported to {output_combined}")
    
    for file in temp_files:
        os.remove(file)
    os.rmdir(temp_dir)
    print("Temporary files cleaned up.")

if __name__ == "__main__":
    INPUT_SCRIPT = "dialogue.txt"
    OUTPUT_AUDIO = "final_podcast.mp3"
    SPEED_MULTIPLIER = 1.5 
    
    asyncio.run(generate_podcast(INPUT_SCRIPT, OUTPUT_AUDIO, speed_factor=SPEED_MULTIPLIER))