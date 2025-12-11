from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

START_URL = "https://www.autofesa.com/coches-segunda-mano"

def scrape_autofesa_sync():

    resultados = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"🔗 Accediendo a: {START_URL}")
        page.goto(START_URL)

        # Cookies
        try:
            page.click("#onetrust-accept-btn-handler", timeout=3000)
            print("✓ Cookies aceptadas")
        except:
            print("ℹ️ No apareció banner de cookies")

        page_num = 1

        while True:
            print(f"\n📄 Scrapear página {page_num}")
            page.wait_for_selector(".vehicle-list__item")

            html = page.content()
            soup = BeautifulSoup(html, "html.parser")

            cars = soup.select(".vehicle-list__item")
            print(f"🚗 {len(cars)} coches encontrados")

            for car in cars:
                titulo = car.select_one(".vehicle-card__title")
                precio = (
                    car.select_one(".vehicle-card__price") or
                    car.select_one(".vehicle-card__price--soldout") or
                    car.select_one(".vehicle-card__price span")
                )
                link = car.select_one("a")
                features = car.select(".vehicle-card__features .list .item")

                resultados.append({
                    "Modelo": titulo.get_text(strip=True) if titulo else "Sin título",
                    "Precio": precio.get_text(strip=True) if precio else "Precio no disponible",
                    "Link": link["href"] if link else "Sin enlace",
                    "Información": " | ".join(f.get_text(strip=True) for f in features)
                            if features else "Sin info"
                })

            # Paginar
            try:
                next_button = page.wait_for_selector(
                    'a.page-link[title="Página siguiente"]',
                    timeout=3000
                )
                next_button.click()
                page_num += 1
            except:
                print("🏁 Última página.")
                break

        browser.close()
        return resultados
