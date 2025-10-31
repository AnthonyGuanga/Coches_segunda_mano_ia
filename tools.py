from typing import Dict, Any, Optional
from pathlib import Path
import httpx
import joblib

__all__ = [
    'get_weather_on_date', 'assess_testability',
    'tools', 'tools_dict', 'tools_description', 'format_tool_output'
]
def get_weather_on_date(latitude: float, longitude: float, date_str: str) -> Dict[str, Any]:
    try:
        url = 'https://api.open-meteo.com/v1/forecast'
        params = {
            'latitude': latitude,
            'longitude': longitude,
            'start_date': date_str,
            'end_date': date_str,
            'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max',
            'timezone': 'UTC'
        }
        r = httpx.get(url, params=params, timeout=10.0)
        r.raise_for_status()
        data = r.json()
        daily = data.get('daily', {})
        summary = {
            'temp_max': daily.get('temperature_2m_max', [None])[0],
            'temp_min': daily.get('temperature_2m_min', [None])[0],
            'precip_total_mm': daily.get('precipitation_sum', [0])[0],
            'wind_max_kmh': daily.get('windspeed_10m_max', [0])[0],
        }
        summary['wind_avg_kmh'] = summary.get('wind_max_kmh')
        return {'success': True, 'summary': summary, 'raw': data}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def _rule_based_recommendation(summary: Dict[str, Any]) -> Dict[str, Any]:
    reasons = []
    score = 0
    prec = summary.get('precip_total_mm', 0) or 0
    if prec and prec > 0.5:
        reasons.append(f'Precipitación total {prec} mm — no ideal para probar')
        score -= 2
    wind = summary.get('wind_avg_kmh', 0) or 0
    if wind and wind > 40:
        reasons.append(f'Promedio de viento alto {wind:.1f} km/h — precaución')
        score -= 1
    tmin = summary.get('temp_min')
    tmax = summary.get('temp_max')
    if tmin is not None and tmin < -5:
        reasons.append(f'Temperatura baja {tmin}°C — puede afectar batería/arranque')
        score -= 1
    if tmax is not None and tmax > 40:
        reasons.append(f'Temperatura alta {tmax}°C — precaución con motor/AC')
        score -= 1
    if score >= 0:
        rec = 'Bien'
    elif score == -1:
        rec = 'Precaución'
    else:
        rec = 'No recomendable'
    return {'recommendation': rec, 'reasons': reasons, 'score': score}


def assess_testability(day: str, latitude: float, longitude: float) -> Dict[str, Any]:
    from pandas import DataFrame
    w = get_weather_on_date(latitude, longitude, day)
    if not w.get('success'):
        return {
            'success': False,
            'error': 'No se pudo obtener el clima: ' + str(w.get('error'))
        }
    summary = w.get('summary', {})
    rb = _rule_based_recommendation(summary)
    return {
        'success': True,
        **rb,
        'summary': summary
    }



def check_vehicle_safety(make: str, model: str, year: int, vin: Optional[str] = None) -> Dict[str, Any]:
    # Mantener la implementación completa que ya tenías antes
    recalls, recalls_error, vin_info, safety_ratings = [], None, None, {}
    try:
        base_url = 'https://api.nhtsa.gov/recalls/recallsByVehicle'
        params = {'make': make, 'model': model, 'modelYear': year}
        r = httpx.get(base_url, params=params, timeout=10.0)
        r.raise_for_status()
        recalls_data = r.json() if r.text else {}
        for rec in recalls_data.get('results', []):
            recalls.append({
                'campaign_number': rec.get('NHTSACampaignNumber') or rec.get('CampaignNumber'),
                'component': rec.get('Component'),
                'summary': rec.get('Summary') or rec.get('RecallSummary'),
                'consequence': rec.get('Consequence') or rec.get('Conequence'),
                'remedy': rec.get('Remedy'),
                'date': rec.get('ReportReceivedDate') or rec.get('Date'),
            })
    except Exception as e_rec:
        recalls = []
        recalls_error = str(e_rec)

    if vin_info is None:
        vin_info = None

    try:
        safety_url = f'https://api.nhtsa.gov/SafetyRatings/vehicle/{year}/{make}/{model}'
        r = httpx.get(safety_url, timeout=10.0)
        r.raise_for_status()
        safety_json = r.json() if r.text else None
        if safety_json and isinstance(safety_json, dict):
            results = safety_json.get('results') or safety_json.get('Results')
            if results:
                first = results[0]
                safety_ratings = {
                    'overall_rating': first.get('OverallRating'),
                    'frontal_crash': first.get('FrontalCrashRating'),
                    'side_crash': first.get('SideCrashRating'),
                    'rollover': first.get('RolloverRating'),
                }
    except Exception:
        safety_ratings = {}

    vehicle_info = {
        'make': make,
        'model': model,
        'year': year,
        'recalls': recalls,
        'total_recalls': len(recalls),
        'safety_ratings': safety_ratings
    }

    recommendations = []
    if recalls:
        recommendations.append('Verificar todos los recalls abiertos antes de comprar')
        recommendations.append('Solicitar documentación de reparaciones de recalls previos')
    if safety_ratings and safety_ratings.get('overall_rating'):
        recommendations.append('Considerar calificaciones de seguridad en la decisión de compra')
    out = {'success': True, 'data': vehicle_info, 'recommendations': recommendations}
    if recalls_error:
        out['recalls_error'] = recalls_error
    return out

