#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║          TRANSCRIBE-AI  ·  Groq Whisper + pyannote           ║
║     Smart splitting · Speaker diarization · Timestamps       ║
╚══════════════════════════════════════════════════════════════╝
Auto-installs missing dependencies on first run.
Reads API tokens from ~/.config/transcribe/config or environment.
"""

import os, re, sys, json, math, shutil, tempfile, argparse, subprocess, time

# ── Bootstrap: rich first (needed for all UI) ─────────────────────
def _pip(*pkgs):
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", *pkgs], check=True)

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import (Progress, SpinnerColumn, BarColumn,
                                TextColumn, TimeElapsedColumn, TaskProgressColumn)
    from rich.table import Table
    from rich.text import Text
    from rich import box
except ImportError:
    print("Installing rich…")
    _pip("rich")
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import (Progress, SpinnerColumn, BarColumn,
                                TextColumn, TimeElapsedColumn, TaskProgressColumn)
    from rich.table import Table
    from rich.text import Text
    from rich import box

console = Console()

REQUIRED_PACKAGES = ["requests", "pyannote.audio", "torch", "torchaudio"]
# Windows: respect TRANSCRIBE_CONFIG env var or use APPDATA; Unix: ~/.config/transcribe/config
if os.name == "nt":
    _cfg_base = os.environ.get("APPDATA", os.path.expanduser("~"))
    CONFIG_FILE = os.environ.get(
        "TRANSCRIBE_CONFIG",
        os.path.join(_cfg_base, "transcribe", "config"),
    )
else:
    CONFIG_FILE = os.environ.get(
        "TRANSCRIBE_CONFIG",
        os.path.expanduser("~/.config/transcribe/config"),
    )
GROQ_API_URL       = "https://api.groq.com/openai/v1/audio/transcriptions"
MAX_BYTES          = 24 * 1024 * 1024
CHUNK_MINUTES      = 9
CHUNK_BITRATE      = "64k"
MERGE_GAP_MAX      = 0.45
SPLIT_GAP_MIN      = 1.20
MAX_SENT_CHARS     = 220
SENTENCE_END       = re.compile(r'[.!?…]["»]?\s*$')

# Fallback model chain — each has a separate rate-limit bucket
GROQ_MODELS = [
    "whisper-large-v3-turbo",   # fastest, try first
    "whisper-large-v3",         # fallback #1
    "distil-whisper-large-v3-en",  # fallback #2 (English only)
]


# ──────────────────────────────────────────────
# Bootstrap
# ──────────────────────────────────────────────

def ensure_dependencies():
    missing = []
    for pkg in REQUIRED_PACKAGES:
        mod = pkg.split(".")[0].replace("-", "_")
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        with console.status(f"[bold cyan]Installing {', '.join(missing)}…"):
            try:
                _pip(*missing)
                console.print(f"[green]✅ Installed:[/green] {', '.join(missing)}")
            except Exception as e:
                console.print(f"[yellow]⚠️  Could not install {missing}: {e}[/yellow]")
                console.print("[yellow]   Speaker diarization may be unavailable.[/yellow]")


def load_config():
    if not os.path.isfile(CONFIG_FILE):
        return
    with open(CONFIG_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and val and key not in os.environ:
                    os.environ[key] = val


def save_config(key, value):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    lines, found = [], False
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{key}="):
                lines[i] = f'{key}="{value}"\n'
                found = True
                break
    if not found:
        lines.append(f'{key}="{value}"\n')
    with open(CONFIG_FILE, "w") as f:
        f.writelines(lines)
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except (AttributeError, NotImplementedError):
        pass  # Windows: chmod not meaningful


def prompt_token(env_var, description, url):
    val = os.environ.get(env_var, "").strip()
    if val:
        return val
    console.print(f"\n[bold yellow]🔑 {env_var} not found[/bold yellow]")
    console.print(f"   {description}")
    console.print(f"   [cyan]Get it free at:[/cyan] [link={url}]{url}[/link]")
    val = console.input(f"   [bold]Paste {env_var}:[/bold] ").strip()
    if val:
        os.environ[env_var] = val
        save_config(env_var, val)
        console.print(f"   [green]✅ Saved to {CONFIG_FILE}[/green]")
    return val


# ──────────────────────────────────────────────
# Audio helpers
# ──────────────────────────────────────────────

def get_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path],
        capture_output=True, text=True, check=True)
    return float(json.loads(r.stdout)["format"]["duration"])


def convert_to_mono_mp3(src, dst):
    subprocess.run(
        ["ffmpeg", "-y", "-i", src, "-ac", "1", "-ab", CHUNK_BITRATE, "-map_metadata", "-1", dst],
        capture_output=True, check=True)


def split_audio(path, chunk_secs, tmpdir):
    pattern = os.path.join(tmpdir, "chunk_%03d.mp3")
    subprocess.run(
        ["ffmpeg", "-y", "-i", path, "-f", "segment", "-segment_time", str(chunk_secs),
         "-ac", "1", "-ab", CHUNK_BITRATE, "-reset_timestamps", "1", "-map_metadata", "-1", pattern],
        capture_output=True, check=True)
    return sorted(os.path.join(tmpdir, f)
                  for f in os.listdir(tmpdir) if f.startswith("chunk_") and f.endswith(".mp3"))


# ──────────────────────────────────────────────
# Groq transcription with model fallback
# ──────────────────────────────────────────────

def _groq_post(filepath, language, api_key, model):
    import requests
    filename = os.path.basename(filepath)
    with open(filepath, "rb") as f:
        return requests.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (filename, f, "audio/mpeg")},
            data={"model": model, "language": language,
                  "response_format": "verbose_json",
                  "timestamp_granularities[]": "word"},
            timeout=300,
        )


def transcribe_chunk_raw(filepath, language, api_key):
    """Try each model in GROQ_MODELS. On 429 wait then try next model."""
    models_left = list(GROQ_MODELS)

    while models_left:
        model = models_left[0]
        resp  = _groq_post(filepath, language, api_key, model)

        if resp.ok:
            return resp.json(), model

        if resp.status_code == 429:
            body = resp.json().get("error", {}).get("message", "")
            m    = re.search(r"try again in (?:(\d+)m)?(\d+)s", body)
            wait = (int(m.group(1) or 0) * 60 + int(m.group(2) or 0) + 3) if m \
                   else int(resp.headers.get("retry-after", 90))

            models_left.pop(0)
            if models_left:
                # Try next model immediately before waiting
                next_model = models_left[0]
                console.print(
                    f"   [yellow]⚡ Rate limit on [bold]{model}[/bold] — "
                    f"switching to [bold]{next_model}[/bold][/yellow]")
                continue

            # All models exhausted — wait on last 429
            console.print(
                f"   [yellow]⏳ All models rate-limited. Waiting [bold]{wait}s[/bold] "
                f"then retrying [bold]{model}[/bold]…[/yellow]")
            _rich_countdown(wait)
            resp = _groq_post(filepath, language, api_key, model)
            if resp.ok:
                return resp.json(), model

        console.print(f"   [red]✗ HTTP {resp.status_code}: {resp.text}[/red]")
        resp.raise_for_status()

    raise RuntimeError("All Groq models exhausted.")


def _rich_countdown(seconds):
    with Progress(
        SpinnerColumn(),
        TextColumn("[cyan]Waiting for rate limit reset…"),
        BarColumn(bar_width=30),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("", total=seconds)
        for _ in range(seconds):
            time.sleep(1)
            progress.advance(task)
    console.print("   [green]🔄 Resuming…[/green]")


# ──────────────────────────────────────────────
# Smart sentence splitting
# ──────────────────────────────────────────────

def build_sentences(words, segments, time_offset=0.0):
    units = []
    if words:
        for w in words:
            units.append({"start": w["start"] + time_offset,
                          "end":   w["end"]   + time_offset,
                          "text":  w["word"]})
    else:
        for s in segments:
            units.append({"start": s["start"] + time_offset,
                          "end":   s["end"]   + time_offset,
                          "text":  s["text"].strip()})
    if not units:
        return []

    sentences, cur_start = [], units[0]["start"]
    cur_end, cur_words   = units[0]["end"], [units[0]["text"]]

    def flush(s, e, wds):
        text = _clean(" ".join(wds))
        if text:
            sentences.append({"start": s, "end": e, "text": text})

    for prev, cur in zip(units, units[1:]):
        gap           = cur["start"] - prev["end"]
        so_far        = " ".join(cur_words)
        ends_sentence = bool(SENTENCE_END.search(so_far))
        should_split  = (ends_sentence and gap >= MERGE_GAP_MAX) \
                        or gap >= SPLIT_GAP_MIN \
                        or len(so_far) >= MAX_SENT_CHARS
        if should_split:
            flush(cur_start, cur_end, cur_words)
            cur_start, cur_end, cur_words = cur["start"], cur["end"], [cur["text"]]
        else:
            cur_end = cur["end"]
            cur_words.append(cur["text"])

    flush(cur_start, cur_end, cur_words)
    return sentences


def _clean(text):
    text = re.sub(r'\s+', ' ', text).strip()
    return text[0].upper() + text[1:] if text else text


# ──────────────────────────────────────────────
# Speaker diarization
# ──────────────────────────────────────────────

def try_diarize(audio_path, num_speakers=None):
    try:
        from pyannote.audio import Pipeline
        import torch, torchaudio, warnings
    except ImportError:
        console.print("[yellow]⚠️  pyannote.audio not installed — skipping diarization.[/yellow]")
        console.print("   Run: [cyan]pip install pyannote.audio torch torchaudio[/cyan]")
        return None

    hf_token = prompt_token(
        "HF_TOKEN",
        "Required for speaker diarization (free).\n"
        "   Accept model terms: huggingface.co/pyannote/speaker-diarization-3.1",
        "https://huggingface.co/settings/tokens"
    )
    if not hf_token:
        console.print("[yellow]⚠️  HF_TOKEN not provided — skipping diarization.[/yellow]")
        return None

    if torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"
    console.print(f"[dim]   Device: [bold]{device.upper()}[/bold][/dim]")

    try:
        with console.status("[bold cyan]🎙️  Loading diarization model…[/bold cyan]", spinner="dots"):
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1", token=hf_token
            ).to(torch.device(device))

        waveform, sample_rate = torchaudio.load(audio_path)
        audio_input = {"waveform": waveform, "sample_rate": sample_rate}
        kwargs = {"num_speakers": num_speakers} if num_speakers else {}

        step_colors = {
            "segmentation": "cyan",
            "embeddings": "magenta",
            "discrete diarization": "yellow",
        }
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold]{task.description}"),
            BarColumn(bar_width=None),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as prog:
            tasks = {}

            def hook(step_name, step_artifact, file=None, total=None, completed=None):
                if total is None:
                    return
                completed = completed or 0
                short = step_name.split("@")[0].strip()
                color = step_colors.get(short, "white")
                if short not in tasks:
                    tasks[short] = prog.add_task(
                        f"[{color}]🎙  {short}[/{color}]", total=total)
                prog.update(tasks[short], completed=completed, total=total)

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                diarization = pipeline(audio_input, hook=hook, **kwargs)

        # pyannote 4.x returns DiarizeOutput; 3.x returns Annotation directly
        ann = diarization.speaker_diarization if hasattr(diarization, 'speaker_diarization') else diarization
        segs = [(t.start, t.end, spk)
                for t, _, spk in ann.itertracks(yield_label=True)]
        n = len({s[2] for s in segs})
        console.print(f"[green]✅ Detected [bold]{n}[/bold] speaker(s)[/green]")
        return segs
    except Exception as e:
        console.print(f"[yellow]⚠️  Diarization failed: {e}[/yellow]")
        return None


def assign_speaker(start, end, diar_segs, speaker_map):
    if not diar_segs:
        return None
    votes = {}
    for d0, d1, spk in diar_segs:
        ov = max(0.0, min(end, d1) - max(start, d0))
        if ov > 0:
            votes[spk] = votes.get(spk, 0.0) + ov
    if not votes:
        return None
    raw = max(votes, key=votes.get)
    if raw not in speaker_map:
        speaker_map[raw] = f"Speaker {len(speaker_map) + 1}"
    return speaker_map[raw]


# ──────────────────────────────────────────────
# Formatting
# ──────────────────────────────────────────────

def fmt_ts(s):
    s = int(s); h, r = divmod(s, 3600); m, sec = divmod(r, 60)
    return f"[{h:02d}:{m:02d}:{sec:02d}]" if h else f"[{m:02d}:{sec:02d}]"


def format_output(sentences, diar_segs):
    speaker_map, lines, prev_spk = {}, [], None
    for sent in sentences:
        spk = assign_speaker(sent["start"], sent["end"], diar_segs, speaker_map)
        if spk and spk != prev_spk:
            if lines:
                lines.append("")
            lines.append(f"── {spk} " + "─" * 40)
            prev_spk = spk
        lines.append(f"{fmt_ts(sent['start'])}  {sent['text']}")
    return "\n".join(lines)


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

BANNER = """[bold cyan]
  ████████╗██████╗  █████╗ ███╗  ██╗███████╗ ██████╗██████╗ ██╗██████╗ ███████╗  ██████╗ ██╗
     ██║   ██╔══██╗██╔══██╗████╗ ██║██╔════╝██╔════╝██╔══██╗██║██╔══██╗██╔════╝ ██╔══██╗██║
     ██║   ██████╔╝███████║██╔██╗██║███████╗██║     ██████╔╝██║██████╔╝█████╗   ███████║██║
     ██║   ██╔══██╗██╔══██║██║╚████║╚════██║██║     ██╔══██╗██║██╔══██╗██╔══╝   ██╔══██║██║
     ██║   ██║  ██║██║  ██║██║ ╚███║███████║╚██████╗██║  ██║██║██████╔╝███████╗ ██║  ██║██║
     ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚══╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝╚═════╝╚══════╝ ╚═╝  ╚═╝╚═╝
