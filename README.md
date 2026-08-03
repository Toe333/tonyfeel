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

TonyFeel measures microtiming from a real drum performance (kick layback, snare push, hat sit) and applies that pocket to dead-quantized GM drum MIDI — voice-locked, not drunk random jitter.

## Demo (30 seconds)

| File | What |
|---|---|
| [`demo/mad_4bars.wav`](demo/mad_4bars.wav) | Tony Bollas — 4 bars of solo live drums (excerpt) |
| [`demo/groove_quantized.mid`](demo/groove_quantized.mid) | Same groove, on the grid |
| [`demo/groove_with_feel.mid`](demo/groove_with_feel.mid) | Same notes + TonyFeel @ 10% |

Pack: [`packs/tony_bollas_mad.json`](packs/tony_bollas_mad.json)

- Kick (verse): ~**+1.2 ms** (on/slightly back)
- Snare (verse): ~**−7.8 ms** (pushes)
- Default apply amount: **10%** of measured scatter

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
# Apply bundled Tony Bollas pack at 10%
tonyfeel apply song.mid --feel tony_bollas_mad -p 10 -o song_felt.mid

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

apply_feel("groove_quantized.mid", "tony_bollas_mad", amount=0.10, out_path="felt.mid")
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
3. Default amount is low (~10%) so it humanizes instead of stumbling

## Credits

- Performance / feel pack: **Tony Bollas**
- Beat tracker: [Beat This!](https://github.com/CPJKU/beat_this) (MIT)
- Optional stem sep: [Demucs](https://github.com/facebookresearch/demucs) (MIT)

Demo audio is a **short excerpt** only. Bring your own takes for new packs.

## License

MIT — see [LICENSE](LICENSE)
