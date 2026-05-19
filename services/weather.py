"""
services/weather.py
--------------------
Inachukua hali ya hewa ya kweli kutoka OpenWeatherMap API.
Inabadilisha data ya hewa kuwa ushauri wa kilimo wa vitendo.
"""

import requests
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
WEATHER_KEY = os.getenv("OPENWEATHER_API_KEY")

# ── Mkoa → Mji unaojulikana OpenWeatherMap ────────────────────
# OpenWeatherMap inajua miji — si mikoa. Mapping hii inabadilisha
# mkoa wowote wa Tanzania kuwa mji mkuu wake unaojulikana API.
MKOA_TO_CITY = {
    "Arusha":            "Arusha",
    "Dar es Salaam":     "Dar es Salaam",
    "Dodoma":            "Dodoma",
    "Geita":             "Geita",
    "Iringa":            "Iringa",
    "Kagera":            "Bukoba",
    "Katavi":            "Mpanda",
    "Kigoma":            "Kigoma",
    "Kilimanjaro":       "Moshi",
    "Lindi":             "Lindi",
    "Manyara":           "Babati",
    "Mara":              "Musoma",
    "Mbeya":             "Mbeya",
    "Morogoro":          "Morogoro",
    "Mtwara":            "Mtwara",
    "Mwanza":            "Mwanza",
    "Njombe":            "Njombe",
    "Pwani":             "Kibaha",
    "Rukwa":             "Sumbawanga",
    "Ruvuma":            "Songea",
    "Shinyanga":         "Shinyanga",
    "Simiyu":            "Bariadi",
    "Singida":           "Singida",
    "Songwe":            "Vwawa",
    "Tabora":            "Tabora",
    "Tanga":             "Tanga",
    "Kaskazini Unguja":  "Zanzibar",
    "Kusini Unguja":     "Zanzibar",
    "Mjini Magharibi":   "Zanzibar",
    "Kaskazini Pemba":   "Wete",
    "Kusini Pemba":      "Mkoani",
}

def _resolve_city(city):
    """Badilisha mkoa kuwa mji unaojulikana OpenWeatherMap."""
    return MKOA_TO_CITY.get(city, city)

# Cache — hali ya hewa ibaki dakika 30
_cache = {}
CACHE_MINUTES = 30

def _cache_valid(city):
    if city not in _cache:
        return False
    age = datetime.now() - _cache[city]["fetched_at"]
    return age < timedelta(minutes=CACHE_MINUTES)

def get_weather(city="Dar es Salaam"):
    """Chukua hali ya hewa ya kweli kutoka OpenWeatherMap."""
    city = _resolve_city(city)  # Badilisha mkoa → mji
    city_key = city.lower().strip()

    if _cache_valid(city_key):
        return _cache[city_key]["data"]

    try:
        url = (
            f"http://api.openweathermap.org/data/2.5/weather"
            f"?q={city},TZ&appid={WEATHER_KEY}&units=metric&lang=en"
        )
        res = requests.get(url, timeout=8)
        res.raise_for_status()
        d = res.json()

        if d.get("cod") != 200:
            return None

        data = {
            "jina":       d["name"],
            "joto":       round(d["main"]["temp"]),
            "joto_hisi":  round(d["main"]["feels_like"]),
            "joto_juu":   round(d["main"]["temp_max"]),
            "joto_chini": round(d["main"]["temp_min"]),
            "hali":       d["weather"][0]["description"],
            "hali_id":    d["weather"][0]["id"],
            "unyevu":     d["main"]["humidity"],
            "upepo":      round(d["wind"]["speed"] * 3.6),  # m/s → km/h
            "mwelekeo_upepo": d["wind"].get("deg", 0),
            "mawingu":    d["clouds"]["all"],              # % ya mawingu
            "shinikizo":  d["main"]["pressure"],
            "mwonekano":  round(d.get("visibility", 10000) / 1000, 1),  # km
            "mvua_saa1":  d.get("rain", {}).get("1h", 0),  # mm katika saa 1
            "mvua_saa3":  d.get("rain", {}).get("3h", 0),  # mm katika saa 3
            "tarehe":     datetime.now().strftime("%d/%m/%Y %H:%M"),
        }

        _cache[city_key] = {"data": data, "fetched_at": datetime.now()}
        return data

    except Exception as e:
        print(f"[weather] Error: {e}")
        return None


