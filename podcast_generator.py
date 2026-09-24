"""
VELOCITY GERMAN PODCAST GENERATOR
15-min bilingual German/English podcast at A2 level
2 hosts: Maria & Lukas
"""
import os, sys, json, asyncio, subprocess, random, requests, re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont, ImageFilter

load_dotenv()

POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL") or "openai"

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
FONTS_DIR = BASE_DIR / "fonts"

HOST1_VOICE = "de-DE-KatjaNeural"
HOST2_VOICE = "de-DE-KillianNeural"

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 30

TOPICS = [
    "Reisen in ein neues Land - Traveling to a new country",
    "Traditionelles Essen - Traditional food",
    "Tagesablauf - Daily routine",
    "Feiertage und Feste - Holidays and celebrations",
    "Wetter und Jahreszeiten - Weather and seasons",
    "Familie und Freunde - Family and friends",
    "Musik und Filme - Music and movies",
    "Sport und Fitness - Sports and exercise",
    "Die ideale Stadt - The ideal city",
    "Sprachen lernen - Learning languages",
    "Das Wochenende - The weekend",
    "Einkaufen und Kleidung - Shopping and clothes",
    "Öffentliche Verkehrsmittel - Public transport",
    "Im Restaurant - At the restaurant",
    "Gesundheit und Wohlbefinden - Health and wellness",
]

YELLOW = (247, 202, 0)
DARK_BG = (11, 14, 27)
WHITE = (255, 255, 255)
LIGHT_GRAY = (170, 180, 205)
DARK_LINE = (50, 55, 75)

def load_font(size, bold=False, italic=False):
    fonts_to_try = []
    if italic and bold:
        fonts_to_try.extend([
            "C:/Windows/Fonts/segoeuiz.ttf", "C:/Windows/Fonts/arialbi.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-BoldItalic.ttf",
            str(FONTS_DIR / "DejaVuSans-BoldOblique.ttf"),
        ])
    elif italic:
        fonts_to_try.extend([
            "C:/Windows/Fonts/segoeuii.ttf", "C:/Windows/Fonts/ariali.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf",
            str(FONTS_DIR / "DejaVuSans-Oblique.ttf"),
        ])
    elif bold:
        fonts_to_try.extend([
            "C:/Windows/Fonts/Inter-Bold-slnt=0.ttf", "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
            str(FONTS_DIR / "DejaVuSans-Bold.ttf"),
        ])
    else:
        fonts_to_try.extend([
            "C:/Windows/Fonts/Inter-Regular-slnt=0.ttf", "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            str(FONTS_DIR / "DejaVuSans.ttf"),
        ])

    for fp in fonts_to_try:
        if Path(fp).exists():
            try: return ImageFont.truetype(fp, size)
            except: continue
    return ImageFont.load_default()

