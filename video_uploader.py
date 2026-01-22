import time
import os
from google import genai
from google.genai import types
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURACIÓN ---
API_KEY = "AIzaSyD6cujWwG67kOQuVRzZ0cRDi3_0DsLWYHs" 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_FILE = os.path.join(BASE_DIR, "Morning_Briefing_Pro.mp4")
CHROME_PROFILE = os.path.abspath(os.path.join(BASE_DIR, "..", "ChromeProfile"))

# Usamos 'gemini-1.5-flash'
client = genai.Client(api_key=API_KEY)

def get_video_description():
    print("🧠 Gemini redactando descripción...")
    prompt = "Eres el presentador de A Tu Alcance. Escribe un título llamativo en MAYÚSCULAS y una descripción de 2 oraciones para el resumen de noticias de hoy. Usa emojis."
    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash', 
            contents=prompt
        )
        return response.text.replace("**", "")
    except Exception as e:
        print(f"⚠️ Error Gemini: {e}")
        return "🔴 NOTICIERO MATUTINO: Resumen de las noticias más importantes de hoy en Puerto Rico."

def click_element_robust(driver, xpaths):
    for xpath in xpaths:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            for btn in elements:
                if btn.is_displayed():
                    btn.click()
                    return True
        except: pass
    return False

def close_popups(driver):
    """Detecta y cierra ventanas emergentes de WhatsApp, Instagram, etc."""
    popup_xpaths = [
        "//span[text()='Not now']", "//div[@aria-label='Not now']", "//span[text()='Ahora no']",
        "//span[text()='Skip']", "//div[@aria-label='Close']", "//div[@aria-label='Cerrar']",
        "//div[text()='Not now']"
    ]
    if click_element_robust(driver, popup_xpaths):
        print("🛡️ ¡Popup detectado y cerrado!")
        time.sleep(2)
        return True
    return False

def upload_to_facebook():
    if not os.path.exists(VIDEO_FILE):
        print(f"❌ Error: No se encontró el video en {VIDEO_FILE}")
        return False

    print(f"📂 Usando perfil de Chrome en: {CHROME_PROFILE}")
    chrome_options = Options()
    chrome_options.add_argument(f"user-data-dir={CHROME_PROFILE}")
    chrome_options.add_argument("--disable-notifications")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.maximize_window()

    try:
        print("🌍 Entrando a Facebook...")
        driver.get("https://www.facebook.com")
        time.sleep(8)

        # 1. Descripción
        description = get_video_description()
        
        # 2. Subir Video
        print("📁 Iniciando carga del video...")
        try:
            video_input = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='file' and contains(@accept, 'video')]"))
            )
            video_input.send_keys(VIDEO_FILE)
        except:
            print("⚠️ No encontré el botón de subida.")
            return False
        
        print("⏳ Esperando carga inicial (15s)...")
        time.sleep(15) 

        # 3. Escribir Descripción
        print("✍️ Intentando escribir descripción...")
        try:
            text_box = driver.switch_to.active_element
            text_box.send_keys(description)
        except: pass
        
        time.sleep(5)

        # 4. BUCLE "TANQUE" MEJORADO (Anti-Popups)
        max_attempts = 15 
        for i in range(max_attempts):
            print(f"🔄 Navegando asistente (Paso {i+1}/{max_attempts})...")
            time.sleep(4) 
            
            # A. PRIMERO: MATAR POPUPS (WhatsApp, etc)
            close_popups(driver)

            # B. BUSCAR BOTÓN FINAL "PUBLICAR"
            post_xpaths = [
                "//div[@aria-label='Post']", "//div[@aria-label='Publicar']", 
                "//div[@aria-label='Share']", "//span[text()='Post']", 
                "//span[text()='Publicar']"
            ]
            if click_element_robust(driver, post_xpaths):
                print("🚀 ¡BOTÓN PUBLICAR DETECTADO Y CLICKEADO!")
                print("⏳ Esperando 45s para confirmar subida...")
                time.sleep(45) 
                return True

            # C. BUSCAR BOTÓN "SIGUIENTE" (NEXT)
            next_xpaths = [
                "//div[@aria-label='Next']", "//div[@aria-label='Siguiente']",
                "//span[text()='Next']", "//span[text()='Siguiente']",
                "//div[text()='Next']"
            ]
            if click_element_robust(driver, next_xpaths):
                print("➡️ Botón 'Siguiente' clickeado. Avanzando pantalla...")
                time.sleep(3) 
                continue

            print("⏳ Procesando...")
        
        print("❌ Se acabaron los intentos. No pude finalizar la publicación.")
        return False

    except Exception as e:
        print(f"❌ Error crítico en la subida: {e}")
        return False
    finally:
        print("🔒 Cerrando navegador...")
        driver.quit()

if __name__ == "__main__":
    upload_to_facebook()