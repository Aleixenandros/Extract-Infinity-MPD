#!/usr/bin/env python3
import argparse
import json
import re
import time
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# === CONFIGURACIÓN POR DEFECTO ===
DEFAULT_WAIT = 30
DEFAULT_HEADLESS = False
DEFAULT_PREFER_DOMAIN = "vbd.mediasetinfinity.es"

# === SCRIPT BLOQUEADOR DE ANUNCIOS ===
BLOCK_SCRIPT = """
let blockedDomains = [
    'doubleclick.net','googlesyndication.com','googletagservices.com',
    'adservice.google.com','imasdk.googleapis.com','video-ads.mediaset.es',
    'ads.mediaset.es','googlevideo.com','rr3---sn-8vq54voxn25po-n89l.googlevideo.com',
    'vast','preroll','adserver','pubads'
];
let observer = new MutationObserver((mutations, observer) => {
    for (let mutation of mutations) {
        for (let node of mutation.addedNodes) {
            if (node.nodeType !== 1) continue;
            if (node.tagName === 'IFRAME' && blockedDomains.some(domain => node.src?.includes(domain))) {
                node.remove(); continue;
            }
            if (node.tagName === 'SCRIPT' && blockedDomains.some(domain => node.src?.includes(domain) || node.innerHTML?.includes(domain))) {
                node.remove(); continue;
            }
            let sources = node.tagName === 'VIDEO' ? [node] : node.querySelectorAll('video, source, track');
            for (let source of sources) {
                let url = source.src || source.getAttribute('src');
                if (!url) continue;
                let parsed = new URL(url, window.location.href);
                if (blockedDomains.some(domain => parsed.hostname.includes(domain) || url.includes(domain))) {
                    source.src = '';
                    source.removeAttribute('src');
                    if (source.parentNode) source.parentNode.removeChild(source);
                }
            }
        }
    }
});
observer.observe(document, { childList: true, subtree: true });
document.querySelectorAll('video').forEach(v => v.pause());
"""

def mpd_to_m3u8(url: str) -> str:
    return (url
            .replace("mpd-cenc.ism/web.mpd", "main.ism/picky.m3u8")
            .replace("web.mpd", "picky.m3u8"))

def accept_cookies(driver):
    try:
        primary_selector = '#didomi-notice-agree-button'
        fallback_selectors = [
            'button.accept-cookies','button.cookie-accept','a#cookie-accept',
            'button[aria-label*="accept"]','button[data-testid="cookie-accept"]',
            'button[class*="accept"]','button[id*="accept"]','a[class*="accept"]'
        ]
        try:
            element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, primary_selector))
            )
            driver.execute_script("arguments[0].click();", element)
            time.sleep(2)
            return True
        except Exception:
            pass

        for selector in fallback_selectors:
            try:
                element = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                driver.execute_script("arguments[0].click();", element)
                time.sleep(2)
                return True
            except Exception:
                continue

        js_accept = """
        let buttons = document.querySelectorAll('button, a');
        for (let btn of buttons) {
            if (btn.innerText.match(/Aceptar|Accept|Consentir|Aceptar todas/i)) {
                btn.click();
                return true;
            }
        }
        return false;
        """
        if driver.execute_script(js_accept):
            time.sleep(2)
            return True
        return False
    except Exception:
        return False

def get_manifest_candidates(driver, prefer_domain=None):
    logs = driver.get_log("performance")
    candidates = []
    for entry in logs:
        msg = json.loads(entry["message"])["message"]
        if msg.get("method") != "Network.requestWillBeSent":
            continue
        url = msg.get("params", {}).get("request", {}).get("url", "")
        if not url:
            continue
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.path.endswith(".m3u8") and "main.ism/picky.m3u8" in url:
            candidates.insert(0, url)
        elif parsed.path.endswith((".mpd", ".m3u8")):
            candidates.append(url)
    if not prefer_domain:
        return candidates
    return [c for c in candidates if prefer_domain in (urlparse(c).hostname or "")]

def get_page_title(driver):
    try:
        script = """
        return document.querySelector('title')?.innerText
            || document.querySelector('meta[name="title"]')?.content
            || document.querySelector('h1')?.innerText
            || 'video';
        """
        return driver.execute_script(script)
    except Exception:
        return "video"

def sanitize_filename(filename):
    """Limpia caracteres no válidos pero mantiene espacios."""
    cleaned = re.sub(r'[\\/:*?"<>|]', '', filename)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()

def main():
    ap = argparse.ArgumentParser(description="Detecta manifiesto de Mediaset Infinity y genera comando yt-dlp listo para usar.")
    ap.add_argument("url", help="URL del reproductor de Infinity")
    args = ap.parse_args()

    # Usa la configuración por defecto
    wait = DEFAULT_WAIT
    headless = DEFAULT_HEADLESS
    prefer_domain = DEFAULT_PREFER_DOMAIN

    opts = Options()
    opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--autoplay-policy=no-user-gesture-required")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)

    try:
        driver.execute_cdp_cmd("Network.enable", {})
        driver.execute_cdp_cmd("Network.setBlockedURLs", {
            "urls": [
                "*doubleclick.net/*","*googlesyndication.com/*","*googletagservices.com/*",
                "*adservice.google.com/*","*imasdk.googleapis.com/*","*video-ads.mediaset.es/*",
                "*ads.mediaset.es/*","*googlevideo.com/videoplayback*",
                "*rr3---sn-8vq54voxn25po-n89l.googlevideo.com/*","*mediaset.es/*vast*","*mediaset.es/*preroll*"
            ]
        })
        driver.execute_script(BLOCK_SCRIPT)
        driver.get(args.url)
        accept_cookies(driver)

        start_time = time.time()
        candidates = []
        while time.time() - start_time < wait:
            candidates = get_manifest_candidates(driver, prefer_domain)
            if candidates:
                break
            time.sleep(0.5)

        if not candidates:
            print("No se encontraron candidatos a manifiesto.")
            return

        print("Candidatos encontrados:", candidates)
        title = get_page_title(driver)
        sanitized_title = sanitize_filename(title)
        manifest_url = candidates[0]

        if manifest_url.lower().endswith(".mpd"):
            manifest_url = mpd_to_m3u8(manifest_url)

        output_filename = f"{sanitized_title}.mp4"
        ytdlp_cmd = (
            f'yt-dlp --add-header "Origin: https://www.mediasetinfinity.es" '
            f'"{manifest_url}" -o "{output_filename}"'
        )
        print(ytdlp_cmd)

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