[/bold cyan]
[dim]  Groq Whisper · pyannote Speaker Diarization · Smart Sentence Splitting[/dim]"""


def main():
    parser = argparse.ArgumentParser(description="transcribe-ai")
    parser.add_argument("file")
    parser.add_argument("language")
    parser.add_argument("--output",    "-o")
    parser.add_argument("--no-diarize", action="store_true")
    parser.add_argument("--speakers",  "-s", type=int, default=None)
    args = parser.parse_args()

    console.print(BANNER)

    load_config()
    ensure_dependencies()

    import requests as _req  # noqa: F401 (ensure installed)

    api_key = prompt_token("GROQ_API_KEY", "Required for transcription.", "https://console.groq.com")
    if not api_key:
        console.print("[red bold]❌ GROQ_API_KEY required. Aborting.[/red bold]"); sys.exit(1)
    if not os.path.isfile(args.file):
        console.print(f"[red]❌ File not found: {args.file}[/red]"); sys.exit(1)

    output_path = args.output or (os.path.splitext(args.file)[0] + "_transcribed.txt")
    file_mb     = os.path.getsize(args.file) / 1024 / 1024

    # ── Header panel ──────────────────────────────────
    info = Table.grid(padding=(0, 2))
    info.add_column(style="bold cyan", no_wrap=True)
    info.add_column()
    info.add_row("File",     f"{args.file}  [dim]({file_mb:.1f} MB)[/dim]")
    info.add_row("Language", args.language)
    info.add_row("Output",   output_path)
    info.add_row("Speakers", "auto-detect" if not args.speakers else str(args.speakers))
    info.add_row("Diarize",  "[red]disabled[/red]" if args.no_diarize else "[green]enabled[/green]")
    console.print(Panel(info, title="[bold]Job[/bold]", border_style="cyan"))

    tmpdir = tempfile.mkdtemp(prefix="groq_transcribe_")
    try:
        # ── Prepare ──────────────────────────────────
        with console.status("[cyan]Preparing audio (mono 64kbps)…[/cyan]"):
            prepared = os.path.join(tmpdir, "prepared.mp3")
            convert_to_mono_mp3(args.file, prepared)
            prep_mb = os.path.getsize(prepared) / 1024 / 1024
        console.print(f"[green]✅ Prepared:[/green] {prep_mb:.1f} MB  [dim](was {file_mb:.1f} MB)[/dim]")

        if os.path.getsize(prepared) <= MAX_BYTES:
            chunks = [prepared]
        else:
            dur     = get_duration(prepared)
            n_ch    = math.ceil(os.path.getsize(prepared) / MAX_BYTES)
            ch_secs = min(math.ceil(dur / n_ch), CHUNK_MINUTES * 60)
            with console.status(f"[cyan]Splitting into {n_ch} chunks of ~{ch_secs//60}m…[/cyan]"):
                chunks = split_audio(prepared, ch_secs, tmpdir)
            console.print(f"[green]✅ Split into {len(chunks)} chunks[/green]")

        # ── Transcribe ────────────────────────────────
        all_sentences, time_offset = [], 0.0
        used_models = set()

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(bar_width=None),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Transcribing…", total=len(chunks))
            for i, chunk in enumerate(chunks, 1):
                chunk_mb = os.path.getsize(chunk) / 1024 / 1024
                progress.update(task, description=f"Chunk {i}/{len(chunks)}  ({chunk_mb:.1f} MB)")
                raw, model_used = transcribe_chunk_raw(chunk, args.language, api_key)
                used_models.add(model_used)
                words    = raw.get("words", [])
                segments = raw.get("segments", [])
                sents    = build_sentences(words, segments, time_offset)
                all_sentences.extend(sents)
                time_offset += get_duration(chunk)
                progress.advance(task)

        console.print(
            f"[green]✅ Transcribed:[/green] {len(all_sentences)} sentences  "
            f"[dim](model: {', '.join(used_models)})[/dim]")

        # ── Diarize ───────────────────────────────────
        diar_segs = None
        if not args.no_diarize:
            diar_segs = try_diarize(prepared, args.speakers)

        # ── Write output ──────────────────────────────
        output = format_output(all_sentences, diar_segs)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output); f.write("\n")

        # ── Summary panel ─────────────────────────────
        total_chars = sum(len(s["text"]) for s in all_sentences)
        dur_min     = time_offset / 60

        summary = Table.grid(padding=(0, 2))
        summary.add_column(style="bold green", no_wrap=True)
        summary.add_column()
        summary.add_row("Output",    output_path)
        summary.add_row("Duration",  f"{dur_min:.1f} min")
        summary.add_row("Sentences", str(len(all_sentences)))
        summary.add_row("Characters",str(total_chars))
        if diar_segs:
            n_spk = len({s[2] for s in diar_segs})
            summary.add_row("Speakers",  str(n_spk))
        summary.add_row("Model(s)",  ", ".join(used_models))
        console.print(Panel(summary, title="[bold green]✅ Done[/bold green]", border_style="green"))

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
