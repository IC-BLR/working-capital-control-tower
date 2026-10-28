#!/usr/bin/env python3
"""Build a polished enterprise demo: full screens, title/end cards, captions, VO."""
import asyncio
import ssl
import shutil
import subprocess
from pathlib import Path

import edge_tts
from edge_tts import communicate as comm
from PIL import Image, ImageDraw, ImageFont

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
comm._SSL_CTX = ctx

DEMO = Path(__file__).resolve().parent
AUDIO = DEMO / "audio"
FRAMES = DEMO / "frames"
CLIPS = DEMO / "clips"
CARDS = DEMO / "cards"
W, H = 1920, 1080
VOICE = "en-US-JennyNeural"
RATE = "+12%"
PITCH = "-1Hz"

CAPTIONS = {
    "01": "Working Capital Intelligence  ·  Receivables + Payables",
    "02": "Cash Calendar  ·  Net Working Capital Exposure",
    "03": "Receivables portfolio  ·  Outstanding due, overdue, aging",
    "04": "Customer ranking  ·  Highest receivable due first",
    "05": "Invoice level  ·  Due amount, date, and overdue days",
    "06": "Payables portfolio  ·  Vendor obligations and exposure",
    "07": "Payable invoice  ·  Payment-ready vs policy blocked",
    "08": "CFO AI Assistant  ·  Portfolio, partner, and invoice Q&A",
    "09": "One loop  ·  Cash in, cash out, timing, risk, decisions",
}


