#!/usr/bin/env python3
"""
Verbose matcher: SA depot addresses -> DMRE fuel zones via fuzzy matching.

Run:
  python3 match_fuel_zones.py

Requires:
  pip install pandas openpyxl rapidfuzz
"""

import os, re, sys, pandas as pd
from rapidfuzz import process, fuzz

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# --- set your absolute Excel path here (keep ONLY this line for INPUT_EXCEL) ---
INPUT_EXCEL = r"/mnt/c/Users/blake/OneDrive - Stellenbosch University/SUN 2/2025/Skripsie/Demo Data/Match_Fuel_Zones_Input.xlsx"

# Output CSV will go next to the script
OUTPUT_CSV = os.path.join(SCRIPT_DIR, "matched_zones.csv")

PREF_ADDR_SHEET = "Addresses"
PREF_MDZ_SHEET  = "MDZ"


# Fuzzy match settings
FUZZY_THRESHOLD = 85
SCORER = fuzz.WRatio

# Locality alias / normalisation
# --- Aliases to improve MDZ matching (address/locality -> MDZ district name or best query) ---
LOCALITY_NORMALISATION = {
    # General SA name changes / legacy names
    "eMalahleni": "Witbank",
    "Emalahleni": "Witbank",
    "Mbombela": "Nelspruit",
    "Gqeberha": "Port Elizabeth",
    "Polokwane": "Pietersburg",
    "Mogale": "Krugersdorp",

    # Cape Town variants
    "Foreshore": "Cape Town",
    "Milnerton": "Cape Town",
    "Marconi Beam": "Cape Town",

    # Johannesburg / Pretoria industrial suburbs
    "Waltloo": "Pretoria",
    "Langlaagte": "Johannesburg",
    "Alrode": "Alberton",

    # Ekurhuleni / Sedibeng oddities
    "Lesedi": "Heidelberg",
    "Lesedi Local Municipality": "Heidelberg",

    # Durban / eThekwini coastal logistics areas
    "Island View": "Durban",
    "Island View Rd": "Durban",
    "Bayhead": "Durban",
    "Wentworth": "Durban",
    "Bluff": "Durban",
    "Sapref": "Durban",

    # Richards Bay cluster (DMZ uses historical magisterial district name)
    "Richards Bay": "Lower Umfolozi",
    "uMhlathuze": "Lower Umfolozi",   # common municipal name
    "uMhlatuze": "Lower Umfolozi",    # variant spelling
    "Empangeni": "Lower Umfolozi",

    # Highveld Ridge (Secunda / Evander)
    "Secunda": "Highveld Ridge",
    "Evander": "Highveld Ridge",

    # Nkomazi (Kamhulshwa) cluster (Hectorspruit / Malalane / Emjejane)
    "Hectorspruit": "Nkomazi (Kamhulshwa)",
    "Emjejane": "Nkomazi (Kamhulshwa)",
    "Malalane": "Nkomazi (Kamhulshwa)",
    "Malelane": "Nkomazi (Kamhulshwa)",

    # King William’s Town (now Qonce) / Berlin / Ntabozuko
    "Ntabozuko": "King Williams Town",
    "Berlin": "King Williams Town",
    "Qonce": "King Williams Town",

    # Northern Cape: Kathu sits in Kuruman (south of 27°)
    # (ASCII fallback '27o' keeps things robust for sources without the degree symbol)
    "Kathu": "Kuruman (south of 27o latitude)",
}


LOCALITY_REGEX = re.compile(r"^(.*?)(?:,\s*South Africa)?\s*$", re.IGNORECASE)

# Output path = same folder as this script
OUTPUT_CSV = os.path.join(SCRIPT_DIR, "matched_zones_2.csv")


