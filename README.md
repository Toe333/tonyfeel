---
title: TonyFeel
emoji: 🥁
colorFrom: yellow
colorTo: red
sdk: gradio
sdk_version: "5.0.0"
app_file: app.py
pinned: false
license: mit
short_description: Apply measured drummer pocket to quantized MIDI
---

# TonyFeel

**Quantized MIDI in → real drummer pocket out.**

TonyFeel measures microtiming from a real drum performance and applies that pocket to dead-quantized GM drum MIDI — voice-locked, not drunk random jitter.

## Demo (30 seconds)

| File | What |
|---|---|
| [`demo/mad_4bars.wav`](demo/mad_4bars.wav) | Tony Bollas — 4 bars solo live drums @ **114.219 BPM** |
| [`demo/groove_quantized.mid`](demo/groove_quantized.mid) | Same groove, on the grid |
| [`demo/groove_with_feel.mid`](demo/groove_with_feel.mid) | Same notes + **4-bar pack @ 25%** (default) |

**Canon pack:** [`packs/tony_bollas_mad_4bar.json`](packs/tony_bollas_mad_4bar.json) — measured from the demo WAV only.

- Kick: ~**−11.8 ms** (pushes)
- Snare: ~**−5.6 ms** (pushes)
- Hat: ~**+19.8 ms** (sits back)
- Default apply amount: **25%**

Secondary (full-song verse): [`packs/tony_bollas_mad.json`](packs/tony_bollas_mad.json)

## Install

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -e .
```

Optional extract extras (Beat This + librosa):

```bash
uv pip install --python .venv/bin/python -e ".[extract]"
```

## CLI

```bash
# Apply default pack (4-bar) at pack default 25%
tonyfeel apply song.mid -o song_felt.mid

# Explicit
tonyfeel apply song.mid --feel tony_bollas_mad_4bar -p 25 -o song_felt.mid

# List packs
tonyfeel packs

# Measure feel from your own drum stem (needs [extract])
tonyfeel extract drums.wav -o my_feel.json --credit "Your Name" --device cuda

# Optional: isolate drums from a mix first
tonyfeel extract mix.wav --demucs -o my_feel.json
```

## Python

```python
from tonyfeel import apply_feel

apply_feel("groove_quantized.mid", amount=0.25, out_path="felt.mid")
# → uses tony_bollas_mad_4bar by default
```

## Hugging Face Space

This repo is a Gradio Space (`app.py`). Upload a MIDI (or use the demo), pick a pack, set amount, download felt MIDI.

Deploy (needs an HF token with **Write** scope):

```bash
hf auth login
bash scripts/push_space.sh Toe333/tonyfeel
```

Then open: https://huggingface.co/spaces/Toe333/tonyfeel

## How it works

1. **Extract** (optional): Beat This finds the beat grid → kick vs downbeat / snare vs beat 2 → feel JSON  
2. **Apply**: one timing offset per (onset × voice); bias = measured mean; std × amount  
3. Default amount is **25%** of measured scatter (bias applied fully)

## Credits

- Performance / feel pack: **Tony Bollas**
- Beat tracker: [Beat This!](https://github.com/CPJKU/beat_this) (MIT)
- Optional stem sep: [Demucs](https://github.com/facebookresearch/demucs) (MIT)

Demo audio is a **short excerpt** only. Bring your own takes for new packs.

## License

MIT — see [LICENSE](LICENSE)
