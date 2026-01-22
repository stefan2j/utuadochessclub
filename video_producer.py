import os
import requests
import feedparser
import re
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from google.cloud import texttospeech
from google import genai 
from google.genai import types
from moviepy import *
from PIL import Image
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN ---
API_KEY = "AIzaSyD6cujWwG67kOQuVRzZ0cRDi3_0DsLWYHs"
NTFY_TOPIC = "utuado_noticias"
OUTPUT_VIDEO = "Morning_Briefing_Pro.mp4"
DEFAULT_IMAGE = "default_news.png" 

# Cliente Gemini (Usando modelo estable)
client = genai.Client(api_key=API_KEY)

# Voces Neurales (Google Cloud)
VOZ_PRESENTADOR = "es-US-Neural2-B" 
VOZ_REPORTERO = "es-US-Neural2-A"   

FEEDS = [
    ("Metro PR", "https://www.metro.pr/arc/outboundfeeds/rss/?outputType=xml", "local"),
    ("CPI", "https://periodismoinvestigativo.com/feed/", "local"),
    ("Radio Isla", "https://radioisla.tv/feed/", "local"),
    ("AP News", "https://apnews.com/index.rss", "us"),
    ("NY Times", "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml", "us")
]

KEYWORDS = ["gobierno", "senado", "gobernador", "alcalde", "trump", "biden", "deporte", "política", "utuado"]

# --- 1. BUSCADOR DE NOTICIAS ---
def get_top_5_stories():
    print("📡 Escaneando noticias...")
    candidates = []
    cutoff_time = datetime.now().astimezone() - timedelta(hours=24)
    for source_name, url, source_type in FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if hasattr(entry, 'published'):
                    try:
                        article_date = date_parser.parse(entry.published)
                        if article_date.tzinfo is None: article_date = article_date.astimezone()
                        if article_date < cutoff_time: continue
                    except: continue
                full_text = (entry.title + " " + entry.get('summary', '')).lower()
                score = 0
                if any(k in full_text for k in KEYWORDS): score += 10
                if source_type == "us" and "puerto rico" not in full_text: continue
                if score > 0:
                    candidates.append({"title": entry.title, "link": entry.link, "summary": entry.get('summary', entry.title), "score": score})
        except: pass
    candidates.sort(key=lambda x: x['score'], reverse=True)
    return candidates[:5]

# --- 2. NOTIFICACIÓN ---
def send_mobile_notification(message):
    try:
        requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=message.encode('utf-8'),
            headers={"Title": "Noticiero Listo 🎬", "Priority": "high", "Tags": "video_camera"})
        print("📲 Notificación enviada.")
    except: pass

# --- 3. DIÁLOGO (GEMINI CORREGIDO) ---
def get_full_article_text(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        paragraphs = soup.find_all('p')
        full_text = " ".join([p.get_text() for p in paragraphs])
        return full_text[:4000] 
    except: return ""

def get_dialogue_script(title, url):
    print(f"🧠 Gemini leyendo noticia: {title[:30]}...")
    full_content = get_full_article_text(url)
    context = full_content if len(full_content) > 200 else title
    
    prompt = f"""
    Eres un productor de noticias de radio. 
    Basándote EXCLUSIVAMENTE en este texto: "{context}"
    Escribe un guion corto y dinámico (máx 180 palabras).
    Usa EXACTAMENTE este formato:
    PRESENTADOR: (Intro impactante de 1 frase)
    REPORTERO: (Desarrollo de la noticia con datos)
    """
    try:
        # MODELO CAMBIADO A 'gemini-1.5-flash' (Sin 'latest')
        response = client.models.generate_content(
            model='gemini-1.5-flash', 
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.7)
        )
        return response.text.replace("**", "").replace("##", "")
    except Exception as e:
        print(f"⚠️ Error Gemini: {e}")
        return f"PRESENTADOR: Noticia importante. REPORTERO: {title}."

# --- 4. AUDIO DUAL ROBUSTO (GOOGLE) ---
def generate_dual_audio(script, filename):
    client_tts = texttospeech.TextToSpeechClient(client_options={"api_key": API_KEY})
    combined_audio = b""
    
    parts = re.split(r'(?i)(PRESENTADOR:|REPORTERO:)', script)
    current_role = VOZ_REPORTERO 
    
    for part in parts:
        part = part.strip()
        if not part: continue
        
        if "PRESENTADOR" in part.upper():
            current_role = VOZ_PRESENTADOR
            continue
        elif "REPORTERO" in part.upper():
            current_role = VOZ_REPORTERO
            continue
        
        try:
            synthesis_input = texttospeech.SynthesisInput(text=part)
            voice = texttospeech.VoiceSelectionParams(language_code="es-US", name=current_role)
            audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=1.0)
            response = client_tts.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
            combined_audio += response.audio_content
        except Exception as e:
            print(f"⚠️ Error sintetizando fragmento: {e}")

    if len(combined_audio) == 0:
        synthesis_input = texttospeech.SynthesisInput(text=script)
        voice = texttospeech.VoiceSelectionParams(language_code="es-US", name=VOZ_REPORTERO)
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
        response = client_tts.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
        combined_audio = response.audio_content

    with open(filename, "wb") as out: out.write(combined_audio)

# --- 5. IMÁGENES Y VIDEO ---
def get_image_from_url(url, filename):
    try:
        if os.path.exists(filename): os.remove(filename)
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.content, 'html.parser')
        img_tag = soup.find("meta", property="og:image")
        if img_tag:
            img_data = requests.get(img_tag["content"]).content
            with open(filename, 'wb') as f: f.write(img_data)
            return True
    except: pass
    return False

def create_slide(story, index):
    print(f"🎨 Procesando Noticia #{index+1}...")
    audio_file, img_file = f"temp_a_{index}.mp3", f"temp_i_{index}.jpg"
    
    script = get_dialogue_script(story['title'], story['link']) 
    generate_dual_audio(script, audio_file)
    
    if not get_image_from_url(story['link'], img_file):
        try:
            Image.open(DEFAULT_IMAGE).convert("RGB").save(img_file)
        except:
            Image.new('RGB', (1280, 720), (100, 0, 0)).save(img_file)

    try:
        audio_clip = AudioFileClip(audio_file)
    except OSError:
        return None, [audio_file, img_file]

    image_clip = ImageClip(img_file).with_duration(audio_clip.duration + 1)
    return image_clip.resized(height=720).with_position("center").with_audio(audio_clip), [audio_file, img_file]

# --- EJECUCIÓN ---
if __name__ == "__main__":
    current_folder = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_folder)
    
    stories = get_top_5_stories()
    if stories:
        clips, temp_files = [], []
        for i, story in enumerate(stories):
            clip, files = create_slide(story, i)
            if clip:
                clips.append(clip)
            temp_files.extend(files)
            
        if clips:
            print("🎞️ Renderizando video final...")
            final_video = concatenate_videoclips(clips, method="compose")
            final_video.write_videofile(OUTPUT_VIDEO, fps=24) 
            
            send_mobile_notification(f"¡Video listo! {len(clips)} noticias.")
            print(f"✅ ÉXITO: {OUTPUT_VIDEO}")
            
            # --- INTEGRACIÓN DEL UPLOADER ---
            try:
                import video_uploader
                print("📤 Iniciando subida automática a Facebook...")
                video_uploader.upload_to_facebook()
            except Exception as e:
                print(f"⚠️ El video se creó pero falló la subida: {e}")
            # ------------------------------------

        else:
            print("❌ No se pudieron generar clips válidos.")
            
        for f in temp_files: 
            if os.path.exists(f): 
                try: os.remove(f)
                except: pass