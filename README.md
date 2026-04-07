# OpenPod: Custom AI Podcast Generator & Audio Accelerator

Originally ideated in 2022 and continuously evolved, OpenPod was born out of a desire to consume educational content faster and more efficiently than standard platforms allow. As an auditory learner who processes information at roughly 3x normal speaking speed, commercial text-to-speech (TTS) solutions were fundamentally lacking—they were incredibly expensive for hour-long generations and hard-capped playback speeds.

What began as a terminal-based workaround to bypass these API limits has since matured into a full-stack, asynchronous desktop application featuring spatial audio and automated metadata tagging.

## Phase 1: The Proof of Concept (V1)

To bypass the limitations of commercial platforms, the initial V1 prototype utilized a decoupled, terminal-based architecture to prove the core concept:

* **The LLM Brain:** Using OpenRouter to access models like Gemini and Llama, the system digested raw PDF textbooks and generated a structured, conversational script between two distinct hosts.
* **The TTS Workaround:** Instead of paying for commercial API tokens, V1 utilized the `edge-tts` library to interface directly with Microsoft Edge's built-in read-aloud feature, granting free access to high-quality Azure Neural voices.
* **The Audio Accelerator:** By integrating `pydub`, the pipeline stitched individual audio segments together and applied a custom speed multiplier algorithm, allowing the audio to be accelerated well beyond commercial limits without pitch distortion.

## Phase 2: The Production Desktop Application (V2)

While V1 successfully proved the concept, generating an hour-long podcast segment by segment in a synchronous terminal loop was slow, and flat audio caused listening fatigue at high speeds. 

The V2 update overhauled the architecture. Upgrading the environment to Python 3.12 and transitioning from a terminal script to a fully-fledged graphical application built with `tkinter`, V2 introduces serious audio engineering and processing advancements:

* **Spatial Audio Panning:** To make the generated podcasts sound like a genuine studio recording, V2 implements spatial audio panning. Host 1 is panned slightly to the left audio channel, and Host 2 is panned to the right. This subtle audio engineering creates an immersive dynamic that dramatically improves long-term listening fatigue.
* **Asynchronous Concurrency:** The generation loop was re-architected using `asyncio` and semaphores to deploy concurrent TTS workers. This allows multiple dialogue chunks to render simultaneously, cutting total build times down to a fraction of the original script.
* **Automated ID3 Metadata:** To ensure the generated MP3s function seamlessly in native music players (like Apple Music or Spotify local files), V2 integrates the `mutagen` library. The GUI allows the user to define track names, albums, artists, and genres, which are burned directly into the final MP3 as ID3 metadata.
* **Deep-Dive Prompt Architecture:** The core LLM prompt was entirely rebuilt. Rather than asking for a basic summary, the V2 system prompt forces the model to engage in relentless curiosity—asking probing questions, deconstructing dense technical jargon into micro-steps, and stretching analogies to explore edge cases.

## The Tech Stack

* **Language:** Python 3.11 (Phase 1) ➔ Python 3.12 (Phase 2)
* **Interface:** Tkinter
* **AI/LLM:** OpenAI API (OpenRouter), PyMuPDF (fitz)
* **Audio Engineering:** `edge-tts` (Azure TTS endpoint access), `pydub`, `asyncio`, `mutagen` (ID3 Tagging)

## How to Use This Repository

This repository hosts the V2 production suite, divided into two distinct, user-friendly desktop applications. 

**Prerequisites:** Install the dependencies. Ensure `ffmpeg` is installed on your local system to allow `pydub` to process audio files.

**Running the Suite:**
1. Run `python dialogue_generator_gui.py` to open the text generation interface. Supply your OpenRouter API key and source document to generate the transcript.
2. Run `python tts_audio_gui.py` to open the audio engine. Select your transcript, configure your preferred metadata and concurrency limits, and generate the final podcast.