def clean_text(text):
    text = re.sub(r'[\r\n]+', ' ', text)
    text = re.sub(r'\b(mm+|um+|uh+|ah+|äh+)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def auto_highlight_german(text):
    if '**' in text:
        return text
    stopwords = {'der', 'die', 'das', 'dem', 'den', 'des', 'ein', 'eine', 'einer', 'eines', 'einem', 'einen', 'und', 'oder', 'aber', 'ist', 'sind', 'war', 'ich', 'du', 'er', 'sie', 'es', 'wir', 'ihr', 'mit', 'in', 'im', 'auf', 'an', 'zu', 'von'}
    words = text.split()
    candidates = []
    for idx, w in enumerate(words):
        clean_w = re.sub(r'[^\wÄÖÜäöüß]', '', w, flags=re.UNICODE)
        if clean_w.lower() not in stopwords and len(clean_w) >= 3:
            candidates.append((len(clean_w), idx, w, clean_w))
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_idx = candidates[0][1]
        raw_w = words[best_idx]
        clean_w = candidates[0][3]
        highlighted = raw_w.replace(clean_w, f"**{clean_w}**")
        words[best_idx] = highlighted
        return " ".join(words)
    return text

def draw_microphone_icon(draw, center_x, center_y, radius=24):
    draw.ellipse([center_x - radius, center_y - radius, center_x + radius, center_y + radius],
                 outline=YELLOW, width=3)
    w, h = 10, 18
    draw.rounded_rectangle([center_x - w//2, center_y - 12, center_x + w//2, center_y - 12 + h],
                           radius=4, fill=YELLOW)
    draw.arc([center_x - 10, center_y - 4, center_x + 10, center_y + 12],
             start=0, end=180, fill=YELLOW, width=3)
    draw.line([(center_x, center_y + 12), (center_x, center_y + 17)], fill=YELLOW, width=3)
    draw.line([(center_x - 7, center_y + 17), (center_x + 7, center_y + 17)], fill=YELLOW, width=3)

def draw_person_icon(draw, center_x, center_y):
    draw.ellipse([center_x - 6, center_y - 12, center_x + 6, center_y], fill=YELLOW)
    draw.chord([center_x - 12, center_y + 2, center_x + 12, center_y + 20],
               start=180, end=360, fill=YELLOW)

def draw_german_flag(img, draw, center_x, center_y, radius=22):
    flag_img = Image.new('RGBA', (radius*2, radius*2), (0, 0, 0, 0))
    fdraw = ImageDraw.Draw(flag_img)
    # German flag: Black top (33%), Red middle (33%), Gold bottom (33%)
    h = radius * 2
    fdraw.rectangle([(0, 0), (radius*2, int(h * 0.33))], fill=(0, 0, 0, 255))
    fdraw.rectangle([(0, int(h * 0.33)), (radius*2, int(h * 0.66))], fill=(221, 0, 0, 255))
    fdraw.rectangle([(0, int(h * 0.66)), (radius*2, h)], fill=(255, 204, 0, 255))
    
    mask = Image.new('L', (radius*2, radius*2), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.ellipse([0, 0, radius*2, radius*2], fill=255)
    img.paste(flag_img, (center_x - radius, center_y - radius), mask)

def draw_headphones_icon(draw, center_x, center_y):
    draw.arc([center_x - 14, center_y - 14, center_x + 14, center_y + 6],
             start=180, end=360, fill=YELLOW, width=3)
    draw.rounded_rectangle([center_x - 16, center_y - 3, center_x - 10, center_y + 11], radius=2, fill=YELLOW)
    draw.rounded_rectangle([center_x + 10, center_y - 3, center_x + 16, center_y + 11], radius=2, fill=YELLOW)

def draw_rich_text_centered(draw, text, center_y, font, max_w=1550, line_height=90):
    text = auto_highlight_german(text)
    pattern = r'(\*\*.*?\*\*)'
    raw_parts = re.split(pattern, text)
    tokens = []
    for part in raw_parts:
        if part.startswith('**') and part.endswith('**'):
            tokens.append((part[2:-2], True))
        elif part:
            tokens.append((part, False))
            
    words_with_status = []
    for text_chunk, is_yellow in tokens:
        words = text_chunk.split(' ')
        for i, w in enumerate(words):
            if w:
                words_with_status.append((w, is_yellow))
            if i < len(words) - 1:
                words_with_status.append((' ', False))

    lines = []
    current_line = []
    current_line_width = 0

    for item in words_with_status:
        word, is_yellow = item
        w_bbox = draw.textbbox((0, 0), word, font=font)
        w_width = w_bbox[2] - w_bbox[0]

        if current_line_width + w_width <= max_w or not current_line:
            current_line.append((word, is_yellow, w_width))
            current_line_width += w_width
        else:
            if current_line and current_line[-1][0] == ' ':
                current_line_width -= current_line[-1][2]
                current_line.pop()
            lines.append((current_line, current_line_width))
            if word == ' ':
                current_line = []
                current_line_width = 0
            else:
                current_line = [(word, is_yellow, w_width)]
                current_line_width = w_width

    if current_line:
        if current_line[-1][0] == ' ':
            current_line_width -= current_line[-1][2]
            current_line.pop()
        lines.append((current_line, current_line_width))

    total_height = len(lines) * line_height
    start_y = center_y - total_height // 2

    for line_idx, (line_words, line_w) in enumerate(lines):
        start_x = (VIDEO_WIDTH - line_w) // 2
        curr_x = start_x
        curr_y = start_y + line_idx * line_height

        for word, is_yellow, w_w in line_words:
            color = YELLOW if is_yellow else WHITE
            draw.text((curr_x, curr_y), word, fill=color, font=font)
            curr_x += w_w

def draw_english_translation(draw, text, center_y, font, max_w=1350, line_height=52):
    words = text.split()
    lines = []
    current_line = []
    
    for w in words:
        test_line = ' '.join(current_line + [w])
        bb = draw.textbbox((0, 0), test_line, font=font)
        if bb[2] - bb[0] <= max_w:
            current_line.append(w)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [w]
    if current_line:
        lines.append(' '.join(current_line))
        
    total_h = len(lines) * line_height
    start_y = center_y - total_h // 2
    
    for idx, line in enumerate(lines):
        draw.text((VIDEO_WIDTH // 2, start_y + idx * line_height + line_height // 2),
                  line, fill=LIGHT_GRAY, font=font, anchor="mm")

def create_frame(turn, output_path, frame_num=0):
    img = Image.new('RGB', (VIDEO_WIDTH, VIDEO_HEIGHT), DARK_BG)
    draw = ImageDraw.Draw(img)

    glow = Image.new('RGBA', (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse([(-200, VIDEO_HEIGHT-600), (600, VIDEO_HEIGHT+200)], fill=(30, 20, 60, 40))
    gdraw.ellipse([(VIDEO_WIDTH-500, -200), (VIDEO_WIDTH+300, 600)], fill=(30, 20, 60, 40))
    img.paste(glow, (0, 0), glow)

    f_title_white = load_font(36, bold=True)
    f_title_sub = load_font(18, bold=False)
    f_title_sub_muted = load_font(15, bold=False)
    f_ep = load_font(22, bold=True)
    f_speaker = load_font(26, bold=True)
    f_hablando = load_font(24, bold=False)
    f_german = load_font(64, bold=True)
    f_english = load_font(42, bold=False, italic=True)
    f_footer = load_font(22, bold=False)

    # === TOP HEADER ===
    header_y = 68
    draw_microphone_icon(draw, center_x=70, center_y=header_y, radius=24)

    draw.text((110, header_y), "VELOCITY", fill=WHITE, font=f_title_white, anchor="lm")
    v_bbox = draw.textbbox((110, header_y), "VELOCITY", font=f_title_white, anchor="lm")
    
    draw.text((v_bbox[2] + 8, header_y), "GERMAN", fill=YELLOW, font=f_title_white, anchor="lm")
    s_bbox = draw.textbbox((v_bbox[2] + 8, header_y), "GERMAN", font=f_title_white, anchor="lm")

    draw.text((s_bbox[2] + 8, header_y), "PODCAST", fill=WHITE, font=f_title_white, anchor="lm")
    p_bbox = draw.textbbox((s_bbox[2] + 8, header_y), "PODCAST", font=f_title_white, anchor="lm")

    draw.line([(p_bbox[2] + 20, 48), (p_bbox[2] + 20, 88)], fill=DARK_LINE, width=2)

    sub_x = p_bbox[2] + 35
    draw.text((sub_x, header_y - 12), "German Podcast", fill=WHITE, font=f_title_sub, anchor="lm")
    draw.text((sub_x, header_y + 12), "Learn Through Conversations", fill=LIGHT_GRAY, font=f_title_sub_muted, anchor="lm")

    ep_num = (frame_num // 150) + 1 if isinstance(frame_num, int) else 1
    ep_str = f"EP {ep_num:02d}"
    draw.rounded_rectangle([(1640, 46), (1750, 90)], radius=8, fill=YELLOW)
    draw.text((1695, header_y), ep_str, fill=DARK_BG, font=f_ep, anchor="mm")

    draw_german_flag(img, draw, center_x=1810, center_y=header_y, radius=22)

    draw.line([(0, 130), (VIDEO_WIDTH, 130)], fill=YELLOW, width=2)

    # === SPEAKER STATUS SECTION ===
    is_host1 = turn.get("speaker") == "Host1"
    speaker_name = "MARIA" if is_host1 else "LUKAS"
    pill_x, pill_y = 120, 210
    pill_w, pill_h = 220, 52

    draw.rounded_rectangle([(pill_x, pill_y), (pill_x + pill_w, pill_y + pill_h)],
                           radius=26, outline=YELLOW, width=2)
    draw_person_icon(draw, center_x=pill_x + 36, center_y=pill_y + 26)
    draw.text((pill_x + 60, pill_y + 26), speaker_name, fill=YELLOW, font=f_speaker, anchor="lm")

    draw.text((pill_x + pill_w + 25, pill_y + 26), "spricht", fill=LIGHT_GRAY, font=f_hablando, anchor="lm")

    # === MAIN GERMAN TEXT ===

    # === MAIN TEXT (auto-size, HARD max 3 lines) ===
    german_text = turn.get("german", turn.get("spanish", ""))
    chosen_font = None
    chosen_lh = 90
    final_lines = []
    for test_size in [64, 56, 48, 40, 34, 28, 24, 20]:
        test_font = load_font(test_size, bold=True)
        test_lh = int(test_size * 1.4)
        text_words = german_text.split()
        tmp_lines = []
        cur = []
        for w in text_words:
            test = ' '.join(cur + [w])
            bb = draw.textbbox((0, 0), test, font=test_font)
            if bb[2] - bb[0] <= 1550 or not cur:
                cur.append(w)
            else:
                tmp_lines.append(' '.join(cur))
                cur = [w]
        if cur: tmp_lines.append(' '.join(cur))
        if len(tmp_lines) <= 3:
            chosen_font = test_font
            chosen_lh = test_lh
            final_lines = tmp_lines
            break
    if chosen_font is None:
        chosen_font = load_font(20, bold=True)
        chosen_lh = int(20 * 1.4)
        text_words = german_text.split()
        tmp_lines = []
        cur = []
        for w in text_words:
            test = ' '.join(cur + [w])
            bb = draw.textbbox((0, 0), test, font=chosen_font)
            if bb[2] - bb[0] <= 1550 or not cur:
                cur.append(w)
            else:
                tmp_lines.append(' '.join(cur))
                cur = [w]
        if cur: tmp_lines.append(' '.join(cur))
        if len(tmp_lines) > 3:
            tmp_lines = tmp_lines[:3]
            if german_text:
                tmp_lines[-1] = tmp_lines[-1].rstrip() + "..."
        final_lines = tmp_lines
        german_text = " ".join(final_lines)
    draw_rich_text_centered(draw, german_text, center_y=440, font=chosen_font, max_w=1550, line_height=chosen_lh)

    # === CENTER DIVIDER WITH DOT ===
    div_y = 615
    draw.line([(VIDEO_WIDTH//2 - 300, div_y), (VIDEO_WIDTH//2 + 300, div_y)], fill=YELLOW, width=2)
    draw.ellipse([(VIDEO_WIDTH//2 - 8, div_y - 8), (VIDEO_WIDTH//2 + 8, div_y + 8)], fill=YELLOW)

    # === ENGLISH TRANSLATION ===
    english_text = turn.get("english", "")
    draw_english_translation(draw, english_text, center_y=715, font=f_english, max_w=1350, line_height=52)

    # === BOTTOM FOOTER ===
    draw.line([(0, 975), (VIDEO_WIDTH, 975)], fill=YELLOW, width=2)

    footer_y = 1025
    draw_headphones_icon(draw, center_x=VIDEO_WIDTH//2 - 270, center_y=footer_y)
    draw.text((VIDEO_WIDTH//2 - 240, footer_y), "Learn German Naturally", fill=WHITE, font=f_footer, anchor="lm")
    
    fn_bbox = draw.textbbox((VIDEO_WIDTH//2 - 240, footer_y), "Learn German Naturally", font=f_footer, anchor="lm")
    draw.line([(fn_bbox[2] + 20, footer_y - 12), (fn_bbox[2] + 20, footer_y + 12)], fill=DARK_LINE, width=2)
    
    draw.text((fn_bbox[2] + 40, footer_y), "velocitygerman.com", fill=WHITE, font=f_footer, anchor="lm")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, quality=92)


def parse_turns_json(content, target_key="german"):
    """Robustly parse JSON array of turns from LLM output, handling unescaped control chars, code fences, and partial json."""
    clean = content.strip()
    if "```json" in clean:
        clean = clean.split("```json")[1].split("```")[0].strip()
    elif "```" in clean:
        clean = clean.split("```")[1].split("```")[0].strip()

    try:
        obj = json.loads(clean, strict=False)
        if isinstance(obj, list):
            return obj
    except Exception:
        pass

    fixed = re.sub(r'(?<!\\)\n', r'\\n', clean)
    try:
        obj = json.loads(fixed, strict=False)
        if isinstance(obj, list):
            return obj
    except Exception:
        pass

    recovered = []
    start = None
    depth = 0
    for ci, ch in enumerate(clean):
        if ch == '{':
            if depth == 0:
                start = ci
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start is not None:
                chunk = clean[start:ci + 1]
                try:
                    t = json.loads(chunk, strict=False)
                    if isinstance(t, dict):
                        recovered.append(t)
                except Exception:
                    try:
                        chunk_fixed = re.sub(r'(?<!\\)\n', r'\\n', chunk)
                        t = json.loads(chunk_fixed, strict=False)
                        if isinstance(t, dict):
                            recovered.append(t)
                    except Exception:
                        pass
                start = None
    if recovered:
        return recovered

    regex = re.compile(
        r'\{\s*"speaker"\s*:\s*"(?P<speaker>[^"]+)"\s*,\s*'
        r'(?:"(?:' + target_key + r'|text|content|spanish)"\s*:\s*"(?P<tgt>.*?)"\s*,\s*)?'
        r'(?:"english"\s*:\s*"(?P<en>.*?)"\s*)?'
        r'\}', re.DOTALL
    )
    for m in regex.finditer(clean):
        spk = m.group("speaker") or "Host1"
        tgt = m.group("tgt") or ""
        en = m.group("en") or ""
        if tgt:
            recovered.append({"speaker": spk, target_key: tgt, "english": en})

    return recovered

def _fetch_turns_batch(topic, topic_es, topic_en, start_turn, batch_size=10):
    """Fetch one small batch of turns with multi-model fallback and robust parsing."""
    current_host = "Host2" if start_turn % 2 == 0 else "Host1"
    next_host = "Host1" if current_host == "Host2" else "Host2"
    host_role = "Lukas" if current_host == "Host2" else "Maria"

    intro_instruction = ""
    if start_turn == 0:
        intro_instruction = ("IMPORTANT: This is the FIRST batch. Keep the introduction SHORT - just 2 lines total "
                             "(one from Lukas/Host2, one from Maria/Host1), then immediately dive into the topic. "
                             "No long welcome speeches.\n")
    elif start_turn < 4:
        intro_instruction = "Continue naturally into the topic conversation. No new introductions.\n"

    prompt = f"""You are writing a German/English learning podcast at A2 level.
Topic: {topic}

The dialogue so far is at turn {start_turn}. The current speaker is {host_role} ({current_host}).
Write the NEXT {batch_size} turns. Speakers STRICTLY alternate starting with {current_host}.

{intro_instruction}Each turn: 3-4 SHORT sentences (6-10 words each) with PERIODS for natural TTS pauses. 20-30 seconds spoken.
Simple present tense. A2 vocabulary. Natural German. NO filler sounds.
IMPORTANT: Highlight exactly 1 key A2 target vocabulary word in each turn's German text using double asterisks, for example: "Wir schauen in die **Zukunft**."
IMPORTANT: Format as a single compact JSON array without unescaped line breaks inside string values.

Return EXACTLY {batch_size} turns as a JSON array (no markdown):
[{{"speaker": "{current_host}", "german": "...", "english": "..."}},
 {{"speaker": "{next_host}", "german": "...", "english": "..."}}]"""

    candidate_models = [AI_MODEL, "openai", "mistral", "qwen"]
    models_to_try = []
    for mod in candidate_models:
        if mod and mod not in models_to_try:
            models_to_try.append(mod)

    for attempt, model_name in enumerate(models_to_try):
        try:
            resp = requests.post("https://gen.pollinations.ai/v1/chat/completions", json={
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "You write natural A2-level German podcast scripts with VERY clear punctuation. Every sentence must have at least 2 commas for natural TTS pauses. Maria and Lukas strictly alternate. Highlight 1 key target word per turn in double asterisks like **Wort**. No filler sounds. Output single compact JSON array without unescaped newlines inside strings."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.8
            }, headers={"Authorization": f"Bearer {POLLINATIONS_API_KEY}"} if POLLINATIONS_API_KEY else {}, timeout=45)
            if resp.status_code != 200:
                print(f"  Batch attempt {attempt+1} ({model_name}) returned HTTP {resp.status_code}", flush=True)
                continue
            content = resp.json()["choices"][0]["message"]["content"].strip()
            script = parse_turns_json(content, "german")
            valid = []
            for i, turn in enumerate(script):
                if not isinstance(turn, dict):
                    continue
                de = turn.get("german") or turn.get("spanish") or turn.get("text") or turn.get("content") or ""
                en = turn.get("english") or turn.get("translation") or ""
                if not de:
                    continue
                valid.append({
                    "speaker": current_host if i % 2 == 0 else next_host,
                    "german": clean_text(de),
                    "english": clean_text(en) if en else "Translation unavailable"
                })
            if len(valid) >= 4:
                return valid
            else:
                print(f"  Batch attempt {attempt+1} ({model_name}) parsed only {len(valid)} turns, trying next model...", flush=True)
        except Exception as e:
            print(f"  Batch attempt {attempt+1} ({model_name}) failed: {e}", flush=True)
            import time
            time.sleep(1)
    return None


def _generate_topic():
    """Have the AI invent a brand-new random topic (unlimited variety).
    Returns '<topic - English>' or None on failure (caller falls back to TOPICS)."""
    seed = random.randint(100000, 999999)
    candidate_models = [AI_MODEL, "openai", "mistral"]
    for m in candidate_models:
        if not m:
            continue
        try:
            resp = requests.post("https://gen.pollinations.ai/v1/chat/completions", json={
                "model": m,
                "messages": [
                    {"role": "system", "content": "You invent fresh, interesting, everyday topics for a German/English A2 learning podcast. Always pick something new and varied from all areas of daily life, as a SHORT noun phrase (2-5 words), NOT a full sentence."},
                    {"role": "user", "content": f"Create EXACTLY ONE brand-new topic (uniqueness seed {seed}) for a German/English A2 podcast. Return ONLY one line in this exact format: <topic in German> - <topic in English>. The first part must be a short noun phrase in German. No numbering, no bullets, no extra text."}
                ],
                "temperature": 1.1,
            }, headers={"Authorization": f"Bearer {POLLINATIONS_API_KEY}"} if POLLINATIONS_API_KEY else {}, timeout=45)
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"].strip().strip('"').strip()
                if content and " - " in content:
                    return content
        except Exception as e:
            print(f"  Topic gen ({m}) failed: {e}", flush=True)
    return None


def _fallback_script(topic_es, topic_en, target=150):
    """Generate 150 unique, educational, progressive dialogue turns in German covering diverse conversation phases."""
    phases = [
        # Phase 1: Greetings & Introduction
        [
            ("Host2", f"Hallo an alle, ich bin Lukas. Willkommen bei Velocity German! Heute sprechen wir über **{topic_es}**.",
                      f"Hello everyone, I'm Lukas. Welcome to Velocity German! Today we are talking about {topic_en}."),
            ("Host1", f"Hallo Lukas, und hallo an alle Hörer! Dieses Thema ist wirklich **spannend** für alle Deutschlerner.",
                      f"Hello Lukas, and hello to all listeners! This topic is truly exciting for all German learners."),
            ("Host2", f"Genau, Maria. Viele Menschen erleben **{topic_es}** jeden Tag, wissen aber nicht, wie man darüber spricht.",
                      f"Exactly, Maria. Many people experience {topic_en} every day, but don't know how to talk about it."),
            ("Host1", f"Das stimmt. Deshalb nutzen wir heute **einfache** Sätze und klare Wörter, damit jeder alles versteht.",
                      f"That's right. Therefore we use simple sentences and clear words today, so everyone understands everything."),
            ("Host2", f"Perfekt! Fangen wir mit der ersten Frage an: Was bedeutet **{topic_es}** für dich im Alltag?",
                      f"Perfect! Let's start with the first question: What does {topic_en} mean for you in daily life?"),
            ("Host1", f"Für mich ist es ein wichtiger Teil des **Tages**, der gute Laune bringt und den Geist belebt.",
                      f"For me it's an important part of the day that brings good mood and enlivens the mind."),
            ("Host2", f"Ich stimme dir vollkommen zu. Sich Zeit dafür zu nehmen, schenkt neue **Energie** und Gelassenheit.",
                      f"I completely agree with you. Taking time for it gives new energy and serenity."),
            ("Host1", f"Ja, und mit dem passenden Wortschatz kann man ganz leicht ein natürliches **Gespräch** führen.",
                      f"Yes, and with the right vocabulary one can easily have a natural conversation."),
            ("Host2", f"Hört heute aufmerksam zu, und sprecht die wichtigsten Schlüsselwörter laut und deutlich **nach**.",
                      f"Listen carefully today, and repeat the most important key words out loud and clearly."),
            ("Host1", f"Sehr gut, Lukas! Schauen wir uns jetzt die praktischen Seiten von **{topic_es}** genauer an.",
                      f"Very good, Lukas! Let's now look more closely at the practical sides of {topic_en}.")
        ],
        # Phase 2: Morning routine & habits
        [
            ("Host2", f"Maria, wann denkst du an einem ganz normalen Tag zuerst an **{topic_es}**?",
                      f"Maria, when on a normal day do you first think about {topic_en}?"),
            ("Host1", f"Meistens denke ich schon früh am Morgen daran, weil es mir hilft, mit **Ruhe** in den Tag zu starten.",
                      f"Mostly I think about it early in the morning, because it helps me start the day with calm."),
            ("Host2", f"Für mich ist der frühe Morgen ebenfalls ein besonderer Moment. Ich nehme mir gerne **Zeit**.",
                      f"For me early morning is also a special moment. I gladly take my time."),
            ("Host1", f"Hektik ist immer ein schlechter Begleiter. Eine gute morgendliche **Gewohnheit** verändert alles.",
                      f"Hurry is always a bad companion. A good morning habit changes everything."),
            ("Host2", f"Viele Menschen widmen sich **{topic_es}** dagegen lieber am späten Nachmittag oder nach der Arbeit.",
                      f"Many people prefer devoting themselves to {topic_en} in late afternoon or after work."),
            ("Host1", f"Das hängt ganz vom persönlichen Tagesablauf ab. Die Hauptsache ist eine gesunde **Balance**.",
                      f"That completely depends on personal daily routine. The main thing is a healthy balance."),
            ("Host2", f"Du hast absolut recht. Auf die eigenen Bedürfnisse zu achten, lässt einen viel **besser** leben.",
                      f"You are absolutely right. Paying attention to one's own needs makes one live much better."),
            ("Host1", f"Und für unsere Deutschlerner baut tägliches kurzes Üben ein starkes sprachliches **Gedächtnis** auf.",
                      f"And for our German learners, daily short practice builds a strong language memory."),
            ("Host2", f"Ganz genau. Zehn Minuten jeden Tag bringen viel mehr als zwei lange Stunden nur am **Sonntag**.",
                      f"Exactly right. Ten minutes every day brings much more than two long hours only on Sunday."),
            ("Host1", f"Sprechen wir als Nächstes darüber, wie **{topic_es}** im Stadtleben sichtbar wird.",
                      f"Next let's talk about how {topic_en} becomes visible in city life.")
        ],
        # Phase 3: In the city & culture
        [
            ("Host2", f"Wenn man durch eine deutsche Stadt spaziert, bemerkt man sofort die Rolle von **{topic_es}**.",
                      f"When walking through a German city, one immediately notices the role of {topic_en}."),
            ("Host1", f"Ja, in Cafés, Geschäften und in Fußgängerzonen unterhalten sich die Leute gerne mit großem **Interesse**.",
                      f"Yes, in cafes, shops and pedestrian zones people enjoy talking about it with great interest."),
            ("Host2", f"In Deutschland schätzt man solche gemeinsamen Momente sehr. Es ist ein Zeichen von **Freundschaft**.",
                      f"In Germany people appreciate such shared moments very much. It's a sign of friendship."),
            ("Host1", f"Gemütlichkeit und Verlässlichkeit sind zentrale Werte. Man fühlt sich in der Runde nie **allein**.",
                      f"Cozy comfort and reliability are central values. One never feels alone in the group."),
            ("Host2", f"Welche Wörter benutzen die Deutschen am häufigsten, wenn sie **{topic_es}** beschreiben?",
                      f"What words do Germans use most frequently when describing {topic_en}?"),
            ("Host1", f"Oft hört man Eigenschaftswörter wie 'hochwertig', 'angenehm' oder 'praktisch', um die **Qualität** zu loben.",
                      f"Often one hears adjectives like 'high-value', 'pleasant' or 'practical' to praise quality."),
            ("Host2", f"Das Wort 'Qualität' passt perfekt. Qualität und Gründlichkeit haben in Deutschland eine lange **Tradition**.",
                      f"The word 'quality' fits perfectly. Quality and thoroughness have a long tradition in Germany."),
            ("Host1", f"Auch wenn man etwas mehr investieren muss, lohnt sich diese sorgfältige **Entscheidung** immer.",
                      f"Even if one has to invest a bit more, this careful decision always pays off."),
            ("Host2", f"Ein wertvoller Tipp für Reisende in Deutschland: Fragt immer die Menschen aus der **Nachbarschaft**.",
                      f"A valuable tip for travelers in Germany: Always ask people from the neighborhood."),
            ("Host1", f"Einheimische kennen immer die besten und authentischsten Orte für **{topic_es}**.",
                      f"Locals always know the best and most authentic places for {topic_en}.")
        ],
        # Phase 4: Advice for learners & beginner challenges
        [
            ("Host2", f"Ein Hörer hat uns gefragt: Ist es schwer, alle Feinheiten rund um **{topic_es}** zu verstehen?",
                      f"A listener asked us: Is it hard to understand all the subtleties around {topic_en}?"),
            ("Host1", f"Am Anfang wirkt es vielleicht etwas komplex, aber mit etwas Geduld wird alles schnell sehr **klar**.",
                      f"At the beginning it might seem a bit complex, but with some patience everything quickly becomes very clear."),
            ("Host2", f"Was ist der typische Fehler, den Sprachanfänger bei diesem Thema oft **machen**?",
                      f"What is the typical mistake language beginners often make with this topic?"),
            ("Host1", f"Der häufigste Fehler ist die Angst vor kleinen Grammatikfehlern oder der Wunsch nach Perfektion am ersten **Tag**.",
                      f"The most common mistake is fear of small grammar errors or the desire for perfection on the first day."),
            ("Host2", f"Fehler zu machen ist völlig normal und notwendig! Aus jedem Fehler lernt man eine neue **Lektion**.",
                      f"Making mistakes is completely normal and necessary! From every mistake one learns a new lesson."),
            ("Host1", f"Ganz genau. Im echten Leben kommt es vor allem darauf an, verstanden zu werden und **Freude** zu zeigen.",
                      f"Exactly right. In real life what matters most is being understood and showing joy."),
            ("Host2", f"Die Menschen in Deutschland freuen sich immer sehr, wenn jemand versucht, ihre Sprache zu **sprechen**.",
                      f"People in Germany are always very happy when someone tries to speak their language."),
            ("Host1", f"Man bekommt fast immer ein freundliches Lächeln und ermutigende Worte, um weiter zu **üben**.",
                      f"One almost always gets a friendly smile and encouraging words to keep practicing."),
            ("Host2", f"Habt also keine Scheu, bei der nächsten Gelegenheit über **{topic_es}** zu sprechen!",
                      f"So have no fear to speak about {topic_en} on the next opportunity!"),
            ("Host1", f"Fasst Mut und wendet die Redewendungen an, die wir in dieser **Folge** gemeinsam lernen.",
                      f"Take courage and apply the idioms we learn together in this episode.")
        ],
        # Phase 5: Regional diversity in German-speaking countries
        [
            ("Host2", f"Maria, wie unterscheidet sich die Sicht auf **{topic_es}** in den verschiedenen Regionen?",
                      f"Maria, how does the view on {topic_en} differ in various regions?"),
            ("Host1", f"Zwischen Bayern, dem Norden, Österreich und der Schweiz gibt es feine Nuancen, aber die Wertschätzung ist überall **stark**.",
                      f"Between Bavaria, the north, Austria and Switzerland there are subtle nuances, but appreciation is everywhere strong."),
            ("Host2", f"Diese regionale Vielfalt macht den gesamten deutschsprachigen Raum so spannend und **lebendig**.",
                      f"This regional diversity makes the entire German-speaking area so exciting and vibrant."),
            ("Host1", f"Jede Region pflegt ihre eigenen Dialekte, Gebräuche und unverwechselbaren **Besonderheiten**.",
                      f"Each region nurtures its own dialects, customs and distinctive specialties."),
            ("Host2", f"Auch internationale Gäste lieben diese Mischung aus moderner Innovation und bodenständiger **Gemütlichkeit**.",
                      f"International guests also love this blend of modern innovation and down-to-earth cozy comfort."),
            ("Host1", f"Denn im Mittelpunkt stehen immer Verlässlichkeit, gute Freunde und der Zusammenhalt in der **Familie**.",
                      f"Because at the center always stand reliability, good friends and cohesion in the family."),
            ("Host2", f"Und **{topic_es}** passt wunderbar in diesen bewussten und achtsamen Lebensstil.",
                      f"And {topic_en} fits wonderfully into this conscious and mindful lifestyle."),
            ("Host1", f"Es ist nicht nur eine theoretische Idee, sondern ein handfester Moment des echten **Teilens**.",
                      f"It's not just a theoretical idea, but a tangible moment of genuine sharing."),
            ("Host2", f"Wenn man schöne Augenblicke teilt, verdoppelt sich die Freude und bleibt als schöne **Erinnerung**.",
                      f"When one shares beautiful moments, joy doubles and remains as a fond memory."),
            ("Host1", f"Genau so ist es, Lukas. Die schönsten Erinnerungen entstehen fast immer aus ganz **einfachen** Dingen.",
                      f"Exactly so, Lukas. The finest memories almost always arise from very simple things.")
        ],
        # Phase 6: Practical learning tips
        [
            ("Host2", f"Geben wir unseren Hörern nun drei praktische Lerntipps, um das Thema **{topic_es}** zu meistern.",
                      f"Let's now give our listeners three practical study tips to master the topic of {topic_en}."),
            ("Host1", f"Erster Tipp: Schreibt neue Wörter und Beispielsätze handschriftlich in ein kleines **Heft**.",
                      f"First tip: Write new words and example sentences by hand in a small notebook."),
            ("Host2", f"Sehr guter Tipp! Das Schreiben von Hand verankert Wortformen viel fester im menschlichen **Gehirn**.",
                      f"Very good tip! Writing by hand anchors word forms much more firmly in the human brain."),
            ("Host1", f"Zweiter Tipp: Hört deutsche Podcasts über Kopfhörer unterwegs in der Bahn oder beim **Spaziergang**.",
                      f"Second tip: Listen to German podcasts on headphones on the go on the train or while walking."),
            ("Host2", f"Dieses passive Zuhören gewöhnt das Ohr ganz natürlich an die Satzmelodie und den Klang der **Stimme**.",
                      f"This passive listening gets the ear naturally accustomed to sentence melody and the sound of the voice."),
            ("Host1", f"Und dritter Tipp: Lernt niemals einzelne Vokabeln ohne Zusammenhang, sondern immer ganze **Sätze**.",
                      f"And third tip: Never learn individual vocab words without context, but always full sentences."),
            ("Host2", f"Dann fällt einem in einer echten Unterhaltung die richtige Formulierung sofort ohne langes **Nachdenken** ein.",
                      f"Then in a real conversation the right phrasing comes immediately without long thinking."),
            ("Host1", f"Genau nach diesem bewährten Prinzip gestalten wir unsere Sprachlektionen auf dem Niveau **A2**.",
                      f"According to this exact proven principle we design our language lessons at the A2 level."),
            ("Host2", f"Viele Hörer berichten in den Kommentaren von spürbaren Fortschritten durch diese einfache **Methode**.",
                      f"Many listeners report in the comments noticeable progress through this simple method."),
            ("Host1", f"Das freut uns riesig und motiviert uns, jede Woche neue lehrreiche Inhalte zu **erstellen**.",
                      f"That pleases us enormously and motivates us to create new instructive content every week.")
        ],
        # Phase 7: Situational roleplay
        [
            ("Host2", f"Machen wir ein kurzes Rollenspiel: Stellen wir uns vor, wir stehen in einem Geschäft für **{topic_es}**.",
                      f"Let's do a short roleplay: Let's imagine we are standing in a store for {topic_en}."),
            ("Host1", f"Sehr gerne! 'Guten Tag, können Sie mir bitte sagen, was Sie mir hierfür **empfehlen**?'",
                      f"Very gladly! 'Good day, can you please tell me what you recommend for me here?'"),
            ("Host2", f"'Guten Tag! Für Einsteiger empfehle ich besonders diese solide und bewährte **Ausführung**.'",
                      f"'Good day! For beginners I especially recommend this solid and proven version.'"),
            ("Host1", f"'Vielen Dank! Und wie lange braucht man ungefähr, um damit sicher und gut im Alltag **umzugehen**?'",
                      f"'Thank you very much! And about how long does one need to handle it safely and well in daily life?'"),
            ("Host2", f"'Normalerweise reichen ein paar Tage regelmäßiger Übung völlig aus, wenn man mit Ruhe und **Geduld** herangeht.'",
                      f"'Normally a few days of regular practice are plenty if one approaches it with calm and patience.'"),
            ("Host1", f"'Das klingt wunderbar! Ich werde Ihren Vorschlag gerne direkt heute **ausprobieren**.'",
                      f"'That sounds wonderful! I will gladly try out your suggestion directly today.'"),
            ("Host2", f"Das war ein typischer, freundlicher Dialog, wie man ihn überall in Deutschland im Alltag **erlebt**.",
                      f"That was a typical friendly dialogue like one experiences everywhere in Germany in daily life."),
            ("Host1", f"Achtet auf höfliche Wendungen wie 'können Sie mir sagen' — sie öffnen jede Tür im **Gespräch**.",
                      f"Pay attention to polite phrases like 'can you tell me' — they open every door in conversation."),
            ("Host2", f"Freundlichkeit schafft sofort eine angenehme Atmosphäre für beide beteiligten **Personen**.",
                      f"Friendliness immediately creates a pleasant atmosphere for both involved persons."),
            ("Host1", f"Merkt euch diese praktischen Sätze gut für eure nächste Reise nach **Deutschland**.",
                      f"Remember these practical sentences well for your next trip to Germany.")
        ],
        # Phase 8: Personal insights & confidence
        [
            ("Host2", f"Maria, wie reagieren deine Freunde im privaten Kreis auf das Thema **{topic_es}**?",
                      f"Maria, how do your friends in private circles react to the topic of {topic_en}?"),
            ("Host1", f"Anfangs waren manche etwas skeptisch, aber nach ersten Erfahrungen haben sie den großen **Nutzen** erkannt.",
                      f"Initially some were somewhat skeptical, but after initial experiences they recognized the great benefit."),
            ("Host2", f"Eine gewisse Vorsicht am Anfang ist eine ganz normale und verständliche menschliche **Reaktion**.",
                      f"A certain caution at the start is a completely normal and understandable human reaction."),
            ("Host1", f"Sobald man aber den ersten Schritt wagt, weicht die Unsicherheit einem spürbaren Gefühl von **Selbstvertrauen**.",
                      f"As soon as one dares the first step, however, uncertainty yields to a noticeable feeling of self-confidence."),
            ("Host2", f"Sprachliches Selbstvertrauen wächst mit jedem Satz, den man mutig laut **ausspricht**.",
                      f"Language self-confidence grows with every sentence that one bravely pronounces out loud."),
            ("Host1", f"Selbst mit einem Grundwortschatz von wenigen Dutzend Wörtern kann man schon interessante Gedanken **ausdrücken**.",
                      f"Even with a basic vocabulary of a few dozen words one can already express interesting thoughts."),
            ("Host2", f"Das Wichtigste ist die Begeisterung und der echte Wunsch nach gegenseitigem **Verständnis**.",
                      f"The most important thing is enthusiasm and the genuine desire for mutual understanding."),
            ("Host1", f"Unsere weltweiten Hörer beweisen jeden Tag, dass Deutsch für jeden engagierten Menschen **machbar** ist.",
                      f"Our worldwide listeners prove every day that German is doable for every committed person."),
            ("Host2", f"Jede gehörte Lektion ist ein weiterer Meilenstein auf eurem persönlichen Bildungsweg zum **Erfolg**.",
                      f"Every listened lesson is another milestone on your personal educational path to success."),
            ("Host1", f"Und wir freuen uns sehr, euch Woche für Woche mit nützlichen Tipps dabei zu **begleiten**.",
                      f"And we are very glad to accompany you week after week with useful tips.")
        ],
        # Phase 9: Vocabulary recap
        [
            ("Host2", f"Fassen wir kurz die fünf wichtigsten Begriffe zusammen, die wir heute rund um **{topic_es}** gelernt haben.",
                      f"Let's briefly summarize the five most important concepts we learned today around {topic_en}."),
            ("Host1", f"Sehr gerne! Das erste Schlüsselwort lautet **Gewohnheit**, also eine regelmäßige nützliche Handlung.",
                      f"Very gladly! The first key word is 'habit', that is, a regular useful action."),
            ("Host2", f"Das zweite zentrale Wort ist **Qualität**, die gute und langlebige Dinge von minderwertigen unterscheidet.",
                      f"The second central word is 'quality', which distinguishes good and long-lasting things from inferior ones."),
            ("Host1", f"Das dritte Wort ist **Gemütlichkeit**, das wunderbare Gefühl von Geborgenheit und herzlicher Entspannung.",
                      f"The third word is 'cozy comfort', the wonderful feeling of security and cordial relaxation."),
            ("Host2", f"Das vierte Wort heißt **Geduld**, denn nachhaltiger Spracherfolg entsteht schrittweise über längere **Zeit**.",
                      f"The fourth word is 'patience', because sustainable language success arises step by step over longer time."),
            ("Host1", f"Und das fünfte Wort ist **Selbstvertrauen**, die unverzichtbare Basis für freies und flüssiges Sprechen.",
                      f"And the fifth word is 'self-confidence', the indispensable foundation for free and fluent speech."),
            ("Host2", f"Schreibt doch bitte einen eigenen Beispielsatz mit einem dieser Wörter unten in die **Kommentare**.",
                      f"Please write your own example sentence with one of these words below in the comments."),
            ("Host1", f"Wir lesen eure Kommentare mit großem Interesse und geben euch gerne eine positive **Rückmeldung**.",
                      f"We read your comments with great interest and gladly give you positive feedback."),
            ("Host2", f"Aktives Mitmachen festigt das Gelernte viel dauerhafter im **Gedächtnis**.",
                      f"Active participation consolidates what was learned much more permanently in memory."),
            ("Host1", f"Kommen wir nun zu den abschließenden Worten unseres heutigen gemeinsamen **Programms**.",
                      f"Let's come now to the concluding words of our shared program today.")
        ],
        # Phase 10: Conclusion & wrap-up
        [
            ("Host2", f"Unsere heutige Podcast-Ausgabe über **{topic_es}** neigt sich nun langsam ihrem Ende zu.",
                      f"Our podcast edition today about {topic_en} is now slowly drawing to its end."),
            ("Host1", f"Die Zeit verging wie im Flug! Wir haben viele wertvolle Ausdrücke und Redewendungen **besprochen**.",
                      f"Time flew by! We discussed many valuable expressions and idioms."),
            ("Host2", f"Hört euch diesen Podcast ruhig mehrmals an, um die richtige Betonung und Melodie zu **verinnerlichen**.",
                      f"Listen to this podcast several times to internalize proper emphasis and melody."),
            ("Host1", f"Jede Wiederholung macht eure Aussprache sicherer, natürlicher und deutlich **flüssiger**.",
                      f"Every repetition makes your pronunciation more confident, natural and clearly more fluent."),
            ("Host2", f"Ein herzliches Dankeschön an all unsere treuen Hörer für eure Unterstützung und euer großes **Interesse**.",
                      f"A cordial thank you to all our loyal listeners for your support and your great interest."),
            ("Host1", f"Abonniert den Kanal Velocity German, gebt uns einen Daumen nach oben und empfehlt uns euren **Freunden**.",
                      f"Subscribe to Velocity German channel, give us a thumbs up and recommend us to your friends."),
            ("Host2", f"In den kommenden Folgen warten viele weitere spannende Themen und praktische Tipps auf **euch**.",
                      f"In coming episodes many more exciting topics and practical tips await you."),
            ("Host1", f"Wir wünschen euch einen wunderschönen Tag und weiterhin viel Freude beim **Deutschlernen**!",
                      f"We wish you a wonderful day and continuing much joy learning German!"),
            ("Host2", f"Macht es gut, bleibt neugierig und bis zum nächsten **Mal**!",
                      f"Take care, stay curious and until next time!"),
            ("Host1", f"Auf Wiedersehen, liebe Freunde, und sprecht fleißig mit einem **Lächeln**!",
                      f"Goodbye, dear friends, and practice diligently with a smile!")
        ]
    ]

    all_templates = []
    for ph in phases:
        all_templates.extend(ph)
    turns = []
    for i in range(target):
        _, t_de, t_en = all_templates[i % len(all_templates)]
        spk = "Host2" if i % 2 == 0 else "Host1"
        turns.append({"speaker": spk, "german": t_de, "english": t_en})
    return turns


def _extend_script(existing_turns, topic_es, topic_en, target=150):
    fallback_pool = _fallback_script(topic_es, topic_en, target)
    idx = 0
    cur_speaker = existing_turns[-1]["speaker"] if existing_turns else "Host1"
    while len(existing_turns) < target:
        cand = fallback_pool[idx % len(fallback_pool)]
        idx += 1
        needed_spk = "Host1" if cur_speaker == "Host2" else "Host2"
        existing_turns.append({
            "speaker": needed_spk,
            "german": cand["german"],
            "english": cand["english"]
        })
        cur_speaker = needed_spk
    return existing_turns[:target]


def generate_script():
    topic = _generate_topic() or random.choice(TOPICS)
    topic_es = topic.split(" - ")[0]
    topic_en = topic.split(" - ")[1]

    TARGET = 150
    BATCH = 10
    all_turns = []
    consecutive_empty = 0
    import time as _time
    _deadline = _time.time() + 600  # generous 10 min cap

    while len(all_turns) < TARGET and consecutive_empty < 12 and _time.time() < _deadline:
        batch = _fetch_turns_batch(topic, topic_es, topic_en, len(all_turns), BATCH)
        if not batch:
            consecutive_empty += 1
            wait_s = min(15, 3 + consecutive_empty * 2)
            print(f"  API busy (consecutive fails: {consecutive_empty}) - waiting {wait_s}s before retrying...", flush=True)
            _time.sleep(wait_s)
            continue
        all_turns.extend(batch)
        consecutive_empty = 0
        print(f"  Script progress: {len(all_turns)}/{TARGET} turns", flush=True)
        if len(all_turns) < TARGET:
            _time.sleep(1)

    all_turns = all_turns[:TARGET]

    if not all_turns:
        print("  Using structured fallback script (150 unique turns)...", flush=True)
        all_turns = _fallback_script(topic_es, topic_en, TARGET)
    elif len(all_turns) < TARGET:
        print(f"  Extending {len(all_turns)} turns to {TARGET} with topic conversation...", flush=True)
        all_turns = _extend_script(all_turns, topic_es, topic_en, TARGET)

    # Short 2-line intro: Lukas (Host2) first, then Maria (Host1), then topic
    all_turns[0]["speaker"] = "Host2"
    all_turns[0]["german"] = f"Hallo, ich bin Lukas. Willkommen bei Velocity German. Heute sprechen wir über **{topic_es}**."
    all_turns[0]["english"] = f"Hi, I'm Lukas. Welcome to Velocity German Podcast. Today we talk about {topic_en}."
    if len(all_turns) > 1:
        all_turns[1]["speaker"] = "Host1"
        all_turns[1]["german"] = f"Danke, Lukas. Das heutige Thema ist sehr **interessant**. Fangen wir an."
        all_turns[1]["english"] = f"Thanks, Lukas. Today's topic is very interesting. Let's start."

    print(f"  Script: {len(all_turns)} turns, topic: {topic_es}", flush=True)
    return all_turns, topic_es, topic_en


async def generate_audio(turns, target_dir=None):
    import edge_tts
    audio_files = []
    for i, turn in enumerate(turns):
        voice = HOST1_VOICE if turn["speaker"] == "Host1" else HOST2_VOICE
        audio_dir = Path(target_dir) if target_dir else OUTPUT_DIR
    audio_dir.mkdir(parents=True, exist_ok=True)
    for i, turn in enumerate(turns):
        voice = HOST1_VOICE if turn["speaker"] == "Host1" else HOST2_VOICE
        filename = audio_dir / f"audio_{i:03d}.mp3"
        spoken_text = re.sub(r'\*\*(.*?)\*\*', r'\1', turn.get("german", turn.get("spanish", "")))
        try:
            communicate = edge_tts.Communicate(spoken_text, voice)
            await communicate.save(str(filename))
            try:
                r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", str(filename)], capture_output=True, text=True)
                duration = float(r.stdout.strip()) if r.stdout else 3.0
            except:
                duration = 3.0
        except Exception as e:
            print(f"  Audio {i} failed: {e}")
            subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "3", str(filename)], capture_output=True)
            duration = 3.0
        audio_files.append({"path": str(filename), "duration": duration, "speaker": turn["speaker"]})
    return audio_files

def create_video(turns, audio_files, video_dir=None):
    if video_dir is None:
        video_dir = OUTPUT_DIR / f"podcast_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    video_dir = Path(video_dir)
    video_dir.mkdir(parents=True, exist_ok=True)

    clips = []
    total_dur = 0

    for i, (turn, audio) in enumerate(zip(turns, audio_files)):
        img = video_dir / f"f_{i:04d}.png"
        create_frame(turn, str(img), i)
        clip = video_dir / f"c_{i:04d}.mp4"
        clips.append(clip)
        dur = audio["duration"]
        fade_start = max(0.0, dur - 0.3)
        subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", str(img), "-i", audio["path"],
            "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT},fps={FPS}",
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p", "-preset", "medium",
            "-t", str(dur), "-af", f"afade=t=out:st={fade_start:.2f}:d=0.3",
            str(clip)
        ], check=True, capture_output=True)

        total_dur += audio["duration"]
        if (i + 1) % 25 == 0:
            print(f"  Frame {i+1}/{len(turns)}")

    concat = video_dir / "list.txt"
    with open(concat, "w") as f:
        for c in clips:
            f.write(f"file '{c.resolve().as_posix()}'\n")

    out = video_dir / "podcast_final.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
                    "-movflags", "+faststart", str(out)], check=True)

    for c in clips:
        c.unlink(missing_ok=True)
    for a in audio_files:
        try:
            Path(a["path"]).unlink(missing_ok=True)
        except Exception:
            pass
    if concat.exists():
        concat.unlink(missing_ok=True)

    return out, total_dur


async def main():
    print("=" * 60)
    print("  VELOCITY GERMAN PODCAST")
    print("=" * 60)

    print("\n[1/4] Generating script (150 turns)...")
    turns, topic_es, topic_en = generate_script()

    video_dir = OUTPUT_DIR / f"podcast_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    video_dir.mkdir(parents=True, exist_ok=True)

    with open(video_dir / "script.json", "w", encoding="utf-8") as f:
        json.dump({"topic": topic_es, "topic_en": topic_en, "turns": turns}, f, indent=2, ensure_ascii=False)

    print(f"\n[2/4] Generating audio ({len(turns)} turns)...")
    audio_files = await generate_audio(turns, video_dir)
    total_audio = sum(a["duration"] for a in audio_files)
    print(f"  Total audio: {total_audio/60:.1f} min")

    print(f"\n[3/4] Creating video...")
    video_path, duration = create_video(turns, audio_files, video_dir)

    print(f"\n[4/4] Saving...")
    first_frame = video_dir / "f_0000.png"
    thumbnail_path = video_dir / "thumbnail.jpg"
    try:
        from PIL import Image as _Img
        if first_frame.exists():
            _Img.open(str(first_frame)).convert("RGB").save(str(thumbnail_path), quality=92)
    except Exception as e:
        print(f"  Thumbnail warn: {e}")

    title = build_podcast_title(topic_es, topic_en)
    description = build_podcast_description(topic_es, topic_en, len(turns), round(duration / 60, 1))
    tags = ["Learn German", "German", "German Podcast", "Learn German Naturally",
            "German for Beginners", "Bilingual", "German Listening", "German Conversation",
            topic_es, "Velocity German"]

    meta_out = {
        "title": title,
        "description": description,
        "tags": tags,
        "category_english": topic_es,
        "language": "German",
        "duration_minutes": round(duration / 60, 1),
        "turns_count": len(turns),
        "video_path": str(video_path),
        "thumbnail_path": str(thumbnail_path),
        "generated_at": datetime.now().isoformat(),
    }
    (OUTPUT_DIR).mkdir(exist_ok=True)
    with open(OUTPUT_DIR / "latest_video.json", "w", encoding="utf-8") as f:
        json.dump(meta_out, f, indent=2, ensure_ascii=False)
    with open(OUTPUT_DIR / "latest_upload_info.json", "w", encoding="utf-8") as f:
        json.dump({"title": title, "description": description,
                   "category": topic_es, "turns_count": len(turns)}, f, indent=2, ensure_ascii=False)

    print("=" * 60)
    print("  PODCAST COMPLETE!")
    print(f"  Topic: {topic_es}")
    print(f"  Duration: {duration/60:.1f} min ({len(turns)} turns)")
    print(f"  Video: {video_path.name}")
    print("=" * 60)


def build_podcast_title(topic_es, topic_en):
    titles = [
        f"German Podcast: {topic_es} | Lerne Deutsch",
        f"Learn German: {topic_es} | Bilingual Podcast",
        f"{topic_es} | German Conversation for Beginners",
        f"{topic_es} | Übe dein Deutsch mit Maria und Lukas",
    ]
    return random.choice(titles)


def build_podcast_description(topic_es, topic_en, turns_count, duration_min):
    description = (
        f"🎙️ Willkommen bei Velocity German Podcast!\n\n"
        f"In dieser Folge unterhalten sich Maria und Lukas über: {topic_es} ({topic_en}).\n"
        f"Eine entspannte zweisprachige Unterhaltung auf A2-Niveau, um Deutsch auf natürliche Weise zu lernen.\n\n"
        f"✨ WHAT'S INSIDE THIS EPISODE:\n"
        f"• {turns_count} nützliche Sätze und Ausdrücke auf Deutsch\n"
        f"• Echte Gespräche mit alltäglichem Wortschatz\n"
        f"• Natürliche Aussprache von Muttersprachlern\n"
        f"• Englische Übersetzung in jeder Zeile\n\n"
        f"📌 HOW TO USE THIS PODCAST:\n"
        f"1️⃣ Höre den deutschen Teil und versuche zu verstehen\n"
        f"2️⃣ Prüfe die englische Übersetzung\n"
        f"3️⃣ Sprich die Sätze laut nach\n"
        f"4️⃣ Höre morgen wieder - jeden Tag wird es einfacher!\n\n"
        f"🔔 Abonniere für eine neue Lektion jeden Tag.\n\n"
        f"📅 Dauer: {duration_min} Minuten\n\n"
        f"#LearnGerman #GermanPodcast #Bilingual #LanguageLearning"
    )
    return description



if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('  Cancelled.')