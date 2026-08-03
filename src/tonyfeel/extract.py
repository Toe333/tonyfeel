"""Extract a feel pack from a drum WAV (Beat This + kick/snare pocket).

Optional Demucs: if input is a full mix, isolate drums first when demucs is installed.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf


def _load_mono(path: Path, sr: int = 44100) -> tuple[np.ndarray, int]:
    import librosa

    y, _ = librosa.load(str(path), sr=sr, mono=True)
    return y.astype(np.float32), sr


def _band_envs(y: np.ndarray, sr: int, hop: int = 256):
    import librosa

    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
    times = librosa.frames_to_time(np.arange(S.shape[1]), sr=sr, hop_length=hop)

    def band(lo, hi):
        m = (freqs >= lo) & (freqs < hi)
        e = S[m].sum(axis=0)
        return e / (np.percentile(e, 95) + 1e-9)

    return times, band(40, 120), band(160, 500), band(5000, 12000)


def _peak_near(times, env, t, half, thr=0.15):
    m = (times >= t - half) & (times <= t + half)
    if not m.any():
        return None, 0.0
    local = np.where(m, env, -1.0)
    i = int(np.argmax(local))
    strength = float(env[i])
    if strength < thr:
        return None, strength
    return float(times[i]), strength


def _stats(offs_ms: list[float]) -> dict[str, Any] | None:
    if not offs_ms:
        return None
    a = np.asarray(offs_ms, float)
    mean = float(np.mean(a))
    std = float(np.std(a))
    ahead = float(np.mean(a < -5))
    behind = float(np.mean(a > 5))
    if abs(mean) < 3:
        pocket = "ON the grid (centered)"
    elif mean < 0:
        pocket = "PUSHING (ahead)"
    else:
        pocket = "LAID-BACK (behind)"
    return {
        "n": int(len(a)),
        "mean_ms": round(mean, 2),
        "std_ms": round(std, 2),
        "median_ms": round(float(np.median(a)), 2),
        "on_pm10": round(float(np.mean(np.abs(a) <= 10)), 3),
        "ahead_frac": round(ahead, 3),
        "behind_frac": round(behind, 3),
        "pocket": pocket,
    }


def _maybe_demucs(wav: Path, work: Path) -> Path:
    """If demucs available, isolate drums; else return original wav."""
    try:
        import demucs.separate  # noqa: F401
    except ImportError:
        return wav

    # Run demucs via subprocess for isolation from cwd
    import subprocess
    import sys

    out_dir = work / "demucs"
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "demucs",
        "--two-stems=drums",
        "-o",
        str(out_dir),
        str(wav),
    ]
    print(f"demucs: {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True)
    # demucs writes out_dir/<model>/<stem>/drums.wav
    hits = list(out_dir.rglob("drums.wav"))
    if not hits:
        print("demucs: no drums.wav found — using original", flush=True)
        return wav
    return hits[0]


def _beat_this(path: Path, device: str = "cpu"):
    from beat_this.inference import File2Beats

    f2b = File2Beats(checkpoint_path="final0", device=device)
    beats, downs = f2b(str(path))
    return np.asarray([float(x) for x in beats], float), np.asarray(
        [float(x) for x in downs], float
    )


def extract_feel(
    wav_path: str | Path,
    out_json: str | Path,
    *,
    name: str = "custom",
    credit: str = "",
    device: str = "cpu",
    use_demucs: bool = False,
    seed_bpm: float | None = None,
    apply_amount: float = 0.10,
) -> Path:
    """Analyze drum WAV → feel JSON pack. Returns path written."""
    wav_path = Path(wav_path)
    out_json = Path(out_json)
    if not wav_path.exists():
        raise FileNotFoundError(wav_path)

    with tempfile.TemporaryDirectory(prefix="tonyfeel_") as tmp:
        work = Path(tmp)
        src = wav_path
        if use_demucs:
            src = _maybe_demucs(wav_path, work)

        print(f"Beat This on {src} (device={device})…", flush=True)
        beats, downs = _beat_this(src, device=device)
        if len(beats) < 8:
            raise RuntimeError(f"too few beats ({len(beats)}) — check audio")

        y, sr = _load_mono(src)
        times, kick, snare, hat = _band_envs(y, sr)

        if len(downs) == 0:
            downs = beats[::4]

        io = np.diff(beats)
        med_bpm = float(60.0 / np.median(io)) if len(io) else 120.0
        bpm = float(seed_bpm) if seed_bpm is not None else med_bpm
        quarter = 60.0 / bpm

        kick_offs, snare_offs, hat_offs = [], [], []
        for td in downs:
            half = max(0.06, 0.22 * quarter)
            # nearest raw beat to this downbeat (pocket vs raw grid)
            j1 = int(np.argmin(np.abs(beats - td)))
            t1 = float(beats[j1])
            j2 = int(np.argmin(np.abs(beats - (t1 + quarter))))
            t2 = float(beats[j2])

            tk, sk = _peak_near(times, kick, t1, half, thr=0.15)
            ts, ss = _peak_near(times, snare, t2, half * 0.9, thr=0.18)
            if tk is not None:
                kick_offs.append((tk - t1) * 1000.0)
            if ts is not None:
                snare_offs.append((ts - t2) * 1000.0)

        # hat vs 8ths from raw beats
        for i in range(len(beats) - 1):
            t8a = float(beats[i])
            t8b = (float(beats[i]) + float(beats[i + 1])) / 2.0
            for t8 in (t8a, t8b):
                th, sh = _peak_near(times, hat, t8, 0.045, thr=0.22)
                if th is not None:
                    hat_offs.append((th - t8) * 1000.0)

        kick_s = _stats(kick_offs)
        snare_s = _stats(snare_offs)
        hat_s = _stats(hat_offs)
        kit_offs = kick_offs + snare_offs
        kit_s = _stats(kit_offs)

        if not kick_s and not snare_s:
            raise RuntimeError("could not locate kick/snare peaks — try a cleaner drum stem")

        kit_std = float((kit_s or {}).get("std_ms", 18.0))
        hat_std = min(float(hat_s["std_ms"]), kit_std) if hat_s else kit_std
        bias_kick = float(kick_s["mean_ms"]) if kick_s else 0.0
        std_kit = kit_std

        retimer = {
            "timing_std_ms": round(std_kit, 2),
            "timing_bias_ms": round(bias_kick, 2),
            "apply_amount": float(apply_amount),
            "swing_bur": 1.0,
            "velocity_jitter": 6,
            "seed": 2007,
            "method": "beat_this_kick1_snare2",
            "source_window": "all_bars_kick+snare",
            "voices": {
                "kick": {
                    "bias_ms": round(kick_s["mean_ms"], 2) if kick_s else 0.0,
                    "std_ms": round(kick_s["std_ms"], 2) if kick_s else round(std_kit, 2),
                },
                "snare": {
                    "bias_ms": round(snare_s["mean_ms"], 2) if snare_s else 0.0,
                    "std_ms": round(snare_s["std_ms"], 2) if snare_s else round(std_kit, 2),
                },
                "hat": {
                    "bias_ms": round(hat_s["mean_ms"], 2) if hat_s else 0.0,
                    "std_ms": round(hat_std, 2),
                },
                "kit": {
                    "bias_ms": round(kit_s["mean_ms"], 2) if kit_s else 0.0,
                    "std_ms": round(kit_std, 2),
                },
                "note": "voice-locked apply; bias=voice mean, std×amount",
            },
        }

        profile = {
            "version": "tonyfeel_v1",
            "name": name,
            "credits": {
                "performer": credit or name,
                "source_audio": wav_path.name,
                "note": "Measured pocket for MIDI retiming. Not a full transcription.",
            },
            "method": "Beat This quarters + kick→1 / snare→2 pocket",
            "seed_bpm": round(bpm, 2),
            "tempo": {
                "bpm_median": round(med_bpm, 2),
                "n_beats": int(len(beats)),
                "n_downbeats": int(len(downs)),
            },
            "voices": {
                "kick": {"all": kick_s},
                "snare": {"all": snare_s},
                "hat_8ths": hat_s,
                "kit_all": kit_s,
            },
            "retimer": retimer,
            "how_to_read": {
                "sign": "negative ms = ahead / pushing; positive = laid-back / behind",
                "apply": "voice-locked jitter; amount scales std only",
            },
        }

        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(profile, indent=2) + "\n")
        print(f"wrote {out_json}", flush=True)
        if kick_s:
            print(f"  kick: {kick_s['mean_ms']:+.1f} ms ±{kick_s['std_ms']:.1f}  ({kick_s['pocket']})")
        if snare_s:
            print(f"  snare: {snare_s['mean_ms']:+.1f} ms ±{snare_s['std_ms']:.1f}  ({snare_s['pocket']})")
        return out_json
