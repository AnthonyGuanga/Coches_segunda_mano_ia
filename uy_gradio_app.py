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
    check_vehicle_safety = getattr(tools, 'check_vehicle_safety', None)
    if check_vehicle_safety is None:

        nbpath = Path(__file__).parent / 'uy_tools.ipynb'
        if nbpath.exists():
            nb = json.loads(nbpath.read_text())
            code_cells = [c for c in nb.get('cells', []) if c.get('cell_type') == 'code']
            target_src = None
            for c in code_cells:
                src = ''.join(c.get('source', []))
                if 'def check_vehicle_safety' in src:
                    target_src = src
                    break
            if target_src:

                from typing import Dict, Any, List, Optional
                safe_globals = {
                    '__name__': 'uy_tools_loaded_partial',
                    'httpx': httpx,
                    'Dict': Dict,
                    'Any': Any,
                    'List': List,
                    'Optional': Optional,
                }

                try:
                    exec(compile(target_src, '<uy_tools_check_vehicle>', 'exec'), safe_globals)
                except Exception:

                    pass
                if 'check_vehicle_safety' in safe_globals:
                    check_vehicle_safety = safe_globals['check_vehicle_safety']

                    try:
                        setattr(tools, 'check_vehicle_safety', check_vehicle_safety)
                    except Exception:
                        pass

    if not callable(check_vehicle_safety):

        check_vehicle_safety = lambda *a, **k: {'success': False, 'error': 'check_vehicle_safety missing'}

    def weather_on_date_ui(lat: float, lon: float, date_str: str) -> Dict[str, Any]:
        return get_weather_on_date(lat, lon, date_str)

    def _forecast_for_date(lat: float, lon: float, date_str: str) -> Dict[str, Any]:
        """Fetch forecast data for a future date using Open-Meteo forecast API and return same summary shape as archive."""
        try:

            d = None
            try:
                from datetime import datetime as _dt
                d = _dt.fromisoformat(date_str).date() if isinstance(date_str, str) else date_str
            except Exception:
                return { 'success': False, 'error': 'Formato de fecha inválido' }

            start = d.isoformat()
            end = d.isoformat()
            url = 'https://api.open-meteo.com/v1/forecast'
            params = {
                'latitude': lat,
                'longitude': lon,
                'start_date': start,
                'end_date': end,
                'hourly': 'temperature_2m,precipitation,windspeed_10m',
                'timezone': 'UTC'
            }
            r = httpx.get(url, params=params, timeout=15.0)
            r.raise_for_status()
            data = r.json()
            hourly = data.get('hourly', {})
            temps = hourly.get('temperature_2m', [])
            prec = hourly.get('precipitation', [])
            wind = hourly.get('windspeed_10m', [])
            summary = {}
            if temps:
                summary['temp_min'] = min(temps)
                summary['temp_max'] = max(temps)
                summary['temp_avg'] = sum(temps)/len(temps)
            if prec:
                summary['precip_total_mm'] = sum(prec)
            if wind:
                summary['wind_avg_kmh'] = (sum(wind)/len(wind))
            return { 'success': True, 'date': start, 'summary': summary, 'raw': data }
        except Exception as e:
            return { 'success': False, 'error': str(e) }

    def _assess_summary_testability(summary: Dict[str, Any], date_str: str) -> Dict[str, Any]:
        """Evaluate testability from a weather summary dict (same heuristic as assess_testability)."""
        reasons = []
        score = 0
        prec = summary.get('precip_total_mm', 0)
        if prec and prec > 0.5:
            reasons.append(f'Precipitación total {prec} mm — no ideal para probar')
            score -= 2
        wind = summary.get('wind_avg_kmh', 0)
        if wind and wind > 40:
            reasons.append(f'Viento medio {wind:.1f} km/h — precaución')
            score -= 1
        tmin = summary.get('temp_min')
        tmax = summary.get('temp_max')
        if tmin is not None and tmin < -5:
            reasons.append(f'Baja temperatura {tmin}°C — puede afectar arranque/batería')
            score -= 1
        if tmax is not None and tmax > 40:
            reasons.append(f'Alta temperatura {tmax}°C — precaución con motores/AC')
            score -= 1
        recommendation = 'Bien' if score >= 0 and not reasons else 'No recomendable' if score < 0 else 'Precaución'
        return {'success': True, 'date': date_str, 'recommendation': recommendation, 'reasons': reasons, 'summary': summary}

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

                    resp2 = {'success': True, 'query': {'amount': amt, 'from': frm_code, 'to': to_code}, 'result': rates[to_code]}
                    return _format_currency_output(resp2, amt, frm_code, to_code)
            except Exception:
                pass
            except Exception:

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

                    from datetime import datetime, date as _date
                    try:
                        d = datetime.fromisoformat(date_str).date()
                    except Exception:
                        return 'Error: formato de fecha inválido. Usa YYYY-MM-DD.'

                    today = _date.today()
                    if d > today:

                        res = _forecast_for_date(lat, lon, date_str)

                        if res.get('success') and res.get('summary'):
                            assess_res = _assess_summary_testability(res.get('summary'), res.get('date'))
                        else:
                            assess_res = { 'success': False, 'error': res.get('error') }
                    else:
                        res = weather_on_date_ui(lat, lon, date_str)
                        assess_res = None

                    if not res or not res.get('success'):
                        err = res.get('error') if isinstance(res, dict) else 'No se pudo obtener datos para esa fecha.'
                        return f"Error: {err}"
                    summary = res.get('summary')
                    if not summary:
                        return 'Error: No hay datos meteorológicos disponibles para la fecha seleccionada.'

                    weather_md = fmt_weather_summary(res)

                    if assess_res is None:
                        try:
                            assess_res = assess_testability(date_str, lat, lon)
                        except Exception as e:
                            assess_res = { 'success': False, 'error': str(e) }

                    if assess_res.get('success'):
                        rec_en = assess_res.get('recommendation', '')
                        rec_map = {'OK': 'Bien', 'Not ideal': 'No recomendable', 'Caution': 'Precaución'}
                        rec = rec_map.get(rec_en, rec_en)
                        reasons = assess_res.get('reasons', []) or []
                        def translate_reason(r: str) -> str:
                            r = r.replace('Precipitation total', 'Precipitación total')
                            r = r.replace('not ideal for testing', '— no ideal para probar')
                            r = r.replace('High wind average', 'Viento medio alto')
                            r = r.replace('— caution', '— precaución')
                            r = r.replace('Low temperature', 'Baja temperatura')
                            r = r.replace('High temperature', 'Alta temperatura')
                            r = r.replace('mm', 'mm')
                            r = r.replace('km/h', 'km/h')
                            return r

                        parts = [weather_md, '\n---\n', f'### Recomendación: **{rec}**']
                        if reasons:
                            parts.append('\n'.join([f'- {translate_reason(r)}' for r in reasons]))
                        return "\n\n".join(parts)
                    else:
                        hint = (assess_res.get('error') or '').lower()

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

            with gr.TabItem('Seguridad / Recalls'):
                gr.Markdown('### Comprobar recalls y calificaciones de seguridad (NHTSA)')
                popular_makes = ['Honda', 'Toyota', 'Ford', 'Volkswagen', 'BMW', 'Nissan']
                make_in = gr.Dropdown(choices=popular_makes, value=popular_makes[0], label='Marca (make)')
                model_in = gr.Dropdown(choices=['(elige marca primero)'], value='(elige marca primero)', label='Modelo (model)')
                year_in = gr.Dropdown(choices=['(elige modelo primero)'], value='(elige modelo primero)', label='Año (year)')
                vin_in = gr.Textbox(value='', label='VIN (opcional)', placeholder='Opcional: VIN completo')
                btns = gr.Button('Comprobar seguridad')
                outsafety = gr.Markdown(label='Resultado Seguridad')

                def _nhtsa_get(path: str, params: dict):
                    try:
                        url = f'https://api.nhtsa.gov/{path}'
                        r = httpx.get(url, params=params, timeout=8.0)
                        r.raise_for_status()
                        return { 'success': True, 'data': r.json() }
                    except Exception as e:
                        return { 'success': False, 'error': str(e) }

                def _fetch_models_for_make(make: str):
                    res = _nhtsa_get('vehicles/GetModelsForMake', {'make': make})
                    if res.get('success'):
                        data = res['data']
                        results = data.get('Results') or []
                        models = sorted({r.get('Model_Name') for r in results if r.get('Model_Name')})
                        if models:
                            return models

                    fallback = {
                        'Honda': ['Civic','Accord','CR-V'],
                        'Toyota': ['Corolla','Camry','RAV4'],
                        'Ford': ['Focus','Fiesta','F-150'],
                        'Volkswagen': ['Golf','Passat','Polo'],
                        'BMW': ['3 Series','5 Series'],
                        'Nissan': ['Sentra','Altima']
                    }
                    return fallback.get(make, [])

                def _fetch_years_for_make_model(make: str, model: str):

                    years = []
                    import datetime
                    current = datetime.date.today().year
                    for y in range(current, current-30, -1):
                        try:
                            url = 'https://api.nhtsa.gov/recalls/recallsByVehicle'
                            r = httpx.get(url, params={'make': make, 'model': model, 'modelYear': y}, timeout=6.0)
                            if r.status_code == 200:
                                years.append(str(y))
                        except Exception:

                            pass
                    if years:
                        return years
                    return [str(y) for y in range(current, current-15, -1)]

                def on_make_change(selected_make):
                    models = _fetch_models_for_make(selected_make)
                    if not models:
                        return gr.update(choices=['(no se encontraron modelos)'], value='(no se encontraron modelos)')
                    return gr.update(choices=models, value=models[0])

                def on_model_change(selected_model, selected_make):
                    if not selected_model or selected_model.startswith('('):
                        return gr.update(choices=['(elige modelo primero)'], value='(elige modelo primero)')
                    years = _fetch_years_for_make_model(selected_make, selected_model)
                    if not years:
                        return gr.update(choices=['(no se encontraron años)'], value='(no se encontraron años)')
                    return gr.update(choices=years, value=years[0])

                make_in.change(fn=on_make_change, inputs=[make_in], outputs=[model_in])
                model_in.change(fn=on_model_change, inputs=[model_in, make_in], outputs=[year_in])

                def fmt_vehicle_safety(resp: Dict[str, Any]) -> str:
                    """Formatea la respuesta de check_vehicle_safety en Markdown en español."""
                    def _stars(val):
                        try:
                            n = int(float(val))
                            if n <= 0:
                                return str(val)
                            n = min(max(n, 0), 5)
                            return '★' * n + f' ({n}/5)'
                        except Exception:
                            return str(val)

                    if not isinstance(resp, dict):
                        return 'Error: respuesta inesperada del proceso de verificación.'

                    if not resp.get('success'):

                        err = resp.get('error') or resp.get('recalls_error') or 'desconocido'
                        return f"Error al consultar seguridad: {err}"

                    data = resp.get('data', {})
                    make = data.get('make') or ''
                    model = data.get('model') or ''
                    year = data.get('year') or ''

                    parts = [f"### Seguridad: {make} {model} ({year})"]
                    parts.append(f"- Recalls totales: **{data.get('total_recalls',0)}**")

                    recalls = data.get('recalls', []) or []
                    if recalls:
                        parts.append('\n**Lista de recalls (resumen):**')
                        for r in recalls[:10]:
                            cn = r.get('campaign_number') or r.get('CampaignNumber') or '-'
                            comp = r.get('component') or r.get('Component') or '-'
                            summ = (r.get('summary') or r.get('Summary') or r.get('description') or '')
                            remedy = r.get('remedy') or r.get('Remedy') or '-'
                            date = r.get('date') or r.get('ReportReceivedDate') or '-'

                            parts.append(f"- **Campaña:** {cn} — Fecha: {date}\n  - Componente: {comp}\n  - Resumen: {summ}\n  - Remedio: {remedy}")
                    else:
                        parts.append('- No se encontraron recalls para la combinación proporcionada.')

                    sr = data.get('safety_ratings') or {}
                    if sr:
                        parts.append('\n**Calificaciones de seguridad (NHTSA):**')
                        overall = sr.get('overall_rating') or sr.get('OverallRating')
                        frontal = sr.get('frontal_crash') or sr.get('frontal') or sr.get('FrontalCrash')
                        side = sr.get('side_crash') or sr.get('side') or sr.get('SideCrash')
                        rollover = sr.get('rollover') or sr.get('rollover_rating') or sr.get('Rollover')
                        parts.append(f"- Evaluación global: **{_stars(overall)}**")
                        parts.append(f"- Frontal: {_stars(frontal)}, Lateral: {_stars(side)}, Volcamiento: {_stars(rollover)}")
                    else:
                        parts.append('- No hay calificaciones de seguridad disponibles.')

                    recs = resp.get('recommendations') or []
                    if recs:
                        parts.append('\n**Recomendaciones:**')
                        for r in recs:
                            rr = str(r)
                            rr = rr.replace('Recall', 'Recall').replace('inspect', 'inspeccionar')
                            parts.append(f'- {rr}')

                    if resp.get('recalls_error'):
                        parts.append(f"\n_Nota: hubo un problema consultando recalls: {resp.get('recalls_error')}_")

                    return "\n\n".join(parts)

                def vehicle_safety_ui(make, model, year, vin):
                    """UI wrapper: normalize inputs and call the underlying tool."""
                    try:
                        mk = (make or '').strip()
                        md = (model or '').strip()
                        if not mk or not md:
                            return 'Por favor especifica marca y modelo.'

                        common_map = {
                            'Onda': 'Honda',
                            'Toyta': 'Toyota',
                            'Bmw': 'BMW',
                            'Vw': 'Volkswagen',
                            'Vokswagen': 'Volkswagen'
                        }
                        if mk in common_map:
                            mk = common_map[mk]
                        mk = ' '.join([p.capitalize() for p in mk.split()])
                        md = ' '.join([p.capitalize() for p in md.split()])

                        try:
                            yr = int(year) if year is not None and str(year).strip() != '' else None
                        except Exception:
                            return 'Año inválido. Indica un número entero (ej: 2015).'

                        vin_n = None
                        if vin:
                            import re
                            vin_n = re.sub(r'[^A-Za-z0-9]', '', str(vin)).upper() or None

                        resp = check_vehicle_safety(mk, md, yr, vin_n)
                        return fmt_vehicle_safety(resp)
                    except Exception as e:
                        return f'Error interno: {e}'

                btns.click(fn=vehicle_safety_ui, inputs=[make_in, model_in, year_in, vin_in], outputs=outsafety)

    globals()['__convert_ui'] = convert_ui
    globals()['__fmt_weather_summary'] = fmt_weather_summary
    globals()['__fmt_rag'] = fmt_rag

    return demo
