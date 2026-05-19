"""
services/farmer_profile.py
---------------------------
Inashughulikia taarifa za mkulima — mkoa, zao, mbolea, wadudu.
Inahifadhi kwenye SQLite (kilimo.db) — kila mkulima ana profile yake.
"""

import sqlite3
import json
import os
import re

DB_PATH = "kilimo.db"
KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "knowledge")

# ── Pakia knowledge base ──────────────────────────────────────
def load_json(filename):
    path = os.path.join(KNOWLEDGE_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

REGIONS_KB   = load_json("regions.json")
CROPS_KB     = load_json("crops.json")

# ── Database setup ────────────────────────────────────────────
def init_profile_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS farmer_profiles (
            session_id TEXT PRIMARY KEY,
            mkoa       TEXT,
            zao        TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_profile_db()

# ── Hifadhi / soma profile ────────────────────────────────────
def save_profile(session_id, mkoa=None, zao=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO farmer_profiles (session_id, mkoa, zao)
        VALUES (?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            mkoa = COALESCE(?, farmer_profiles.mkoa),
            zao  = COALESCE(?, farmer_profiles.zao),
            updated_at = CURRENT_TIMESTAMP
    """, (session_id, mkoa, zao, mkoa, zao))
    conn.commit()
    conn.close()

def get_profile(session_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT mkoa, zao FROM farmer_profiles WHERE session_id = ?",
        (session_id,)
    )
    row = c.fetchone()
    conn.close()
    if row:
        return {"mkoa": row[0], "zao": row[1]}
    return {"mkoa": None, "zao": None}

def clear_profile(session_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM farmer_profiles WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

# ── Gundua mkoa na zao kutoka ujumbe ─────────────────────────

# Mikoa yote 31 ya Tanzania + majina mbadala (aliases)
MIKOA_YOTE = {
    # Mikoa ya Bara
    "Arusha":         ["arusha", "arush"],
    "Dar es Salaam":  ["dar es salaam", "dar", "dsm", "dares salaam", "darussalam"],
    "Dodoma":         ["dodoma"],
    "Geita":          ["geita"],
    "Iringa":         ["iringa"],
    "Kagera":         ["kagera", "bukoba"],
    "Katavi":         ["katavi", "mpanda"],
    "Kigoma":         ["kigoma"],
    "Kilimanjaro":    ["kilimanjaro", "kili", "moshi"],
    "Lindi":          ["lindi"],
    "Manyara":        ["manyara", "babati"],
    "Mara":           ["mara", "musoma"],
    "Mbeya":          ["mbeya"],
    "Morogoro":       ["morogoro"],
    "Mtwara":         ["mtwara"],
    "Mwanza":         ["mwanza"],
    "Njombe":         ["njombe"],
    "Pwani":          ["pwani", "coast", "kibaha", "bagamoyo"],
    "Rukwa":          ["rukwa", "sumbawanga"],
    "Ruvuma":         ["ruvuma", "songea"],
    "Shinyanga":      ["shinyanga"],
    "Simiyu":         ["simiyu", "bariadi"],
    "Singida":        ["singida"],
    "Songwe":         ["songwe", "vwawa"],
    "Tabora":         ["tabora"],
    "Tanga":          ["tanga"],
    "Iringa":         ["iringa"],
    # Mikoa ya Visiwani
    "Kaskazini Unguja":  ["kaskazini unguja", "north zanzibar", "unguja kaskazini"],
    "Kusini Unguja":     ["kusini unguja", "south zanzibar", "unguja kusini"],
    "Mjini Magharibi":   ["mjini magharibi", "zanzibar mjini", "stone town", "zanzibar"],
    "Kaskazini Pemba":   ["kaskazini pemba", "north pemba"],
    "Kusini Pemba":      ["kusini pemba", "south pemba"],
}

# Mikoa inayojulikana kwenye regions.json (ina data kamili)
MIKOA_INAYOJULIKANA = list(REGIONS_KB.get("mikoa", {}).keys())

def detect_mkoa(text_lower):
    """Gundua mkoa kutoka ujumbe — inajua majina yote 31 + aliases."""
    for mkoa_rasmi, aliases in MIKOA_YOTE.items():
        for alias in aliases:
            if alias in text_lower:
                return mkoa_rasmi
    return None

MAZAO_MAPPING = {
    # Kiswahili → jina kwenye knowledge base
    "mahindi": "Mahindi", "maize": "Mahindi", "corn": "Mahindi",
    "mpunga": "Mpunga", "rice": "Mpunga", "paddy": "Mpunga",
    "nyanya": "Nyanya", "tomato": "Nyanya", "tomatoes": "Nyanya",
    "maharagwe": "Maharagwe", "beans": "Maharagwe", "bean": "Maharagwe",
    "mihogo": "Mihogo", "cassava": "Mihogo", "mhogo": "Mihogo",
    "viazi": "Viazi", "potato": "Viazi", "potatoes": "Viazi",
    "alizeti": "Alizeti", "sunflower": "Alizeti",
    "ndizi": "Ndizi", "banana": "Ndizi", "bananas": "Ndizi",
    "kahawa": "Kahawa", "coffee": "Kahawa",
    "pamba": "Pamba", "cotton": "Pamba",
    "mtama": "Mtama", "sorghum": "Mtama",
    "karanga": "Karanga", "groundnut": "Karanga", "peanut": "Karanga",
    "ufuta": "Ufuta", "sesame": "Ufuta",
    "ngano": "Ngano", "wheat": "Ngano",
}

def detect_profile_from_message(text):
    """
    Chunguza ujumbe wa mtumiaji — gundua mkoa na zao aliyotaja.
    Inajua mikoa yote 31 ya Tanzania + majina mbadala.
    """
    text_lower = text.lower()
    found = {"mkoa": None, "zao": None}

    # Gundua mkoa — tumia function mpya inayojua mikoa yote 31
    found["mkoa"] = detect_mkoa(text_lower)

    # Gundua zao
    for keyword, zao_name in MAZAO_MAPPING.items():
        if keyword in text_lower:
            found["zao"] = zao_name
            break

    return found

# ── Tengeneza context kwa AI ──────────────────────────────────
def build_farmer_context(session_id, message):
    """
    Tengeneza string ya context kuhusu mkulima — itatumwa kwa Groq
    pamoja na SYSTEM_PROMPT ili AI ijue hali halisi ya mkulima.
    """

    # Gundua mkoa/zao mpya kutoka ujumbe
    detected = detect_profile_from_message(message)

    # Hifadhi kama kuna mpya
    if detected["mkoa"] or detected["zao"]:
        save_profile(session_id, detected["mkoa"], detected["zao"])

    # Soma profile ya sasa
    profile = get_profile(session_id)
    mkoa = profile.get("mkoa")
    zao  = profile.get("zao")

    if not mkoa and not zao:
        return ""  # Hatujui chochote — usiongeze context

    lines = ["=== TAARIFA ZA MKULIMA HUYU ==="]

    # ── Taarifa za mkoa ──
    if mkoa:
        region_data = REGIONS_KB.get("mikoa", {}).get(mkoa, {})
        lines.append(f"\nMKOA: {mkoa}")
        if region_data:
            lines.append(f"Hali ya hewa: {region_data.get('hali_ya_hewa', '—')}")
            lines.append(f"Udongo: {region_data.get('udongo', '—')}")

            # Msimu wa sasa
            import datetime
            month = datetime.datetime.now().month
            misimu = region_data.get("misimu", {})
            msimu_wa_sasa = _get_current_season(month, misimu)
            if msimu_wa_sasa:
                lines.append(f"Msimu wa sasa: {msimu_wa_sasa}")

            mazao_bora = region_data.get("mazao_bora", [])
            if mazao_bora:
                lines.append(f"Mazao bora kwa {mkoa}: {', '.join(mazao_bora)}")

            changamoto = region_data.get("changamoto", [])
            if changamoto:
                lines.append(f"Changamoto za kawaida: {', '.join(changamoto)}")
        else:
            # Mkoa unajulikana lakini hauna data kamili kwenye KB
            # Tumia maarifa ya jumla ya Tanzania — AI atajaza mapengo
            lines.append(f"(Mkoa huu unajulikana Tanzania — tumia maarifa yako ya kilimo wa Tanzania kujibu)")
            lines.append(f"Jibu kwa kuzingatia hali ya kawaida ya kilimo cha mkoa huo Tanzania.")

    # ── Taarifa za zao ──
    if zao:
        crop_data = CROPS_KB.get("mazao", {}).get(zao, {})
        lines.append(f"\nZAO: {zao}")
        if crop_data:
            lines.append(f"Muda wa kukua: {crop_data.get('muda_wa_kukua', '—')}")
            lines.append(f"Joto bora: {crop_data.get('joto_bora', '—')}")
            lines.append(f"pH bora ya udongo: {crop_data.get('pH_bora', '—')}")
            lines.append(f"Mvua inayohitajika: {crop_data.get('mvua_inayohitajika', '—')}")

            # Mbolea
            mbolea = crop_data.get("mbolea", {})
            if mbolea:
                lines.append(f"\nMBOLEA INAYOPENDEKEZWA KWA {zao.upper()}:")
                kp = mbolea.get("kabla_ya_kupanda", {})
                if kp:
                    lines.append(f"  Kabla ya kupanda: {kp.get('aina','—')} — {kp.get('kiasi','—')}")
                    lines.append(f"  Wakati: {kp.get('wakati','—')}")
                    lines.append(f"  Bei Tanzania: {kp.get('bei_tz','—')}")
                kk = mbolea.get("kukua", {})
                if kk:
                    lines.append(f"  Wakati wa kukua: {kk.get('aina','—')} — {kk.get('kiasi','—')}")
                    lines.append(f"  Bei Tanzania: {kk.get('bei_tz','—')}")

            # Umwagiliaji
            umwagiliaji = crop_data.get("umwagiliaji", {})
            if umwagiliaji:
                lines.append(f"\nUMWAGILIAJI KWA {zao.upper()}:")
                lines.append(f"  Kiasi: {umwagiliaji.get('kiasi_kwa_msimu','—')}")
                lines.append(f"  Mbinu bora: {umwagiliaji.get('mbinu_bora','—')}")
                lines.append(f"  Ratiba: {umwagiliaji.get('ratiba','—')}")
                hatua = umwagiliaji.get("hatua_muhimu", [])
                if hatua:
                    lines.append(f"  Hatua muhimu: " + " | ".join(hatua[:3]))

            # Wadudu na dawa
            wadudu = crop_data.get("wadudu_na_dawa", [])
            if wadudu:
                lines.append(f"\nWADUDU HATARI KWA {zao.upper()} NA DAWA ZAKE:")
                for w in wadudu:
                    lines.append(f"  🐛 {w.get('jina','—')}")
                    lines.append(f"     Dalili: {w.get('dalili','—')}")
                    lines.append(f"     Dawa: {', '.join(w.get('dawa',[]))}")
                    lines.append(f"     Kipimo: {w.get('kipimo','—')}")
                    lines.append(f"     Bei: {w.get('bei_tz','—')}")

            # Magonjwa
            magonjwa = crop_data.get("magonjwa", [])
            if magonjwa:
                lines.append(f"\nMAGONJWA YA {zao.upper()} NA TIBA:")
                for m in magonjwa:
                    lines.append(f"  🦠 {m.get('jina','—')}")
                    lines.append(f"     Dalili: {m.get('dalili','—')}")
                    lines.append(f"     Tiba: {m.get('tiba','—')}")

            # Aina bora
            aina = crop_data.get("aina_bora_tanzania", [])
            if aina:
                lines.append(f"\nAINA BORA ZA {zao.upper()} TANZANIA:")
                for a in aina:
                    lines.append(f"  ✅ {a.get('jina','—')}: {a.get('sifa','—')}")

    lines.append("\n=== MWISHO WA TAARIFA ZA MKULIMA ===")
    lines.append("Tumia taarifa hizi kujibu kwa usahihi wa hali halisi ya mkulima huyu.")

    return "\n".join(lines)


def _get_current_season(month, misimu):
    """Gundua msimu wa sasa kulingana na mwezi."""
    month_names = {
        1:"Januari",2:"Februari",3:"Machi",4:"Aprili",5:"Mei",6:"Juni",
        7:"Julai",8:"Agosti",9:"Septemba",10:"Oktoba",11:"Novemba",12:"Desemba"
    }
    current_month_name = month_names.get(month, "")

    for season_name, info in misimu.items():
        mwanzo = info.get("mwanzo", "")
        mwisho = info.get("mwisho", "")
        mvua   = info.get("mvua", "")

        # Angalia kama mwezi wa sasa uko ndani ya msimu
        miezi_ya_msimu = _months_in_range(mwanzo, mwisho)
        if month in miezi_ya_msimu:
            return f"{season_name.capitalize()} ({mwanzo}–{mwisho}), mvua: {mvua}"

    return "Kati ya misimu"


def _months_in_range(start_name, end_name):
    """Rudisha nambari za miezi kati ya mwanzo na mwisho."""
    month_map = {
        "Januari":1,"Februari":2,"Machi":3,"Aprili":4,"Mei":5,"Juni":6,
        "Julai":7,"Agosti":8,"Septemba":9,"Oktoba":10,"Novemba":11,"Desemba":12
    }
    s = month_map.get(start_name, 1)
    e = month_map.get(end_name, 12)
    if s <= e:
        return list(range(s, e + 1))
    else:
        # Inazunguka mwaka (mfano: Novemba–Aprili)
        return list(range(s, 13)) + list(range(1, e + 1))