def build_weather_farming_context(city="Dar es Salaam", zao=None):
    """
    Tengeneza context ya hali ya hewa KWA KILIMO TU —
    itumike kwenye system prompt ya bot.
    Bot itajua hali ya hewa ya kweli na itoe ushauri wa kilimo.
    """
    w = get_weather(city)
    if not w:
        return ""

    joto      = w["joto"]
    unyevu    = w["unyevu"]
    upepo_kph = w["upepo"]
    mvua_saa1 = w["mvua_saa1"]
    mvua_saa3 = w["mvua_saa3"]
    mawingu   = w["mawingu"]
    hali      = w["hali"]

    lines = [f"\n=== HALI YA HEWA YA KWELI — {w['jina'].upper()} (Sasa hivi) ==="]
    lines.append(f"Joto:        {joto}°C (hisi {w['joto_hisi']}°C)")
    lines.append(f"Unyevu:      {unyevu}%")
    lines.append(f"Upepo:       {upepo_kph} km/h")
    lines.append(f"Hali ya anga: {hali}")
    lines.append(f"Mawingu:     {mawingu}%")
    lines.append(f"Mvua (saa 1): {mvua_saa1} mm")
    lines.append(f"Mvua (saa 3): {mvua_saa3} mm")
    lines.append(f"Ilisasishwa: {w['tarehe']}")

    # ── Uchambuzi wa kilimo kulingana na hali halisi ──────────
    lines.append("\n--- UCHAMBUZI WA KILIMO (kulingana na hali ya sasa) ---")

    # 1. Spray Window — wakati mzuri wa kunyunyizia dawa
    if mvua_saa1 > 0 or mvua_saa3 > 2:
        lines.append("🚫 KUNYUNYIZIA DAWA: USINYUNYIZIE — mvua inanyesha au inakuja. Dawa itaoshwa.")
    elif upepo_kph > 20:
        lines.append("🚫 KUNYUNYIZIA DAWA: USINYUNYIZIE — upepo mkali (>20km/h). Dawa itabebwa mbali.")
    elif upepo_kph <= 10 and mvua_saa3 == 0:
        lines.append("✅ KUNYUNYIZIA DAWA: WAKATI MZURI — upepo mdogo, hakuna mvua inayotarajiwa.")
    else:
        lines.append("⚠️ KUNYUNYIZIA DAWA: Subiri — angalia hali ya hewa baadaye kidogo.")

    # 2. Hatari ya magonjwa kulingana na hewa
    lines.append("\n🦠 HATARI YA MAGONJWA:")
    disease_risks = []

    if unyevu >= 80 and 20 <= joto <= 28:
        disease_risks.append("🔴 HATARI YA JUU — Late Blight (nyanya/viazi): Unyevu mkubwa + joto la kati ni mazingira bora ya ugonjwa huu. Nyunyizia Ridomil ndani ya masaa 24.")
    elif unyevu >= 70 and joto >= 25:
        disease_risks.append("🟡 HATARI YA KATI — Early Blight (nyanya): Nyunyizia Mancozeb kama bado hujafanya wiki hii.")

    if unyevu >= 75 and 24 <= joto <= 30:
        disease_risks.append("🔴 HATARI YA JUU — Blast ya Mpunga: Usiku wenye unyevu + joto hili ni hatari. Nyunyizia Tricyclazole.")

    if unyevu >= 85:
        disease_risks.append("🟡 ONYO — Ukungu wa Mahindi (Gray Leaf Spot): Mwagilia chini tu, epuka maji juu ya majani.")

    if not disease_risks:
        disease_risks.append("🟢 Hatari ya chini sasa hivi — hali ya hewa si ya kusababisha magonjwa makubwa.")

    lines.extend(disease_risks)

    # 3. Umwagiliaji
    lines.append("\n💧 USHAURI WA UMWAGILIAJI:")
    if mvua_saa1 > 5 or mvua_saa3 > 10:
        lines.append("🚫 USIMWAGILIE — mvua ya kutosha inanyesha sasa hivi.")
    elif joto >= 33 and unyevu < 50:
        lines.append("🔴 MWAGILIA HARAKA — joto kali na udongo unakauka. Mwagilia saa hii asubuhi au jioni.")
    elif joto >= 28 and unyevu < 60:
        lines.append("⚠️ MWAGILIA LEO — joto la wastani, udongo unahitaji maji. Mwagilia asubuhi au jioni.")
    elif mvua_saa3 == 0 and mawingu < 30:
        lines.append("✅ MWAGILIA asubuhi (saa 1-2) au jioni (saa 11-12) — hewa nzuri, hakuna mvua.")
    else:
        lines.append("➡️ Angalia udongo kwa mkono — kama ukavu, mwagilia asubuhi au jioni.")

    # 4. Ushauri maalum kwa zao
    if zao:
        lines.append(f"\n🌱 USHAURI MAALUM KWA {zao.upper()} KULINGANA NA HALI YA SASA:")

        if zao == "Nyanya":
            if unyevu >= 80:
                lines.append("⚠️ Nyanya: Unyevu mkubwa — angalia Tuta absoluta na Late Blight. Mwagilia chini tu (drip), epuka kunyunyizia majani.")
            if joto >= 32:
                lines.append("⚠️ Nyanya: Joto kali — maua yanaweza kuanguka. Weka kivuli au mwagilia mara mbili kwa siku.")
            if upepo_kph > 15:
                lines.append("⚠️ Nyanya: Upepo — hakikisha nguzo na kamba za kuunga ziko imara.")

        elif zao == "Mahindi":
            if joto >= 35:
                lines.append("🔴 Mahindi: Joto kali sana — kama mahindi yako yana maua, hii inaweza kupunguza mavuno. Mwagilia mara moja kwa siku.")
            if unyevu >= 75 and joto >= 25:
                lines.append("⚠️ Mahindi: Angalia Fall Army Worm — hali hii inasaidia kuzaliana kwao. Angalia shamba asubuhi.")

        elif zao == "Mpunga":
            if unyevu >= 80 and 24 <= joto <= 30:
                lines.append("🔴 Mpunga: Hatari ya Blast ni kubwa sana. Nyunyizia Tricyclazole au Isoprothiolane LEO.")
            if joto >= 35:
                lines.append("⚠️ Mpunga: Joto kali wakati wa kutoa maua linapunguza mazao. Hakikisha maji ya kutosha mashambani.")

        elif zao == "Maharagwe":
            if unyevu >= 75:
                lines.append("⚠️ Maharagwe: Unyevu mkubwa — hatari ya kuoza kwa mizizi. Hakikisha mifereji ya maji inafanya kazi.")
            if mvua_saa3 > 5:
                lines.append("✅ Maharagwe: Mvua nzuri — hakuna haja ya kumwagilia sasa.")

        elif zao == "Mihogo":
            if joto >= 30 and unyevu < 50:
                lines.append("➡️ Mihogo: Inastahimili joto — lakini kama ni mwaka wa kwanza, mwagilia wiki moja moja.")

    lines.append("\nMUHIMU: Tumia taarifa hizi za hali ya hewa ya KWELI kujibu maswali ya kilimo.")
    lines.append("Ukiulizwa hali ya hewa — toa nambari halisi zilizo hapo juu, si makadirio.")
    lines.append("=== MWISHO WA HALI YA HEWA ===")

    return "\n".join(lines)


if __name__ == "__main__":
    print("🌤 Kujaribu Weather Service...")
    ctx = build_weather_farming_context("Dar es Salaam", "Nyanya")
    print(ctx)