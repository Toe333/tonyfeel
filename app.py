#!/usr/bin/env python3
"""TonyFeel — Hugging Face Gradio Space (cpu-basic apply demo)."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import gradio as gr
from tonyfeel.apply import apply_feel
from tonyfeel.feel import DEMO_DIR, list_packs, pack_path

DEMO_WAV = DEMO_DIR / "mad_4bars.wav"
DEMO_Q = DEMO_DIR / "groove_quantized.mid"
DEMO_F = DEMO_DIR / "groove_with_feel.mid"


def _packs():
    names = list_packs()
    return names or ["tony_bollas_mad"]


def run_apply(midi_file, pack_name, percent, mono):
    if midi_file is None:
        raise gr.Error("Upload a MIDI file, or click Load demo groove first.")
    src = Path(midi_file if isinstance(midi_file, str) else midi_file.name)
    if not src.exists():
        raise gr.Error(f"missing MIDI: {src}")
    amount = float(percent) / 100.0
    feel = pack_path(pack_name)
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / f"{src.stem}_tonyfeel_p{int(percent)}.mid"
        apply_feel(
            src,
            feel,
            out_path=out,
            amount=amount,
            mono=bool(mono),
            seed=2007,
        )
        # Persist outside temp for Gradio download
        durable = Path(tempfile.gettempdir()) / out.name
        durable.write_bytes(out.read_bytes())
        return str(durable)


def load_demo():
    if not DEMO_Q.exists():
        raise gr.Error("demo/groove_quantized.mid missing from Space checkout")
    return str(DEMO_Q)


def build() -> gr.Blocks:
    packs = _packs()
    with gr.Blocks(title="TonyFeel") as demo:
        gr.Markdown(
            """
# TonyFeel
**Quantized MIDI in → real drummer pocket out.**

Voice-locked microtiming from a real drum take (kick sit / snare push),
not random humanize. Demo pack: **Tony Bollas** (4-bar live excerpt).
"""
        )
        with gr.Row():
            with gr.Column():
                if DEMO_WAV.exists():
                    gr.Audio(
                        value=str(DEMO_WAV),
                        label="Tony Bollas — MAD 4-bar solo drums (excerpt)",
                        type="filepath",
                    )
                gr.Markdown(
                    "Credit: Tony Bollas, drums. Excerpt only — not a full-song release."
                )
            with gr.Column():
                midi_in = gr.File(
                    label="MIDI in (GM drums on ch.10)",
                    file_types=[".mid", ".midi"],
                    type="filepath",
                )
                pack = gr.Dropdown(
                    choices=packs,
                    value=packs[0],
                    label="Feel pack",
                )
                percent = gr.Slider(
                    1,
                    50,
                    value=10,
                    step=1,
                    label="Amount (%)",
                    info="10% is the default sweet spot; 50% sounds drunk",
                )
                mono = gr.Checkbox(label="Mono kit-lock (legacy A/B)", value=False)
                with gr.Row():
                    btn_demo = gr.Button("Load demo groove")
                    btn_run = gr.Button("Apply feel", variant="primary")
                midi_out = gr.File(label="Felt MIDI out")

        btn_demo.click(fn=load_demo, outputs=midi_in)
        btn_run.click(
            fn=run_apply,
            inputs=[midi_in, pack, percent, mono],
            outputs=midi_out,
        )

        if DEMO_Q.exists() and DEMO_F.exists():
            gr.Markdown("### Pre-rendered demo pair")
            with gr.Row():
                gr.File(value=str(DEMO_Q), label="groove_quantized.mid")
                gr.File(value=str(DEMO_F), label="groove_with_feel.mid (10%)")

        gr.Markdown(
            """
### CLI
```bash
tonyfeel apply song.mid --feel tony_bollas_mad -p 10 -o song_felt.mid
tonyfeel extract drums.wav -o my_feel.json   # needs [extract] extras
```
MIT · [GitHub](https://github.com/Toe333/tonyfeel)
"""
        )
    return demo


if __name__ == "__main__":
    build().launch()
