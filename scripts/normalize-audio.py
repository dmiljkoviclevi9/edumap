#!/usr/bin/env python3
# normalize-audio.py
# EBU R128 loudness normalization for the EduMap audio library.
#
# Why this exists:
#   ElevenLabs returns clips with wildly varying perceived loudness — a short
#   word like "Čad" is far quieter than a long phrase like "Ujedinjeni arapski
#   emirati", even with the same voice settings. Without normalization, kids
#   constantly reach for the volume slider. EBU R128 (LUFS-based) measures
#   perceived loudness the way ears actually work — the standard every
#   streaming platform uses — so the corrected files all hit the same
#   subjective volume regardless of duration or stress pattern.
#
# Two-pass loudnorm:
#   Pass 1 measures the file's integrated loudness, true peak, loudness range,
#   and threshold. Pass 2 applies a precise correction using those measured
#   values. Single-pass is faster but less accurate (can clip transients on
#   short clips). Worth the extra ffmpeg invocation for 251 country names.
#
# Targets (defaults):
#   -16 LUFS — spoken-word streaming standard (Apple Podcasts, audiobooks).
#              Louder than EBU broadcast (-23) so it works in noisy rooms.
#   -1.5 dBTP — true-peak cap with safety margin for MP3 encoding artifacts.
#   LRA 11    — preserves natural dynamics; lower compresses more.
#
# Idempotent-ish: re-running normalizes already-normalized files (which is a
# no-op in practice — measured ≈ target so offset ≈ 0). Wastes ~1s per file
# but doesn't corrupt anything.
#
# Usage:
#   python -X utf8 scripts/normalize-audio.py --locale sr-Cyrl
#   python -X utf8 scripts/normalize-audio.py --locale sr-Cyrl --dry-run
#   python -X utf8 scripts/normalize-audio.py --locale sr-Cyrl --limit 5
#
# Requires ffmpeg on PATH. Install on Windows:
#   winget install Gyan.FFmpeg
# Then restart your shell so the PATH update takes effect.

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys


def require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        sys.exit(
            "Error: ffmpeg not found on PATH.\n"
            "  Install with: winget install Gyan.FFmpeg\n"
            "  Then restart your shell so PATH refreshes."
        )


def measure(input_path: pathlib.Path, target_i: float, target_tp: float, target_lra: float) -> dict:
    """Pass 1: measure the file's loudness statistics.

    loudnorm prints a JSON blob to stderr at the end of analysis. We grab the
    last {...} block — earlier {...} matches can occur in info lines on some
    ffmpeg builds.
    """
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats",
        "-i", str(input_path),
        "-af", f"loudnorm=I={target_i}:TP={target_tp}:LRA={target_lra}:print_format=json",
        "-f", "null", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg measure failed (exit {proc.returncode}):\n{proc.stderr[-500:]}")

    matches = list(re.finditer(r"\{[^{}]*\}", proc.stderr, re.DOTALL))
    if not matches:
        raise RuntimeError(f"No JSON block found in ffmpeg output:\n{proc.stderr[-500:]}")
    return json.loads(matches[-1].group(0))


def apply_normalization(
    input_path: pathlib.Path,
    output_path: pathlib.Path,
    stats: dict,
    target_i: float,
    target_tp: float,
    target_lra: float,
    bitrate: str,
    sample_rate: int,
) -> None:
    """Pass 2: apply the loudness correction using measured values."""
    af = (
        f"loudnorm=I={target_i}:TP={target_tp}:LRA={target_lra}:"
        f"measured_I={stats['input_i']}:measured_TP={stats['input_tp']}:"
        f"measured_LRA={stats['input_lra']}:measured_thresh={stats['input_thresh']}:"
        f"offset={stats['target_offset']}:linear=true:print_format=summary"
    )
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-nostats", "-loglevel", "error",
        "-i", str(input_path),
        "-af", af,
        "-c:a", "libmp3lame", "-b:a", bitrate, "-ar", str(sample_rate),
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg apply failed (exit {proc.returncode}):\n{proc.stderr[-500:]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="EBU R128 loudness normalization for EduMap audio.")
    parser.add_argument("--locale", default="sr-Cyrl",
                        help="BCP-47 locale subdirectory under --audio-dir (default: sr-Cyrl)")
    parser.add_argument("--audio-dir", default="src/EduMap.Api/wwwroot/audio",
                        help="Audio root; processes <audio-dir>/<locale>/*.mp3")
    parser.add_argument("--target-i", type=float, default=-16.0,
                        help="Integrated loudness target in LUFS (default: -16, spoken-word standard)")
    parser.add_argument("--target-tp", type=float, default=-1.5,
                        help="True-peak target in dBTP (default: -1.5, MP3-safe margin)")
    parser.add_argument("--target-lra", type=float, default=11.0,
                        help="Loudness range target (default: 11, preserves natural dynamics)")
    parser.add_argument("--bitrate", default="96k",
                        help="Output MP3 bitrate (default: 96k, plenty for speech)")
    parser.add_argument("--sample-rate", type=int, default=44100,
                        help="Output sample rate (default: 44100)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Measure only; report stats without rewriting files")
    parser.add_argument("--limit", type=int, default=0,
                        help="Stop after N files (0 = no limit)")
    args = parser.parse_args()

    require_ffmpeg()

    audio_dir = pathlib.Path(args.audio_dir) / args.locale
    if not audio_dir.is_dir():
        sys.exit(f"Error: audio directory does not exist: {audio_dir}")

    files = sorted(audio_dir.glob("*.mp3"))
    if args.limit:
        files = files[:args.limit]

    if not files:
        sys.exit(f"No .mp3 files found in {audio_dir}")

    print(f"Locale     : {args.locale}")
    print(f"Audio dir  : {audio_dir}")
    print(f"Target     : I={args.target_i} LUFS  TP={args.target_tp} dBTP  LRA={args.target_lra}")
    print(f"Encoding   : libmp3lame {args.bitrate} @ {args.sample_rate} Hz")
    print(f"Files      : {len(files)}  {'(dry-run)' if args.dry_run else ''}")
    print()

    ok = fail = 0
    total_offset_abs = 0.0
    for path in files:
        try:
            stats = measure(path, args.target_i, args.target_tp, args.target_lra)
            in_i = float(stats["input_i"])
            in_tp = float(stats["input_tp"])
            offset = float(stats["target_offset"])
            total_offset_abs += abs(offset)

            if args.dry_run:
                print(f"  {path.name:14s}  in={in_i:+6.2f} LUFS  TP={in_tp:+6.2f} dBTP  -> offset={offset:+5.2f} dB")
                ok += 1
                continue

            tmp_path = path.with_suffix(".tmp.mp3")
            apply_normalization(
                path, tmp_path, stats,
                args.target_i, args.target_tp, args.target_lra,
                args.bitrate, args.sample_rate,
            )
            os.replace(tmp_path, path)
            print(f"  {path.name:14s}  in={in_i:+6.2f} LUFS  -> {args.target_i:+.1f} LUFS  (offset {offset:+.2f} dB)")
            ok += 1
        except Exception as e:
            print(f"  {path.name:14s}  FAIL — {e}")
            fail += 1
            tmp_path = path.with_suffix(".tmp.mp3")
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    avg_offset = total_offset_abs / max(ok, 1)
    print()
    print(f"Result: {ok} {'measured' if args.dry_run else 'normalized'}, {fail} failed  |  avg |offset| was {avg_offset:.2f} dB")


if __name__ == "__main__":
    main()
