"""ScentAI - AI image and video ad studio for fragrance brands (Streamlit + Gemini / Veo)."""
import hashlib
import hmac
import io
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st
from PIL import Image

try:
    from google import genai
    from google.genai import types
except ImportError:  # shown in the UI
    genai = None

st.set_page_config(page_title="ScentAI | AI perfume ad studio", page_icon="🌿", layout="wide")

# ----------------------------------------------------------------- config
DEFAULT_OPAL = "https://opal.google/app/1BztoIE8FXaKXZ1YRjxzrZOlQ6PQuBeU2"
IMAGE_MODELS = ["gemini-2.5-flash-image", "gemini-3-pro-image-preview"]
VIDEO_MODELS = ["veo-3.1-fast-generate-preview", "veo-3.1-generate-preview"]
ETHNICITIES = ["Nigerian", "African", "Caucasian", "Mongolian", "Latin", "East Asian",
               "South Asian", "Middle Eastern", "Mixed / any"]
THEMES = {
    "Golden Hour Luxury": "warm sun-kissed golden hour light, honeyed glow, soft lens flare, cinematic",
    "Midnight Mystery": "moody dramatic night scene, neon rim light, deep shadows, wet reflective surfaces",
    "Botanical Essence": "fresh dew-covered florals, woods and green leaves, natural diffused daylight",
    "Minimalist Modern": "clean architectural studio, pale stone and glass, soft even light, negative space",
}
THEME_COLORS = {"Golden Hour Luxury": "#E8C987", "Midnight Mystery": "#0B2F4A",
                "Botanical Essence": "#1F8A70", "Minimalist Modern": "#D7E6EA"}
RATIOS = {"4:5": (4, 5), "9:16": (9, 16), "16:9": (16, 9)}
CAMERAS = ["Slow push-in", "Orbit around the bottle", "Handheld follow", "Macro rack focus",
           "Static, shallow depth of field", "Crane reveal"]
STORE = Path(os.getenv("SCENTAI_DATA", "campaigns"))


