
from typing import Any, Dict, List
import httpx
import gradio as gr


def get_weather(latitude: float, longitude: float) -> Dict[str, Any]:
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {"latitude": latitude, "longitude": longitude, "current_weather": True}
        r = httpx.get(url, params=params, timeout=10.0)
        r.raise_for_status()
        data = r.json()
        return {"success": True, "data": data.get("current_weather"), "raw": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_coin_price(coin_id: str = "bitcoin") -> Dict[str, Any]:
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": coin_id, "vs_currencies": "usd", "include_market_cap": "true"}
        r = httpx.get(url, params=params, timeout=10.0)
        r.raise_for_status()
        data = r.json()
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


def search_public_apis(query: str, max_results: int = 10) -> Dict[str, Any]:
    try:
        url = "https://raw.githubusercontent.com/public-apis/public-apis/master/README.md"
        r = httpx.get(url, timeout=10.0)
        r.raise_for_status()
        text = r.text
        matches: List[Dict[str, str]] = []
        for line in text.splitlines():
            if query.lower() in line.lower():
                matches.append({"line": line.strip()})
                if len(matches) >= max_results:
                    break
        return {"success": True, "query": query, "results": matches}
    except Exception as e:
        return {"success": False, "error": str(e)}


def weather_ui(lat: float, lon: float) -> Dict[str, Any]:
    return get_weather(lat, lon)


def coin_ui(coin_id: str) -> Dict[str, Any]:
    return get_coin_price(coin_id)


def public_apis_ui(query: str) -> Dict[str, Any]:
    return search_public_apis(query, max_results=10)


def build_demo():
    with gr.Blocks() as demo:
        with gr.Tabs():
            with gr.TabItem('Weather'):
                lat = gr.Number(value=40.4168, label='Latitude')
                lon = gr.Number(value=-3.7038, label='Longitude')
                btn = gr.Button('Get weather')
                out = gr.JSON(label='Weather')
                btn.click(fn=weather_ui, inputs=[lat, lon], outputs=out)
            with gr.TabItem('Coin'):
                coin_id = gr.Textbox(value='bitcoin', label='Coin id (coingecko)')
                btn2 = gr.Button('Get price')
                out2 = gr.JSON(label='Price')
                btn2.click(fn=coin_ui, inputs=coin_id, outputs=out2)
            with gr.TabItem('Public APIs'):
                query = gr.Textbox(value='maps', label='Query')
                btn3 = gr.Button('Search public APIs')
                out3 = gr.JSON(label='Results')
                btn3.click(fn=public_apis_ui, inputs=query, outputs=out3)
    return demo


def main():
    # Prefer an explicit app builder from uy_gradio_app if present.
    # Keep a simple fallback to the basic demo builder defined here.
    demo_obj = None
    try:
        from uy_gradio_app import build_demo_extended
        demo_obj = build_demo_extended()
    except Exception as e:
        print('Could not load uy_gradio_app.build_demo_extended():', e)
        print('Falling back to built-in demo()')
        demo_obj = build_demo()

    # Determine a local IP to display to the user (best-effort)
    import socket
    local_ip = '127.0.0.1'
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass
    print(f'Starting Gradio on http://0.0.0.0:7860 (also available at http://{local_ip}:7860)')
    # Launch and keep the server (binding to all interfaces so it's reachable on the LAN)
    demo_obj.launch(server_name='0.0.0.0', server_port=7860, share=False)


if __name__ == '__main__':
    main()
