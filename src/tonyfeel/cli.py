"""tonyfeel CLI — apply | extract | packs | demo."""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from tonyfeel import __version__
from tonyfeel.apply import apply_feel
from tonyfeel.feel import DEMO_DIR, PACKS_DIR, list_packs, pack_path


def _cmd_apply(args):
    amount = args.amount
    if args.percent is not None:
        amount = float(args.percent) / 100.0
    out = apply_feel(
        args.midi,
        feel_path=args.feel,
        out_path=args.out,
        amount=amount,
        seed=args.seed,
        mono=args.mono,
        bias_ms=args.bias_ms,
        std_ms=args.std_ms,
        density=args.density,
        all_channels=args.all_channels,
    )
    print(f"wrote {out}")


def _cmd_extract(args):
    from tonyfeel.extract import extract_feel

    out = args.out
    if out is None:
        out = Path(args.wav).with_suffix(".feel.json")
    extract_feel(
        args.wav,
        out,
        name=args.name,
        credit=args.credit,
        device=args.device,
        use_demucs=args.demucs,
        seed_bpm=args.bpm,
        apply_amount=(args.percent / 100.0) if args.percent is not None else 0.10,
    )


def _cmd_packs(_args):
    packs = list_packs()
    if not packs:
        print(f"(no packs in {PACKS_DIR})")
        return
    for name in packs:
        p = pack_path(name)
        print(f"{name:30s}  {p}")


def _cmd_demo(args):
    """Copy demo assets to a directory (or print their paths)."""
    assets = [
        DEMO_DIR / "mad_4bars.wav",
        DEMO_DIR / "groove_quantized.mid",
        DEMO_DIR / "groove_with_feel.mid",
        DEMO_DIR / "README.md",
    ]
    if args.out:
        dest = Path(args.out)
        dest.mkdir(parents=True, exist_ok=True)
        for a in assets:
            if a.exists():
                shutil.copy2(a, dest / a.name)
                print(f"copied {a.name} → {dest / a.name}")
            else:
                print(f"missing {a}", file=sys.stderr)
    else:
        for a in assets:
            print(f"{'OK' if a.exists() else 'MISSING':7s}  {a}")


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="tonyfeel",
        description="Apply measured drummer pocket to quantized MIDI.",
    )
    ap.add_argument("--version", action="version", version=f"tonyfeel {__version__}")
    sp = ap.add_subparsers(dest="cmd", required=True)

    p = sp.add_parser("apply", help="retime MIDI with a feel pack")
    p.add_argument("midi", help="input .mid")
    p.add_argument(
        "--feel",
        default="tony_bollas_mad_4bar",
        help="pack name or path (default: tony_bollas_mad_4bar)",
    )
    p.add_argument("-o", "--out", help="output .mid")
    p.add_argument(
        "-p",
        "--percent",
        type=float,
        default=None,
        help="feel amount as percent (default: pack apply_amount, usually 25)",
    )
    p.add_argument("--amount", type=float, default=None, help="feel amount 0..1 (alt to -p)")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--mono", action="store_true", help="legacy mono kit-lock")
    p.add_argument("--bias-ms", type=float, default=None)
    p.add_argument("--std-ms", type=float, default=None)
    p.add_argument("--density", type=float, default=1.0)
    p.add_argument("-a", "--all-channels", action="store_true")
    p.set_defaults(func=_cmd_apply)

    e = sp.add_parser("extract", help="measure feel from a drum WAV (needs beat-this)")
    e.add_argument("wav", help="drum stem or mix (.wav)")
    e.add_argument("-o", "--out", help="output feel JSON")
    e.add_argument("--name", default="custom", help="pack display name")
    e.add_argument("--credit", default="", help="performer credit string")
    e.add_argument("--device", default="cpu", help="cpu or cuda for Beat This")
    e.add_argument("--demucs", action="store_true", help="isolate drums with Demucs first")
    e.add_argument("--bpm", type=float, default=None, help="seed BPM hint")
    e.add_argument("-p", "--percent", type=float, default=25.0, help="default apply amount %%")
    e.set_defaults(func=_cmd_extract)

    k = sp.add_parser("packs", help="list bundled feel packs")
    k.set_defaults(func=_cmd_packs)

    d = sp.add_parser("demo", help="show or copy demo assets")
    d.add_argument("-o", "--out", help="copy demo files into this directory")
    d.set_defaults(func=_cmd_demo)

    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
