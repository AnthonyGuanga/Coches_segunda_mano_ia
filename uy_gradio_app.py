import json
import types
import sys
from pathlib import Path
from typing import Any, Dict
import httpx
import gradio as gr


def _ensure_uy_tools_module() -> types.ModuleType:
    """Ensure a module named `uy_tools` is importable.
    If a real Python module is not present, try to load `uy_tools.ipynb` and
    execute its definition cells into a module object.
    """
    try:
        import uy_tools  
        return uy_tools
    except Exception:
        nbpath = Path(__file__).parent / 'uy_tools.ipynb'
        if not nbpath.exists():
            raise
        nb = json.loads(nbpath.read_text())
        code_cells = [c for c in nb.get('cells', []) if c.get('cell_type') == 'code']
        ns: Dict[str, Any] = {}
        for c in code_cells:
            src = ''.join(c.get('source', []))
            if src.strip().startswith('# Ej') or src.strip().startswith('print('):
                continue
            try:
                exec(compile(src, '<uy_tools_ipynb>', 'exec'), ns)
            except Exception:

                pass
        mod = types.ModuleType('uy_tools')
        for k, v in ns.items():
            setattr(mod, k, v)
        sys.modules['uy_tools'] = mod
        return mod


def build_demo_extended():

    tools = _ensure_uy_tools_module()

    get_weather_on_date = getattr(tools, 'get_weather_on_date', lambda *a, **k: {'success': False, 'error': 'get_weather_on_date missing'})
    convert_currency = getattr(tools, 'convert_currency', lambda *a, **k: {'success': False, 'error': 'convert_currency missing'})
    rag_query = getattr(tools, 'rag_query', lambda *a, **k: {'success': False, 'error': 'rag_query missing'})
    assess_testability = getattr(tools, 'assess_testability', lambda *a, **k: {'success': False, 'error': 'assess_testability missing'})

    def weather_on_date_ui(lat: float, lon: float, date_str: str) -> Dict[str, Any]:
        return get_weather_on_date(lat, lon, date_str)

    def _format_currency_output(resp, amount, frm, to):
        try:
            if not resp or not resp.get('success'):
                return f"Conversión no disponible: {resp.get('error') if resp else 'error en la consulta'}"
            result = resp.get('result')
            if result is None:
                return f"No disponible: no se obtuvo tasa para {frm} → {to}"
            try:
                val = float(result)
                return f"{float(amount):,.2f} {frm} = {val:,.2f} {to}"
            except Exception:
                return f"{amount} {frm} = {result} {to}"
        except Exception as e:
            return f"Error al formatear la conversión: {e}"

    def convert_ui(amount, frm, to, date_str=None):
        try:
            frm_code = (frm or '').strip().upper()
            to_code = (to or '').strip().upper()
            if not frm_code or not to_code:
                return 'Por favor especifica códigos de moneda válidos (ej: EUR, USD).'
            try:
                amt = float(amount)
            except Exception:
                return 'Por favor indica un importe numérico válido.'

            resp = convert_currency(amt, frm_code, to_code, date=None)

            if resp and resp.get('success') and resp.get('result') is not None:
                return _format_currency_output(resp, amt, frm_code, to_code)

            try:
                url = 'https://api.exchangerate.host/convert'
                params = {'from': frm_code, 'to': to_code, 'amount': amt}
                r = httpx.get(url, params=params, timeout=6.0)
                r.raise_for_status()
                jd = r.json()
                if jd.get('success') and 'result' in jd and jd.get('result') is not None:
                    resp2 = {'success': True, 'query': {'amount': amt, 'from': frm_code, 'to': to_code}, 'result': jd.get('result')}
                    return _format_currency_output(resp2, amt, frm_code, to_code)

            except Exception:
                pass
            try:

                url2 = 'https://api.frankfurter.app/latest'
                params2 = {'amount': amt, 'from': frm_code, 'to': to_code}
                r2 = httpx.get(url2, params=params2, timeout=6.0)
                r2.raise_for_status()
                jd2 = r2.json()
                rates = jd2.get('rates') or {}
                if to_code in rates and rates[to_code] is not None:
                    # frankfurter returns the converted amount in rates[to_code] when amount is provided
                    resp2 = {'success': True, 'query': {'amount': amt, 'from': frm_code, 'to': to_code}, 'result': rates[to_code]}
                    return _format_currency_output(resp2, amt, frm_code, to_code)
            except Exception:
                pass
            except Exception:
                # ignore fallback errors, fall through to no-available message
                pass

            return f'No disponible: no se obtuvo tasa para {frm_code} → {to_code}'
        except Exception as e:
            return f"Error en la conversión: {e}"

    def rag_ui(query: str):
        return rag_query(query)

    def fmt_weather_summary(res: Dict[str, Any]) -> str:
        if not res.get('success'):
            return f"Error: {res.get('error')}"
        s = res.get('summary', {})
        parts = [f"### Clima para {res.get('date','-')}"]
        parts.append(f"- Temperatura mínima: **{s.get('temp_min','-')} °C")
        parts.append(f"- Temperatura máxima: **{s.get('temp_max','-')} °C")
        parts.append(f"- Temperatura media: **{round(s.get('temp_avg',0),1)} °C")
        parts.append(f"- Precipitación total: **{s.get('precip_total_mm',0)} mm")
        parts.append(f"- Viento medio: **{round(s.get('wind_avg_kmh',0),1)} km/h")
        return "\n".join(parts)

    def fmt_rag(res: Dict[str, Any]) -> str:
        if not res.get('success'):

            hint = res.get('hint') or ''
            http_err = res.get('http_error') or ''
            py_err = res.get('python_error') or ''
            return f"**RAG no disponible localmente**\n- {hint}\n- HTTP: {http_err}\n- Python: {py_err}"

        r = res.get('response')
        if isinstance(r, dict):
            return "### Respuesta RAG:\n" + json.dumps(r, indent=2, ensure_ascii=False)
        return f"### Respuesta RAG:\n{r}"

    with gr.Blocks(title='Asistente Coches - Herramientas') as demo:
        gr.Markdown("""
        # Asistente para coches de segunda mano
        Usa las pestañas para consultar clima, conversiones de moneda, evaluación de condiciones para pruebas y preguntar al RAG.
        """)
        # Provincias de España (capitales) - lat, lon aproximados
        provinces = {
            'A Coruña': (43.3623, -8.4115),
            'Álava': (42.8467, -2.6727),
            'Albacete': (38.9943, -1.8564),
            'Alicante': (38.3452, -0.4810),
            'Almería': (36.8340, -2.4637),
            'Asturias': (43.3609, -5.8448),
            'Ávila': (40.6565, -4.7017),
            'Badajoz': (38.8794, -6.9707),
            'Barcelona': (41.3851, 2.1734),
            'Burgos': (42.3439, -3.6969),
            'Cáceres': (39.4753, -6.3726),
            'Cádiz': (36.5167, -6.2833),
            'Cantabria': (43.4623, -3.8090),
            'Castellón': (39.9864, -0.0513),
            'Ciudad Real': (38.9862, -3.9275),
            'Córdoba': (37.8882, -4.7794),
            'Cuenca': (40.0704, -2.1374),
            'Girona': (41.9794, 2.8214),
            'Granada': (37.1773, -3.5986),
            'Guadalajara': (40.6333, -3.1667),
            'Gipuzkoa': (43.3209, -1.9819),
            'Huelva': (37.2614, -6.9447),
            'Huesca': (42.1401, -0.4089),
            'Jaén': (37.7796, -3.7837),
            'León': (42.5987, -5.5671),
            'Lleida': (41.6176, 0.6200),
            'Lugo': (43.0125, -7.5550),
            'Madrid': (40.4168, -3.7038),
            'Málaga': (36.7213, -4.4214),
            'Murcia': (37.9922, -1.1307),
            'Navarra': (42.8125, -1.6458),
            'Ourense': (42.3350, -7.8631),
            'Palencia': (42.0096, -4.5286),
            'Las Palmas': (28.1235, -15.4363),
            'Pontevedra': (42.4310, -8.6444),
            'La Rioja': (42.4626, -2.4458),
            'Salamanca': (40.9701, -5.6635),
            'Santa Cruz de Tenerife': (28.4636, -16.2518),
            'Segovia': (40.9481, -4.1186),
            'Sevilla': (37.3891, -5.9845),
            'Soria': (41.7636, -2.4685),
            'Tarragona': (41.1189, 1.2445),
            'Teruel': (40.3440, -1.1068),
            'Toledo': (39.8628, -4.0273),
            'Valencia': (39.4699, -0.3763),
            'Valladolid': (41.6523, -4.7245),
            'Vizcaya': (43.2630, -2.9350),
            'Zamora': (41.5036, -5.7445),
            'Zaragoza': (41.6488, -0.8891),
            'Ceuta': (35.8894, -5.3213),
            'Melilla': (35.1740, -2.9150)
        }
        currencies = [
            'EUR','USD','GBP','JPY','CHF','CAD','AUD','INR','CNY','MXN',
            'BRL','ARS','PEN','CLP','NOK','SEK','DKK','RUB','ZAR','TRY',
            'PLN','HUF','ILS','KRW','SGD','HKD','MYR','IDR','THB','PHP'
        ]

        with gr.Tabs():
            with gr.TabItem('Conversión'):
                gr.Markdown('### Conversión de moneda')
                amt = gr.Number(value=1000, label='Importe')
                frm = gr.Dropdown(choices=currencies, value='EUR', label='De (moneda)')
                to = gr.Dropdown(choices=currencies, value='USD', label='A (moneda)')
                btnc = gr.Button('Convertir')
                outc = gr.Markdown(label='Resultado')

                btnc.click(fn=convert_ui, inputs=[amt, frm, to], outputs=outc)

            with gr.TabItem('Clima (provincia + fecha)'):
                gr.Markdown('### Selecciona provincia de España y fecha')
                prov = gr.Dropdown(choices=list(provinces.keys()), value='Madrid', label='Provincia')
                date_d = gr.Textbox(value='2025-10-16', label='Fecha (YYYY-MM-DD)')
                btnd = gr.Button('Obtener clima')
                outd = gr.Markdown(label='Clima histórico')

                def _prov_to_latlon(prov_name: str):
                    return provinces.get(prov_name, provinces['Madrid'])

                def _weather_by_province(prov_name: str, date_str: str):
                    lat, lon = _prov_to_latlon(prov_name)
                    res = weather_on_date_ui(lat, lon, date_str)

                    if not res or not res.get('success'):
                        err = res.get('error') if isinstance(res, dict) else 'No se pudo obtener datos para esa fecha.'
                        return f"Error: {err}"
                    summary = res.get('summary')
                    if not summary:
                        return 'Error: No hay datos meteorológicos disponibles para la fecha seleccionada.'

                    # Build weather markdown
                    weather_md = fmt_weather_summary(res)

                    # Also call assess_testability to provide recommendation + reasons
                    try:
                        assess_res = assess_testability(date_str, lat, lon)
                    except Exception as e:
                        assess_res = { 'success': False, 'error': str(e) }

                    if assess_res.get('success'):
                        # Map recommendations to Spanish
                        rec_en = assess_res.get('recommendation', '')
                        rec_map = {'OK': 'Bien', 'Not ideal': 'No recomendable', 'Caution': 'Precaución'}
                        rec = rec_map.get(rec_en, rec_en)
                        reasons = assess_res.get('reasons', []) or []

                        # Translate some common reason patterns to Spanish
                        def translate_reason(r: str) -> str:
                            r = r.replace('Precipitation total', 'Precipitación total')
                            r = r.replace('not ideal for testing', '— no ideal para probar')
                            r = r.replace('High wind average', 'Viento medio alto')
                            r = r.replace('— caution', '— precaución')
                            r = r.replace('Low temperature', 'Baja temperatura')
                            r = r.replace('High temperature', 'Alta temperatura')
                            # simple unit translations
                            r = r.replace('mm', 'mm')
                            r = r.replace('km/h', 'km/h')
                            return r

                        parts = [weather_md, '\n---\n', f'### Recomendación: **{rec}**']
                        if reasons:
                            parts.append('\n'.join([f'- {translate_reason(r)}' for r in reasons]))
                        return "\n\n".join(parts)
                    else:
                        hint = (assess_res.get('error') or '').lower()
                        # detect common archive/date errors and return a friendly Spanish message
                        if any(k in hint for k in ('400', 'bad request', 'archive', 'out of range', 'date')):
                            return weather_md + "\n\n**Recomendación:** No hay datos meteorológicos para la fecha seleccionada (posible fecha fuera de rango o no disponible en el archivo histórico). Prueba con otra fecha."
                        return weather_md + f"\n\n**Recomendación:** No se pudo evaluar: {assess_res.get('error') or 'Error desconocido'}"

                btnd.click(fn=_weather_by_province, inputs=[prov, date_d], outputs=outd)

            with gr.TabItem('Preguntar al RAG'):
                gr.Markdown('### Pregunta al RAG')
                q = gr.Textbox(value='¿Historial de mantenimiento para VW Golf 2012?', label='Pregunta', placeholder='Escribe tu pregunta...')
                btnr = gr.Button('Preguntar')
                outr = gr.Markdown(label='Respuesta RAG')
                btnr.click(fn=lambda s: fmt_rag(rag_ui(s)), inputs=q, outputs=outr)

    globals()['__convert_ui'] = convert_ui
    globals()['__fmt_weather_summary'] = fmt_weather_summary
    globals()['__fmt_rag'] = fmt_rag

    return demo