def die(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(1)


def extract_locality(address: str) -> str:
    if not isinstance(address, str) or not address.strip():
        return ""
    m = LOCALITY_REGEX.match(address.strip())
    core = m.group(1) if m else address
    parts = [p.strip() for p in core.split(",") if p.strip()]
    if not parts: return ""
    for p in reversed(parts):
        if not re.fullmatch(r"[0-9\s\-]+", p) and len(p) > 1:
            return p
    return parts[0] if parts else ""


def normalise_locality(locality: str) -> str:
    if not locality:
        return ""
    for k, v in LOCALITY_NORMALISATION.items():
        if locality.lower() == k.lower():
            return v
    return locality


def fuzzy_match_one(query: str, candidates: pd.Series, threshold: int = FUZZY_THRESHOLD, scorer=SCORER):
    if not query or candidates.empty:
        return None, 0.0
    choices = candidates.dropna().astype(str).unique().tolist()
    best = process.extractOne(query, choices, scorer=scorer)
    if not best:
        return None, 0.0
    match_value, score, _ = best
    if score >= threshold:
        return match_value, float(score)
    return None, float(score)


def pick_sheet_name(all_sheets, preferred, fallbacks):
    """Return preferred if present; else first match from fallbacks (case-insensitive); else None."""
    lower = {s.lower(): s for s in all_sheets}
    if preferred in all_sheets:
        return preferred
    if preferred.lower() in lower:
        return lower[preferred.lower()]
    for fb in fallbacks:
        if fb in all_sheets:
            return fb
        if fb.lower() in lower:
            return lower[fb.lower()]
    return None


def main():
    print(f"[INFO] Script folder: {SCRIPT_DIR}")
    print(f"[INFO] Expecting Excel at: {INPUT_EXCEL}")

    if not os.path.exists(INPUT_EXCEL):
        die(f"Excel file not found at: {INPUT_EXCEL}")

    # Inspect workbook to find sheets
    try:
        xls = pd.ExcelFile(INPUT_EXCEL)
        sheets = xls.sheet_names
    except Exception as e:
        die(f"Failed to open Excel: {e}")

    print(f"[INFO] Found sheets: {sheets}")

    addr_sheet = pick_sheet_name(
        sheets,
        PREF_ADDR_SHEET,
        fallbacks=["Sheet 1", "Addresses", "Address", "Sheet1"]
    )
    mdz_sheet = pick_sheet_name(
        sheets,
        PREF_MDZ_SHEET,
        fallbacks=["Sheet 2", "MDZ", "Zones", "Fuel Zones", "Sheet2"]
    )

    if not addr_sheet:
        die("Could not find an Addresses sheet. Create one named 'Addresses' or 'Sheet 1'.")
    if not mdz_sheet:
        die("Could not find an MDZ sheet. Create one named 'MDZ' or 'Sheet 2'.")

    print(f"[INFO] Using address sheet: {addr_sheet}")
    print(f"[INFO] Using MDZ sheet: {mdz_sheet}")

    try:
        df_addr = pd.read_excel(INPUT_EXCEL, sheet_name=addr_sheet)
        df_mdz  = pd.read_excel(INPUT_EXCEL, sheet_name=mdz_sheet)
    except Exception as e:
        die(f"Failed reading sheets: {e}")

    # Validate columns
    if "Supply_Depot_Address" not in df_addr.columns:
        die(f"Addresses sheet '{addr_sheet}' must contain column 'Supply_Depot_Address'. Columns present: {list(df_addr.columns)}")

    required_mdz_cols = {"Fuel Zone", "Magisterial district"}
    if not required_mdz_cols.issubset(set(df_mdz.columns)):
        die(f"MDZ sheet '{mdz_sheet}' must contain columns {required_mdz_cols}. Columns present: {list(df_mdz.columns)}")

    print(f"[INFO] {len(df_addr)} address rows loaded.")
    print(f"[INFO] {len(df_mdz)} MDZ rows loaded.")

    # Create ID if not present
    if "ID" not in df_addr.columns:
        df_addr.insert(0, "ID", range(1, len(df_addr) + 1))

    # Extract and normalise
    print("[INFO] Extracting locality...")
    df_addr["Locality"] = df_addr["Supply_Depot_Address"].astype(str).apply(extract_locality)
    df_addr["Locality_Norm"] = df_addr["Locality"].apply(normalise_locality)
    df_addr["CountryFlag"] = df_addr["Supply_Depot_Address"].str.contains("South Africa", case=False, na=False).map(
        {True: "SA", False: "Foreign"}
    )

    # Prepare MDZ lookup
    df_mdz_lookup = (
        df_mdz[["Magisterial district", "Fuel Zone", *(c for c in ["Magisterial code", "Province"] if c in df_mdz.columns)]]
        .dropna(subset=["Magisterial district"])
        .drop_duplicates(subset=["Magisterial district"])
        .reset_index(drop=True)
    )
    print(f"[INFO] Unique MDZ districts: {df_mdz_lookup['Magisterial district'].nunique()}")

    # Fuzzy match only SA rows
    sa_mask = (df_addr["CountryFlag"] == "SA")
    print(f"[INFO] Matching SA rows: {sa_mask.sum()} (foreign rows: {(~sa_mask).sum()})")

    matches = []
    for idx, row in df_addr[sa_mask].iterrows():
        q = str(row["Locality_Norm"]).strip()
        best_val, score = fuzzy_match_one(q, df_mdz_lookup["Magisterial district"])
        matches.append((idx, q, best_val, score, "fuzzy" if best_val else "none"))

    df_match = pd.DataFrame(matches, columns=["_idx", "Query_Locality", "Matched_District", "Match_Score", "Match_Method"])
    df_addr = df_addr.join(df_match.set_index("_idx"), how="left")

    df_addr = df_addr.merge(
        df_mdz_lookup,
        left_on="Matched_District",
        right_on="Magisterial district",
        how="left",
        suffixes=("", "_mdz"),
    )

    df_addr["Match_Status"] = df_addr.apply(
        lambda r: (
            "OK" if (pd.notna(r.get("Fuel Zone")) and (r.get("Match_Score", 0) >= FUZZY_THRESHOLD) and r.get("CountryFlag")=="SA")
            else ("FOREIGN" if r.get("CountryFlag")=="Foreign" else "REVIEW")
        ),
        axis=1,
    )

    # Output selected columns
    out_cols = [
        "ID",
        "Supply_Depot_Address",
        "CountryFlag",
        "Locality",
        "Locality_Norm",
        "Query_Locality",
        "Matched_District",
        "Match_Score",
        "Match_Method",
        "Fuel Zone",
    ]
    if "Magisterial code" in df_addr.columns: out_cols.append("Magisterial code")
    if "Province" in df_addr.columns: out_cols.append("Province")
    out_cols.append("Match_Status")

    df_out = df_addr[out_cols].copy()

    # Write CSV
    df_out.to_csv(OUTPUT_CSV, index=False)
    print(f"[INFO] Wrote {len(df_out)} rows to:\n  {OUTPUT_CSV}")

    # Simple summary
    print(
        "[INFO] Summary -> "
        f"OK: {(df_out['Match_Status']=='OK').sum()}, "
        f"REVIEW: {(df_out['Match_Status']=='REVIEW').sum()}, "
        f"FOREIGN: {(df_out['Match_Status']=='FOREIGN').sum() if 'FOREIGN' in df_out['Match_Status'].values else 0}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        die(f"Unhandled error: {e}")