def font(size: int, bold: bool = False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/SFNS.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def make_cards():
    CARDS.mkdir(exist_ok=True)

    # Title
    img = Image.new("RGB", (W, H), (15, 23, 42))
    draw = ImageDraw.Draw(img)
    # subtle gradient band
    for y in range(H):
        t = y / H
        r = int(15 + (6 - 15) * t)
        g = int(23 + (78 - 23) * t)
        b = int(42 + (99 - 42) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    draw.rectangle([0, 420, W, 422], fill=(56, 189, 248))
    draw.text((W // 2, 340), "WORKING CAPITAL CONTROL TOWER", font=font(28, True), fill=(148, 163, 184), anchor="mm")
    draw.text((W // 2, 430), "Working Capital Intelligence", font=font(64, True), fill=(248, 250, 252), anchor="mm")
    draw.text(
        (W // 2, 520),
        "Receivables  ·  Payables  ·  Aging  ·  Risk  ·  AI Decisions",
        font=font(30),
        fill=(186, 230, 253),
        anchor="mm",
    )
    img.save(CARDS / "title.png")

    # End
    img = Image.new("RGB", (W, H), (15, 23, 42))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        draw.line([(0, y), (W, y)], fill=(int(15 + 10 * t), int(23 + 40 * t), int(42 + 50 * t)))
    draw.rectangle([0, 470, W, 472], fill=(16, 185, 129))
    draw.text((W // 2, 390), "Cash in  ·  Cash out  ·  Timing  ·  Risk", font=font(36, True), fill=(167, 243, 208), anchor="mm")
    draw.text((W // 2, 480), "Working Capital Control Tower", font=font(52, True), fill=(248, 250, 252), anchor="mm")
    draw.text((W // 2, 560), "Net Working Capital Exposure = Total Receivables − Total Payables", font=font(26), fill=(203, 213, 225), anchor="mm")
    img.save(CARDS / "end.png")
    print("cards ready")


def captioned_frame(src: Path, caption: str) -> Path:
    """Composite a lower-third caption onto a full-frame PNG (no ffmpeg drawtext)."""
    img = Image.open(src).convert("RGBA")
    if img.size != (W, H):
        img = img.resize((W, H), Image.Resampling.LANCZOS)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    bar_h = 108
    draw.rectangle([0, H - bar_h, W, H], fill=(15, 23, 42, 170))
    draw.rectangle([0, H - bar_h, 8, H], fill=(56, 189, 248, 255))
    draw.text((48, H - 68), caption, font=font(32, True), fill=(248, 250, 252, 255))
    out = CLIPS / f"cap_{src.stem}.png"
    Image.alpha_composite(img, overlay).convert("RGB").save(out, quality=95)
    return out


def burn_caption(src: Path, dest: Path, caption: str, duration: float):
    """Full-frame clip with lower-third caption burned into the still."""
    capped = captioned_frame(src, caption)
    vf = (
        f"format=yuv420p,"
        f"fade=t=in:st=0:d=0.25,"
        f"fade=t=out:st={max(0.3, duration - 0.35):.3f}:d=0.35"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-loop",
            "1",
            "-framerate",
            "30",
            "-i",
            str(capped),
            "-t",
            f"{duration:.3f}",
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-tune",
            "stillimage",
            "-pix_fmt",
            "yuv420p",
            str(dest),
        ],
        check=True,
    )


def still_clip(src: Path, dest: Path, duration: float, fade: bool = True):
    vf = "format=yuv420p"
    if fade:
        vf += f",fade=t=in:st=0:d=0.3,fade=t=out:st={max(0.2, duration - 0.35):.3f}:d=0.35"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-loop",
            "1",
            "-framerate",
            "30",
            "-i",
            str(src),
            "-t",
            f"{duration:.3f}",
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-tune",
            "stillimage",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(dest),
        ],
        check=True,
    )


def mux(video: Path, audio: Path, dest: Path, duration: float):
    # Normalize VO to stereo 48k so concat matches title/end cards
    af = (
        f"aformat=sample_rates=48000:channel_layouts=stereo,"
        f"afade=t=in:st=0:d=0.1,afade=t=out:st={max(0, duration - 0.15):.3f}:d=0.15"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(video),
            "-i",
            str(audio),
            "-af",
            af,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "30",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-b:a",
            "192k",
            "-shortest",
            "-t",
            f"{duration:.3f}",
            str(dest),
        ],
        check=True,
    )


def silent_pad(video: Path, dest: Path, duration: float):
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(video),
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "30",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-b:a",
            "192k",
            "-shortest",
            "-t",
            f"{duration:.3f}",
            str(dest),
        ],
        check=True,
    )


def main():
    make_cards()
    AUDIO.mkdir(exist_ok=True)
    if CLIPS.exists():
        shutil.rmtree(CLIPS)
    CLIPS.mkdir()

    scenes = []
    for line in (DEMO / "script.txt").read_text().strip().splitlines():
        label, frame, text = line.split("|", 2)
        num = label.split()[1]
        assert (FRAMES / frame).exists(), frame
        scenes.append((num, frame, text.strip()))

    async def synth():
        out = []
        for num, frame, text in scenes:
            mp3 = AUDIO / f"scene_{num}.mp3"
            await edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH).save(str(mp3))
            wav = AUDIO / f"scene_{num}.wav"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), str(wav)], check=True)
            dur = float(
                subprocess.check_output(
                    [
                        "ffprobe",
                        "-v",
                        "error",
                        "-show_entries",
                        "format=duration",
                        "-of",
                        "default=nk=1:nw=1",
                        str(wav),
                    ],
                    text=True,
                ).strip()
            )
            print(f"audio {num}: {dur:.2f}s")
            out.append((num, frame, dur))
        return out

    built = asyncio.run(synth())
    vo_total = sum(d for _, _, d in built)
    title_d, end_d = 2.4, 2.6
    # Keep final under ~90s
    budget = 89.0 - title_d - end_d
    speed = 1.0 if vo_total <= budget else min(1.18, vo_total / budget)
    print(f"VO={vo_total:.2f}s speed={speed:.3f}")

    concat = []

    # Title
    title_v = CLIPS / "title_v.mp4"
    title_a = CLIPS / "title.mp4"
    still_clip(CARDS / "title.png", title_v, title_d)
    silent_pad(title_v, title_a, title_d)
    concat.append(title_a)

    for num, frame, dur in built:
        clip_dur = dur / speed
        v_only = CLIPS / f"v_{num}.mp4"
        final = CLIPS / f"clip_{num}.mp4"
        wav = AUDIO / f"scene_{num}.wav"
        # Optional speed-up of audio
        sped = AUDIO / f"scene_{num}_sped.wav"
        if abs(speed - 1) > 1e-3:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-loglevel",
                    "error",
                    "-i",
                    str(wav),
                    "-filter:a",
                    f"atempo={speed:.4f}",
                    str(sped),
                ],
                check=True,
            )
            wav_use = sped
        else:
            wav_use = wav

        burn_caption(FRAMES / frame, v_only, CAPTIONS[num], clip_dur)
        mux(v_only, wav_use, final, clip_dur)
        concat.append(final)
        print(f"clip {num}: {clip_dur:.2f}s")

    # End
    end_v = CLIPS / "end_v.mp4"
    end_a = CLIPS / "end.mp4"
    still_clip(CARDS / "end.png", end_v, end_d)
    silent_pad(end_v, end_a, end_d)
    concat.append(end_a)

    list_path = DEMO / "concat.txt"
    list_path.write_text("\n".join(f"file '{p.as_posix()}'" for p in concat) + "\n")
    out = DEMO / "Working_Capital_Control_Tower_Demo.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(out),
        ],
        check=True,
    )
    fd = float(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nk=1:nw=1",
                str(out),
            ],
            text=True,
        ).strip()
    )
    wh = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0",
            str(out),
        ],
        text=True,
    ).strip()
    print(f"FINAL duration={fd:.2f}s {wh} size={out.stat().st_size}")
    if fd > 96:
        raise SystemExit(f"Too long: {fd:.1f}s")


if __name__ == "__main__":
    main()