def secret(name, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return os.getenv(name, default)


# ----------------------------------------------------------------- styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bodoni+Moda:ital,opsz,wght@0,6..96,400;0,6..96,600;1,6..96,400&family=Figtree:wght@400;500;600&display=swap');
:root{--ink:#0B2F4A;--sea:#1F8A70;--mist:#EEF6F5;--aqua:#D5EAE6;--line:#C9DCDD;--blue:#1C5D99}
html,body,[class*="css"],.stApp{font-family:'Figtree',sans-serif;color:var(--ink)}
#MainMenu,footer,header[data-testid="stHeader"]{visibility:hidden;height:0}
.block-container{max-width:1180px;padding:1.2rem 1.2rem 3rem}
h1,h2,h3,.display{font-family:'Bodoni Moda',serif!important;font-weight:400!important;letter-spacing:-.01em;color:var(--ink)}
.nav{display:flex;justify-content:space-between;align-items:center;padding:.4rem 0 1rem;border-bottom:1px solid var(--line)}
.logo{font-family:'Bodoni Moda',serif;font-size:1.6rem;color:var(--ink)}
.logo b{color:var(--sea);font-weight:600}
.hero{display:grid;grid-template-columns:1.25fr .75fr;gap:2rem;align-items:center;padding:2.5rem 0 1.5rem}
.hero h1{font-size:clamp(2.1rem,5.6vw,4rem);line-height:1.05;margin:0 0 1rem}
.hero p{font-size:1.1rem;max-width:34rem;line-height:1.55;color:#2d5069}
.btns{display:flex;gap:.8rem;flex-wrap:wrap;margin-top:1.4rem}
.btn{display:inline-block;padding:.85rem 1.5rem;border-radius:999px;text-decoration:none!important;font-weight:600;font-size:.98rem;border:1.5px solid var(--ink);color:var(--ink)!important}
.btn.solid{background:var(--ink);color:#fff!important}
.bottle{width:100%;max-width:320px;margin:auto;display:block}
.bottle .liquid{animation:sway 7s ease-in-out infinite;transform-origin:50% 100%}
@keyframes sway{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}
.pulse-wrap{text-align:center;margin:1.2rem 0}
.pulse{display:inline-block;padding:1rem 2.2rem;border-radius:999px;background:linear-gradient(135deg,var(--blue),var(--sea));color:#fff!important;font-weight:600;font-size:1.1rem;text-decoration:none!important;animation:pulse 2s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(31,138,112,.55)}70%{box-shadow:0 0 0 18px rgba(31,138,112,0)}100%{box-shadow:0 0 0 0 rgba(31,138,112,0)}}
@media (prefers-reduced-motion:reduce){.pulse,.bottle .liquid{animation:none}}
.swatches{display:grid;grid-template-columns:repeat(4,1fr);gap:.8rem}
.sw{border-radius:14px;padding:1rem;min-height:120px;display:flex;flex-direction:column;justify-content:flex-end;font-size:.9rem}
.sw b{font-family:'Bodoni Moda',serif;font-size:1.1rem;font-weight:400}
.chips span{display:inline-block;margin:.2rem .3rem .2rem 0;padding:.35rem .9rem;border-radius:999px;background:var(--mist);border:1px solid var(--line);font-size:.92rem}
.steps{display:grid;grid-template-columns:repeat(4,1fr);gap:1.2rem}
.steps div{border-top:2px solid var(--sea);padding-top:.7rem;font-size:.95rem;line-height:1.5}
.steps b{display:block;font-family:'Bodoni Moda',serif;font-size:1.15rem;font-weight:400;margin-bottom:.2rem}
.foot{margin-top:3rem;padding-top:1.4rem;border-top:1px solid var(--line);display:flex;flex-wrap:wrap;gap:1rem 2rem;justify-content:space-between;align-items:center;font-size:.9rem}
.foot a{color:var(--ink);margin-right:1.1rem}
.stButton>button,.stDownloadButton>button{border-radius:999px;font-weight:600}
.stButton>button[kind="primary"]{background:var(--sea);border-color:var(--sea)}
@media (max-width:760px){.hero{grid-template-columns:1fr}.swatches,.steps{grid-template-columns:1fr 1fr}.bottle{max-width:200px}}
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------- auth
def check_login():
    users = secret("users") or {}
    if not users:
        st.sidebar.warning("No [users] set in secrets: login is off. Add users before sharing this app.")
        return "guest"
    if st.session_state.get("user"):
        return st.session_state["user"]
    st.markdown('<div class="nav"><span class="logo">Scent<b>AI</b></span></div>', unsafe_allow_html=True)
    st.subheader("Sign in")
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        ok = st.form_submit_button("Sign in", type="primary")
    if ok:
        if time.time() < st.session_state.get("lock_until", 0):
            st.error("Too many attempts. Wait a minute and try again.")
        else:
            digest = hashlib.sha256(p.encode()).hexdigest()
            if u in users and hmac.compare_digest(digest, str(users[u])):
                st.session_state["user"] = u
                st.session_state["fails"] = 0
                st.rerun()
            st.session_state["fails"] = st.session_state.get("fails", 0) + 1
            if st.session_state["fails"] >= 5:
                st.session_state["lock_until"] = time.time() + 60
                st.session_state["fails"] = 0
            st.error("Username or password is incorrect.")
    st.stop()


user = check_login()
OPAL_URL = secret("OPAL_URL", DEFAULT_OPAL)

# ----------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("### Settings")
    if user != "guest" and st.button("Sign out"):
        st.session_state.pop("user", None)
        st.rerun()
    manual_key = st.text_input("Gemini API key (optional override)", type="password",
                               help="Normally set as GEMINI_API_KEY in secrets.")
    image_model = st.selectbox("Image model", IMAGE_MODELS)
    video_model = st.selectbox("Video model", VIDEO_MODELS)
    resolution = st.selectbox("Video resolution", ["720p", "1080p"],
                              help="1080p works with 16:9 only.")
    st.caption("Veo makes 8-second clips with native voices and lip-sync.")


def get_client():
    key = manual_key or secret("GEMINI_API_KEY")
    if genai is None:
        st.error("Install dependencies first: pip install -r requirements.txt")
        st.stop()
    if not key:
        st.error("Add GEMINI_API_KEY to .streamlit/secrets.toml, or paste a key in the sidebar.")
        st.stop()
    return genai.Client(api_key=key)


# ----------------------------------------------------------------- helpers
def user_dir():
    d = STORE / "".join(c for c in user if c.isalnum() or c in "-_")
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_asset(data: bytes, ext: str, prompt: str):
    stem = f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:5]}"
    p = user_dir() / f"{stem}.{ext}"
    p.write_bytes(data)
    p.with_suffix(".txt").write_text(prompt, encoding="utf-8")
    return p


def crop_image(data: bytes, ratio: str, fmt="PNG"):
    w_r, h_r = RATIOS[ratio]
    im = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = im.size
    target = w_r / h_r
    if w / h > target:
        nw = int(h * target); im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w / target); im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    out = io.BytesIO(); im.save(out, fmt, **({"quality": 95} if fmt == "JPEG" else {}))
    return out.getvalue()


def ffmpeg_ok():
    return shutil.which("ffmpeg") is not None


def crop_video(data: bytes, ratio: str):
    w_r, h_r = RATIOS[ratio]
    with tempfile.TemporaryDirectory() as t:
        src, dst = Path(t, "in.mp4"), Path(t, "out.mp4")
        src.write_bytes(data)
        vf = f"crop='min(iw,ih*{w_r}/{h_r})':'min(ih,iw*{h_r}/{w_r})'"
        subprocess.run(["ffmpeg", "-y", "-i", str(src), "-vf", vf, "-c:a", "copy", str(dst)],
                       check=True, capture_output=True)
        return dst.read_bytes()


def join_videos(clips: list):
    with tempfile.TemporaryDirectory() as t:
        lst = Path(t, "list.txt")
        lines = []
        for i, c in enumerate(clips):
            p = Path(t, f"c{i}.mp4"); p.write_bytes(c); lines.append(f"file '{p}'")
        lst.write_text("\n".join(lines))
        dst = Path(t, "out.mp4")
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-c:v", "libx264", "-c:a", "aac", str(dst)], check=True, capture_output=True)
        return dst.read_bytes()


def ad_prompt(idea, ethnicity, theme, extra=""):
    model = "" if ethnicity.startswith("Mixed") else f"A {ethnicity} fashion model. "
    return (f"Luxury perfume campaign. {model}{idea}. Style: {THEMES[theme]}. "
            f"Photorealistic, ultra-detailed, premium editorial quality, natural skin texture, "
            f"elegant glass bottle with accurate reflections. {extra}").strip()


def generate_image(client, prompt, ratio, refs=None):
    contents = [prompt] + (refs or [])
    resp = client.models.generate_content(
        model=image_model, contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            image_config=types.ImageConfig(aspect_ratio=ratio)))
    for part in resp.candidates[0].content.parts:
        if getattr(part, "inline_data", None) and part.inline_data.data:
            return part.inline_data.data
    raise RuntimeError("The model returned no image. Try rewording the prompt.")


def generate_clip(client, prompt, ratio, image_bytes=None, status=None):
    api_ratio = "16:9" if ratio == "16:9" else "9:16"
    res = resolution if api_ratio == "16:9" else "720p"
    kwargs = dict(model=video_model, prompt=prompt,
                  config=types.GenerateVideosConfig(aspect_ratio=api_ratio, resolution=res))
    if image_bytes:
        kwargs["image"] = types.Image(image_bytes=image_bytes, mime_type="image/png")
    op = client.models.generate_videos(**kwargs)
    start = time.time()
    while not op.done:
        if status:
            status(min(0.95, (time.time() - start) / 150))
        time.sleep(8)
        op = client.operations.get(op)
    if getattr(op, "error", None):
        raise RuntimeError(str(op.error))
    vids = getattr(op.response, "generated_videos", None)
    if not vids:
        raise RuntimeError("No video returned. The prompt may have been blocked; reword it and retry.")
    client.files.download(file=vids[0].video)
    data = vids[0].video.video_bytes
    if ratio == "4:5":
        if not ffmpeg_ok():
            st.warning("Install ffmpeg to export 4:5. Showing 9:16 instead.")
        else:
            data = crop_video(data, "4:5")
    return data


def png_bytes(upload):
    im = Image.open(upload).convert("RGB")
    im.thumbnail((1600, 1600))
    out = io.BytesIO(); im.save(out, "PNG")
    return out.getvalue()


# ----------------------------------------------------------------- hero
BOTTLE = """<svg class="bottle" viewBox="0 0 200 280" role="img" aria-label="Perfume bottle illustration">
<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7FD1B9"/><stop offset="1" stop-color="#1C5D99"/></linearGradient></defs>
<rect x="82" y="14" width="36" height="30" rx="4" fill="#0B2F4A"/>
<rect x="90" y="44" width="20" height="16" fill="#C9DCDD"/>
<rect x="30" y="60" width="140" height="190" rx="26" fill="#fff" stroke="#0B2F4A" stroke-width="3"/>
<g class="liquid"><rect x="38" y="120" width="124" height="122" rx="20" fill="url(#g)" opacity=".92"/></g>
<rect x="62" y="150" width="76" height="52" rx="4" fill="#fff" opacity=".9"/>
<text x="100" y="182" text-anchor="middle" font-family="Georgia,serif" font-size="17" fill="#0B2F4A">ScentAI</text>
<path d="M46 80 q-4 60 0 120" stroke="#fff" stroke-width="5" fill="none" opacity=".7" stroke-linecap="round"/>
</svg>"""

st.markdown(f"""
<div class="nav"><span class="logo">Scent<b>AI</b></span>
<span><a href="#studio" style="color:#0B2F4A">Studio</a></span></div>
<div class="hero"><div>
<h1>Craft hypnotic perfume adverts and visuals with AI in seconds</h1>
<p>Generate cinematic commercial videos, luxury bottle mockups, and high-fashion model campaigns across diverse ethnicities instantly with AI.</p>
<div class="btns"><a class="btn solid" href="#studio">Generate Image</a>
<a class="btn" href="#studio">Create Video Here</a></div></div>
<div>{BOTTLE}</div></div>
<div class="pulse-wrap"><a class="pulse" href="{OPAL_URL}" target="_blank" rel="noopener noreferrer">🎬 Create Custom Ad Video Here</a></div>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------- studio
st.markdown('<div id="studio"></div>', unsafe_allow_html=True)
st.header("Studio")
tab_img, tab_vid, tab_lib = st.tabs(["Images", "Commercial video", "Campaign library"])

# ---- images
with tab_img:
    mode = st.radio("Mode", ["Prompt to image", "Image to image"], horizontal=True)
    c1, c2 = st.columns(2)
    with c1:
        idea = st.text_area("Describe your visual", height=120, key="img_idea",
                            placeholder="Model holding a blue-green glass bottle on a rooftop at dusk, wind in her hair")
        ethn = st.selectbox("Model ethnicity", ETHNICITIES, key="img_eth")
        theme = st.selectbox("Campaign style", list(THEMES), key="img_theme")
        ratio = st.selectbox("Format", list(RATIOS), key="img_ratio",
                             format_func=lambda r: {"4:5": "4:5 feed", "9:16": "9:16 story", "16:9": "16:9 wide"}[r])
        src = None
        if mode == "Image to image":
            up = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg", "webp"], key="img_up")
            if up:
                src = png_bytes(up)
                st.image(src, caption="Original", use_container_width=True)
        go = st.button("Generate image", type="primary", key="img_go")
    with c2:
        if go:
            if not idea.strip():
                st.error("Describe the image first.")
            elif mode == "Image to image" and not src:
                st.error("Upload an image to transform.")
            else:
                client = get_client()
                prompt = ad_prompt(idea, ethn, theme, "Keep the uploaded product exactly as it is." if src else "")
                try:
                    with st.spinner("Painting your campaign frame…"):
                        refs = [Image.open(io.BytesIO(src))] if src else None
                        data = generate_image(client, prompt, ratio, refs)
                        save_asset(data, "png", prompt)
                        st.session_state["last_img"] = data
                except Exception as e:
                    st.error(f"Image generation failed: {e}")
        if "last_img" in st.session_state:
            st.image(st.session_state["last_img"], caption="Generated", use_container_width=True)
            cols = st.columns(3)
            for col, r in zip(cols, RATIOS):
                col.download_button(f"Download {r}", crop_image(st.session_state["last_img"], r),
                                    file_name=f"scentai-{r.replace(':', 'x')}.png", mime="image/png",
                                    key=f"dl_img_{r}", use_container_width=True)

# ---- video
with tab_vid:
    vmode = st.radio("Mode", ["Prompt to video", "Bottle image to video"], horizontal=True)
    left, right = st.columns(2)
    with left:
        videa = st.text_area("Scene, mood and setting", height=100, key="v_idea",
                             placeholder="A woman steps onto a balcony at golden hour and lifts the bottle to her wrist")
        cam = st.selectbox("Camera movement", CAMERAS)
        vethn = st.selectbox("Model ethnicity", ETHNICITIES, key="v_eth")
        vtheme = st.selectbox("Campaign style", list(THEMES), key="v_theme")
        vratio = st.selectbox("Format", list(RATIOS), key="v_ratio", index=1)
        bottle = None
        if vmode == "Bottle image to video":
            bu = st.file_uploader("Upload your perfume bottle", type=["png", "jpg", "jpeg", "webp"], key="v_up")
            if bu:
                bottle = png_bytes(bu)
                st.image(bottle, caption="Original bottle", use_container_width=True)
        st.markdown("**Voices and dialogue** (optional)")
        narr = st.text_input("Voiceover narration", placeholder="Some scents don't announce themselves. They arrive.")
        n_char = st.slider("Speaking characters", 0, 3, 0)
        chars = []
        for i in range(n_char):
            a, b = st.columns([1, 2])
            nm = a.text_input(f"Name {i+1}", value=["Ada", "Marcus", "Lin"][i], key=f"cn{i}")
            vo = b.text_input("Look and voice", key=f"cv{i}",
                              value=["Nigerian woman, warm low voice", "Caucasian man, calm baritone",
                                     "Mongolian woman, soft clear voice"][i])
            chars.append((nm, vo))
        script = st.text_area(
            "Scenes (separate scenes with a line of ---; write dialogue as NAME: line)", height=140, key="v_script",
            placeholder="Ada: Is that new?\nMarcus: It's the only thing I'm wearing tonight.\n---\nAda: Then I'll stay a little longer.")
        vgo = st.button("Generate commercial", type="primary", key="v_go")
    with right:
        if vgo:
            if not videa.strip():
                st.error("Describe the scene first.")
            elif vmode == "Bottle image to video" and not bottle:
                st.error("Upload your bottle image first.")
            else:
                client = get_client()
                scenes = [s.strip() for s in script.split("---") if s.strip()] or [""]
                if len(scenes) > 1 and not ffmpeg_ok():
                    st.info("ffmpeg isn't installed, so scenes will appear as separate clips.")
                base = ad_prompt(videa, vethn, vtheme, f"Camera: {cam}.")
                cast = " ".join(f"{n} is {v}." for n, v in chars)
                prog = st.progress(0.0, text="Starting…")
                clips, prompts = [], []
                try:
                    for i, sc in enumerate(scenes):
                        p = base + (f" Cast: {cast}" if cast else "")
                        if narr and i == 0:
                            p += f' A voiceover says: "{narr}"'
                        if sc:
                            p += (" Scripted dialogue, each character speaks their own line with distinct voice, "
                                  "natural emotion and lip movements synchronized to the speech. "
                                  f"Dialogue: {sc}")
                        p += " No subtitles or on-screen text. Consistent audio and characters."
                        label = f"Scene {i+1} of {len(scenes)}: rendering (1-3 min)…"
                        clip = generate_clip(client, p, vratio, bottle,
                                             status=lambda f, i=i, label=label: prog.progress(
                                                 (i + f) / len(scenes), text=label))
                        clips.append(clip); prompts.append(p)
                        save_asset(clip, "mp4", p)
                    prog.progress(1.0, text="Done")
                    final = clips[0] if len(clips) == 1 or not ffmpeg_ok() else join_videos(clips)
                    if len(clips) > 1 and ffmpeg_ok():
                        save_asset(final, "mp4", "Joined: " + " || ".join(prompts))
                    st.session_state["last_vid"] = final
                    st.session_state["last_clips"] = clips if not ffmpeg_ok() else []
                except Exception as e:
                    prog.empty()
                    st.error(f"Video generation failed: {e}")
        if "last_vid" in st.session_state:
            if st.session_state.get("last_clips"):
                for i, c in enumerate(st.session_state["last_clips"]):
                    st.video(c); st.download_button(f"Download scene {i+1}", c, f"scentai-scene{i+1}.mp4",
                                                    "video/mp4", key=f"dlc{i}")
            else:
                st.video(st.session_state["last_vid"])
                st.download_button("Download video (HD)", st.session_state["last_vid"], "scentai-ad.mp4",
                                   "video/mp4", key="dlv", use_container_width=True)
        if vmode == "Bottle image to video" and bottle:
            st.caption("Your bottle is used as the first frame, so the product stays exact.")

# ---- library
with tab_lib:
    files = sorted([p for p in user_dir().iterdir() if p.suffix in (".png", ".mp4")], reverse=True)[:18]
    if not files:
        st.info("Nothing here yet. Generate an image or commercial and it will be saved to this library.")
    else:
        cols = st.columns(3)
        for i, p in enumerate(files):
            with cols[i % 3]:
                if p.suffix == ".png":
                    st.image(str(p), use_container_width=True)
                else:
                    st.video(str(p))
                note = p.with_suffix(".txt")
                if note.exists():
                    st.caption(note.read_text(encoding="utf-8")[:110] + "…")
                st.download_button("Download", p.read_bytes(), p.name,
                                   "image/png" if p.suffix == ".png" else "video/mp4", key=f"lib{p.name}")

# ----------------------------------------------------------------- showcase
st.header("Campaign styles")
st.markdown('<div class="swatches">' + "".join(
    f'<div class="sw" style="background:{THEME_COLORS[k]};color:{"#fff" if k in ("Midnight Mystery","Botanical Essence") else "#0B2F4A"}">'
    f'<b>{k}</b>{v.split(",")[0]}</div>' for k, v in THEMES.items()) + "</div>", unsafe_allow_html=True)
st.markdown("#### Models from around the world")
st.markdown('<div class="chips">' + "".join(f"<span>{e}</span>" for e in ETHNICITIES) + "</div>",
            unsafe_allow_html=True)

st.header("How it works")
st.markdown("""<div class="steps">
<div><b>Upload or describe</b>Add your bottle photo or write your creative idea.</div>
<div><b>Pick a look</b>Choose model ethnicity, lighting mood and camera movement.</div>
<div><b>Generate</b>Get a commercial sized for TikTok, Instagram and YouTube, with voices.</div>
<div><b>Download and publish</b>Export 4:5, 9:16 or 16:9, ready for campaigns.</div>
</div>""", unsafe_allow_html=True)

st.markdown(f"""<div class="foot"><span class="logo">Scent<b>AI</b></span>
<span><a href="#">About</a><a href="mailto:hello@scentai.example">Contact</a><a href="#">Privacy Policy</a><a href="#">Terms of Service</a></span>
<span>© {datetime.now().year} ScentAI. All rights reserved.</span></div>""", unsafe_allow_html=True)