tools_dict = {
    "get_weather_on_date": get_weather_on_date,
    "assess_testability": assess_testability,
    "check_vehicle_safety": check_vehicle_safety
}

tools_description = """
Funciones disponibles:
1. get_weather_on_date(latitude, longitude, date_str) — clima histórico.
2. assess_testability(day, latitude, longitude) — evalúa aptitud para prueba.
3. check_vehicle_safety(make, model, year, vin=None) — recalls y seguridad.
"""

def format_tool_output(tool_name: str, result):
    if not isinstance(result, dict):
        return str(result)
    if tool_name == "convert_currency":
        if result.get("success"):
            return f"{result['result']:.2f}"
        return f"Error: {result.get('error')}"
    if tool_name == "get_weather_on_date":
        if result.get("success"):
            s = result.get("summary", {})
            return (f"Máx: {s.get('temp_max')}°C, Mín: {s.get('temp_min')}°C, "
                    f"Precip: {s.get('precip_total_mm')} mm, Viento máx: {s.get('wind_max_kmh')} km/h")
        return f"Error: {result.get('error')}"
    if tool_name == "assess_testability":
        if result.get("success"):
            rec = result.get("recommendation", "")
            reasons = "; ".join(result.get("reasons", []))
            return f"{rec}. Motivos: {reasons or 'Ninguno'}"
        return f"Error: {result.get('error')}"
    if tool_name == "check_vehicle_safety":
        if result.get("success"):
            d = result.get("data", {})
        recalls = d.get("recalls", [])
        if recalls:
            recall_texts = []
            for r in recalls:
                recall_texts.append(
                    f"- Campaña: {r.get('campaign_number')}\n"
                    f"  Componente: {r.get('component')}\n"
                    f"  Resumen: {r.get('summary')}\n"
                    f"  Consecuencia: {r.get('consequence')}\n"
                    f"  Remedio: {r.get('remedy')}\n"
                    f"  Fecha: {r.get('date')}\n"
                )
            recalls_str = "\n".join(recall_texts)
        else:
            recalls_str = "No se encontraron recalls registrados."

        safety = d.get("safety_ratings", {})
        ratings_str = (
            f"\nCalificaciones de seguridad:\n"
            f"  General: {safety.get('overall_rating')}\n"
            f"  Choque frontal: {safety.get('frontal_crash')}\n"
            f"  Choque lateral: {safety.get('side_crash')}\n"
            f"  Vuelco: {safety.get('rollover')}\n"
        ) if safety else ""

        recs = result.get("recommendations", [])
        rec_text = "\nRecomendaciones:\n- " + "\n- ".join(recs) if recs else ""

        return (
            f"{d.get('make')} {d.get('model')} ({d.get('year')}):\n\n"
            f"Recalls encontrados:\n{recalls_str}\n"
            f"{ratings_str}"
            f"{rec_text}"
        )
    return f"Error: {result.get('error')}"


tools = list(tools_dict.values())
