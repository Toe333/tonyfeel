"""Voice-locked MIDI retimer — apply a feel pack to quantized MIDI."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import mido
import numpy as np

from tonyfeel.feel import load_feel

# GM drum note → feel voice. Non-drums / unknown kit → "kit".
_DRUM_VOICE = {
    35: "kick",
    36: "kick",
    37: "snare",
    38: "snare",
    39: "snare",
    40: "snare",
    42: "hat",
    44: "hat",
    46: "hat",
    49: "crash",
    51: "crash",
    57: "crash",
}


def feel_voice(note: int, ch: int) -> str:
    if ch != 9:
        return "kit"
    return _DRUM_VOICE.get(int(note), "kit")


def voice_timing_maps(
    ret: dict[str, Any],
    full: dict[str, Any],
    amount: float,
    cli_bias: float | None = None,
    cli_std: float | None = None,
    force_mono: bool = False,
) -> tuple[dict[str, tuple[float, float]], bool, float, float]:
    """Per-voice (bias_ms, std_ms) for apply.

    Bias = measured voice mean (full). Std = measured voice std × amount, clamped.
    Hat scatter capped to kit std. --mono / bias/std overrides → mono kit-lock.
    """
    meas_std = float(ret.get("timing_std_ms", 20.0))
    meas_bias = float(ret.get("timing_bias_ms", 0.0))

    def _clamp_std(s: float) -> float:
        return float(min(max(float(s), 0.0), 18.0))

    if force_mono or cli_bias is not None or cli_std is not None:
        b = float(cli_bias) if cli_bias is not None else meas_bias
        s = _clamp_std(cli_std if cli_std is not None else meas_std * amount)
        return {"kit": (b, s)}, True, meas_bias, meas_std

    rv = ret.get("voices") or {}
    bias_of: dict[str, float] = {}
    std_of: dict[str, float] = {}
    for key in ("kick", "snare", "hat", "kit", "crash"):
        block = rv.get(key)
        if isinstance(block, dict) and "bias_ms" in block:
            bias_of[key] = float(block["bias_ms"])
            std_of[key] = float(block.get("std_ms", meas_std))

    if not bias_of and isinstance(full, dict):
        vv = full.get("voices") or {}

        def _pick(node, *path):
            cur = node
            for p in path:
                if not isinstance(cur, dict):
                    return None
                cur = cur.get(p)
            return cur if isinstance(cur, dict) else None

        kick = _pick(vv, "kick", "verse") or _pick(vv, "kick", "all")
        snare = _pick(vv, "snare", "verse") or _pick(vv, "snare", "all")
        hat = vv.get("hat_8ths") if isinstance(vv.get("hat_8ths"), dict) else None
        kit = vv.get("kit_verse") if isinstance(vv.get("kit_verse"), dict) else None
        if kick and "mean_ms" in kick:
            bias_of["kick"] = float(kick["mean_ms"])
            std_of["kick"] = float(kick.get("std_ms", meas_std))
        if snare and "mean_ms" in snare:
            bias_of["snare"] = float(snare["mean_ms"])
            std_of["snare"] = float(snare.get("std_ms", meas_std))
        if hat and "mean_ms" in hat:
            bias_of["hat"] = float(hat["mean_ms"])
            kit_std = float((kit or {}).get("std_ms", meas_std))
            std_of["hat"] = min(float(hat.get("std_ms", kit_std)), kit_std)
        if kit and "mean_ms" in kit:
            bias_of["kit"] = float(kit["mean_ms"])
            std_of["kit"] = float(kit.get("std_ms", meas_std))

    if not bias_of:
        s = _clamp_std(meas_std * amount)
        return {"kit": (meas_bias, s)}, True, meas_bias, meas_std

    kit_b = bias_of.get("kit", meas_bias)
    kit_s = std_of.get("kit", meas_std)
    bias_of.setdefault("kit", kit_b)
    std_of.setdefault("kit", kit_s)
    bias_of.setdefault("crash", kit_b)
    std_of.setdefault("crash", kit_s)
    for v in ("kick", "snare", "hat"):
        bias_of.setdefault(v, kit_b)
        std_of.setdefault(v, kit_s)

    out = {
        v: (bias_of[v], _clamp_std(std_of[v] * amount))
        for v in ("kick", "snare", "hat", "crash", "kit")
    }
    return out, False, meas_bias, meas_std


def apply_feel(
    midi_path: str | Path,
    feel_path: str | Path | None = None,
    *,
    out_path: str | Path | None = None,
    amount: float | None = None,
    seed: int | None = None,
    mono: bool = False,
    bias_ms: float | None = None,
    std_ms: float | None = None,
    velocity_jitter: int | None = None,
    density: float = 1.0,
    all_channels: bool = False,
    channels: set[int] | None = None,
) -> Path:
    """Apply feel pack to MIDI. Returns output path.

    Default: drum channel 10 (ch index 9) only. amount scales measured std;
    bias is applied fully. One offset per (onset tick × voice).
    """
    ret, full = load_feel(feel_path)
    rng = np.random.default_rng(seed if seed is not None else ret.get("seed", 2007))
    amt = float(amount) if amount is not None else float(ret.get("apply_amount", 0.25))
    voice_map, is_mono, meas_bias, meas_std = voice_timing_maps(
        ret, full, amt, cli_bias=bias_ms, cli_std=std_ms, force_mono=mono
    )
    vel_j = (
        velocity_jitter
        if velocity_jitter is not None
        else min(int(ret.get("velocity_jitter", 8)), 6)
    )

    if all_channels:
        chans = None
    elif channels is not None:
        chans = set(channels)
    else:
        chans = {9}

    def _hit(ch):
        return chans is None or ch in chans

    midi_path = Path(midi_path)
    mid = mido.MidiFile(str(midi_path))
    tempo = 500000
    for tr in mid.tracks:
        for msg in tr:
            if msg.type == "set_tempo":
                tempo = msg.tempo
                break
    tpb = mid.ticks_per_beat
    ms_per_tick = (tempo / 1000.0) / tpb

    out = mido.MidiFile(ticks_per_beat=tpb)
    for tr in mid.tracks:
        abs_t = 0
        events = []
        for msg in tr:
            abs_t += msg.time
            events.append([abs_t, msg.copy()])

        keys = set()
        for t, m in events:
            if m.type == "note_on" and m.velocity > 0 and _hit(getattr(m, "channel", 0)):
                voice = "kit" if is_mono else feel_voice(m.note, getattr(m, "channel", 0))
                keys.add((t, voice))
        jitter_map = {}
        for t, voice in keys:
            b_ms, s_ms = voice_map.get(voice, voice_map["kit"])
            j_ms = b_ms + float(rng.normal(0.0, s_ms))
            jitter_map[(t, voice)] = int(round(j_ms / ms_per_tick))

        pending: dict[tuple, list] = {}
        new_events = []
        dropped = set()

        for abs_tick, msg in events:
            ch = getattr(msg, "channel", None)
            if msg.type == "note_on" and msg.velocity > 0 and _hit(ch):
                if density < 1.0 and ch == 9 and msg.note in (42, 44, 46) and rng.random() > density:
                    dropped.add((ch, msg.note, abs_tick))
                    continue
                voice = "kit" if is_mono else feel_voice(msg.note, ch)
                jt = jitter_map.get((abs_tick, voice), 0)
                new_t = max(0, abs_tick + jt)
                v = int(np.clip(msg.velocity + int(rng.integers(-vel_j, vel_j + 1)), 1, 127))
                new_msg = msg.copy(velocity=v)
                pending.setdefault((ch, msg.note), []).append((abs_tick, new_t))
                new_events.append([new_t, new_msg])
            elif (
                msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0)
            ) and _hit(ch):
                key = (ch, msg.note)
                q = pending.get(key)
                if not q:
                    new_events.append([abs_tick, msg])
                    continue
                old_on, new_on = q.pop(0)
                if (ch, msg.note, old_on) in dropped:
                    continue
                dur = abs_tick - old_on
                new_events.append([max(0, new_on + dur), msg.copy()])
            else:
                new_events.append([abs_tick, msg])

        new_events.sort(
            key=lambda e: (
                e[0],
                0
                if (
                    e[1].type == "note_off"
                    or (e[1].type == "note_on" and e[1].velocity == 0)
                )
                else 1,
            )
        )
        ntr = mido.MidiTrack()
        prev = 0
        for abs_tick, msg in new_events:
            msg.time = max(0, abs_tick - prev)
            prev = abs_tick
            ntr.append(msg)
        out.tracks.append(ntr)

    if out_path is None:
        out_path = midi_path.with_name(midi_path.stem + "_tonyfeel.mid")
    else:
        out_path = Path(out_path)
    out.save(str(out_path))
    return out_path
