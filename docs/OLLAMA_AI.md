# Free local AI (Ollama): the Translate button

What it does: the **Translate** button next to the Gujarati / Hindi boxes suggests the translation of a name. Nothing leaves your PC and nothing is paid. The doctor checks and edits it before saving.

## Install (once)
1. Install **Ollama for Windows** from ollama.com (it starts by itself when Windows starts).
2. Open PowerShell and run: `ollama pull qwen2.5:3b` (about 1.9 GB, once).
That is all. `start.bat` also starts Ollama if it is not running and loads the model into memory, so the first Translate is quick.

## Speed
- This PC has no strong graphics card, so Ollama works on the processor. A small model (`qwen2.5:3b`) gives an answer in a few seconds.
- A bigger model (`gemma2:9b`) is better at Gujarati but much slower. Change it in `.env`: `OLLAMA_MODEL=gemma2:9b`.
- `OLLAMA_KEEP_ALIVE=-1` (default) keeps the model in memory, so only the first answer after a restart is slow.

## If it says "AI is offline"
Ollama is not running: open the Ollama app, or run `scripts\ollama-ready.bat`. The rest of the software works without it; Gujarati and Hindi can be typed by hand.
