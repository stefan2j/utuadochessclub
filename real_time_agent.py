import time
import os
import requests
import feedparser
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

# --- CONFIGURACIÓN ---
API_KEY = "AIzaSyD6cujWwG67kOQuVRzZ0cRDi3_0DsLWYHs" 
SCHEDULE_HOURS = [8, 11, 14, 17] 
HOURS_BACK = 24

# Inicialización del cliente Gemini
client = genai.Client(api_key=API_KEY)

# Rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE_DIR, "posted_history.txt")
PROFILE_PATH = os.path.join(BASE_DIR, "ChromeProfile")

FEEDS = [
    ("Metro PR", "https://www.metro.pr/arc/outboundfeeds/rss/?outputType=xml", "local"),
    ("CPI", "https://periodismoinvestigativo.com/feed/", "local"),
    ("Radio Isla", "https://radioisla.tv/feed/", "local"),
    ("AP News", "https://apnews.com/index.rss", "us"),
    ("NY Times", "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml", "us")
]

KEYWORDS = ["gobierno", "senado", "gobernador", "alcalde", "trump", "biden", "deporte", "política", "utuado"]

# --- FUNCIONES DE APOYO ---
def make_bold(text):
    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    bold   = "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝗅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
    return text.translate(str.maketrans(normal, bold))

def get_full_article_text(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        paragraphs = soup.find_all('p')
        text = " ".join([p.get_text() for p in paragraphs])
        return text[:4000]
    except: return ""

def load_history():
    if not os.path.exists(HISTORY_FILE): return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines()]

def save_to_history(link):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{link}\n")

# --- GENERACIÓN DE CONTENIDO (MODELO CORREGIDO) ---
def get_gemini_summary(title, url):
    print(f"🧠 Analizando noticia completa con Gemini...")
    full_text = get_full_article_text(url)
    context = full_text if len(full_text) > 200 else title

    instr = "Eres el editor jefe de 'A Tu Alcance'. Crea un titular corto en MAYÚSCULAS y un resumen de 3 oraciones. NO uses asteriscos ni markdown."
    
    try:
        # CAMBIO: 'gemini-1.5-flash'
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=f"Basado exclusivamente en este texto, redacta la noticia: {context}",
            config=types.GenerateContentConfig(
                system_instruction=instr,
                temperature=0.4
            )
        )
        content = response.text.replace("**", "").replace("##", "")
        lines = content.split('\n')
        if lines: lines[0] = make_bold(lines[0])
        return "<br>".join(lines)
    except Exception as e:
        print(f"❌ Error en Gemini: {e}")
        return make_bold(title.upper())

# --- LÓGICA DE FACEBOOK ---
def post_to_facebook(text_html, link):
    chrome_options = Options()
    chrome_options.add_argument(f"user-data-dir={PROFILE_PATH}")
    chrome_options.add_argument("--disable-notifications")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.maximize_window()

    try:
        driver.get("https://www.facebook.com")
        time.sleep(10)

        box = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@aria-label, 'on your mind')]")))
        box.click()
        time.sleep(5)

        active_element = driver.switch_to.active_element
        active_element.send_keys(link)
        print("⏳ Generando vista previa...")
        time.sleep(20)

        active_element.send_keys(Keys.CONTROL + "a")
        active_element.send_keys(Keys.BACKSPACE)
        
        driver.execute_script("""
            var element = arguments[0];
            var html = arguments[1];
            element.focus();
            document.execCommand('insertHTML', false, html);
        """, active_element, text_html)
        time.sleep(5)

        post_btn = driver.find_element(By.XPATH, "//div[@aria-label='Post' or @aria-label='Publicar']")
        post_btn.click()
        print("🚀 ¡Publicación exitosa!")
        time.sleep(10)
        return True
    except Exception as e:
        print(f"❌ Fallo al publicar: {e}")
        return False
    finally:
        driver.quit()

# --- BUCLE PRINCIPAL ---
def wait_until_next_slot():
    now = datetime.now()
    current_hour = now.hour
    next_slot = None
    for slot in SCHEDULE_HOURS:
        if slot > current_hour:
            next_slot = slot
            break
    if next_slot is None:
        target_time = now.replace(day=now.day+1, hour=SCHEDULE_HOURS[0], minute=0, second=0)
    else:
        target_time = now.replace(hour=next_slot, minute=0, second=0)
    
    delta = target_time - now
    print(f"\n💤 Próximo post a las: {target_time.strftime('%H:%M')}")
    time.sleep(delta.total_seconds())

def get_best_fresh_article():
    print("📡 Buscando noticias frescas (últimas 24h)...")
    posted_links = load_history()
    cutoff_time = datetime.now().astimezone() - timedelta(hours=HOURS_BACK)

    for source_name, url, source_type in FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if entry.link in posted_links: continue
                if hasattr(entry, 'published'):
                    try:
                        article_date = date_parser.parse(entry.published)
                        if article_date.tzinfo is None: article_date = article_date.astimezone()
                        if article_date < cutoff_time: continue 
                    except: pass
                full_text = (entry.title + " " + entry.get('summary', '')).lower()
                if any(k in full_text for k in KEYWORDS):
                    return entry
        except: pass
    return None

if __name__ == "__main__":
    print("🚀 AGENTE A TU ALCANCE INICIADO (24/7)")
    while True:
        wait_until_next_slot()
        article = get_best_fresh_article()
        if article:
            summary_html = get_gemini_summary(article.title, article.link)
            if post_to_facebook(summary_html, article.link):
                save_to_history(article.link)
        else:
            print("😴 No se encontraron noticias nuevas en este ciclo.")
        time.sleep(60)