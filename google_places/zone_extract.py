import csv
from pathlib import Path

# ---------- CONFIG ----------
INPUT_TXT  = Path("/mnt/c/Users/blake/OneDrive - Stellenbosch University/SUN 2/2025/Skripsie/Demo Data/Fuel Zone Magisterial district Magi.txt")   # your extracted text file
OUTPUT_CSV = Path("/mnt/c/Users/blake/OneDrive - Stellenbosch University/SUN 2/2025/Skripsie/Demo Data/fuel_zones_clean.csv")
# ----------------------------

PROVINCES = {
    "Eastern Cape",
    "Western Cape",
    "Northern Cape",
    "KwaZulu Natal",
    "Free State",
    "North West",
    "Mpumalanga",
    "Gauteng",
    "Limpopo",
}

HEADERS = ["Fuel Zone", "Magisterial district", "Magisterial code", "Province"]

def is_header_line(tokens):
    """Detect and skip header lines like 'Fuel Zone Magisterial district ...'."""
    joined = " ".join(tokens).lower()
    return ("fuel" in joined and "zone" in joined and "magisterial" in joined) or joined.strip() == ""

def looks_like_fuel_zone(token):
    """
    Fuel zone codes in the file generally look like:
      09B, 05A, 61C, 33J, 67C, etc.  (two digits + 1 uppercase letter)
    """
    if len(token) != 3:
        return False
    return token[:2].isdigit() and token[2:].isalpha() and token[2:].isupper()

def detect_province(tokens):
    """
    Province is at the end. It’s either one token (Mpumalanga, Gauteng, Limpopo)
    or two tokens (Eastern/Western/Northern Cape, Free State, North West, KwaZulu Natal).
    Return (province, n_tokens_consumed_from_end) or (None, 0) if not found.
    """
    if not tokens:
        return None, 0

    # Try last two tokens first
    if len(tokens) >= 2:
        last2 = " ".join(tokens[-2:])
        if last2 in PROVINCES:
            return last2, 2

    # Then last one
    last1 = tokens[-1]
    if last1 in PROVINCES:
        return last1, 1

    return None, 0

def parse_line(line):
    """
    Parse one content line into a row dict.
    Format: <zone> <district (may have spaces/parentheses)> <mag_code> <province>
    """
    # Normalize whitespace to single spaces
    tokens = line.strip().split()
    if not tokens or is_header_line(tokens):
        return None

    # Some lines can begin with garbage; ensure first token is a fuel zone
    if not looks_like_fuel_zone(tokens[0]):
        return None

    zone = tokens[0]

    # Detect province at the end
    province, prov_count = detect_province(tokens)
    if not province:
        return None  # can't parse without province reliably

    # Magisterial code should be the token right before the province tokens
    if len(tokens) < 2 + prov_count:
        return None
    mag_code = tokens[-1 - prov_count]

    # Remaining middle is the district
    middle = tokens[1:-1 - prov_count]
    district = " ".join(middle).strip()

    # Skip obvious non-rows
    if not district or district.upper() == "NO" and mag_code.upper() == "MDZ":
        return None

    # Keep #N/A codes as-is so you can inspect later
    return {
        "Fuel Zone": zone,
        "Magisterial district": district,
        "Magisterial code": mag_code,
        "Province": province,
    }

def main():
    rows = []
    seen = set()  # for de-duplication

    with INPUT_TXT.open("r", encoding="utf-8", errors="ignore") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue

            row = parse_line(line)
            if not row:
                continue

            key = (row["Fuel Zone"], row["Magisterial district"], row["Magisterial code"], row["Province"])
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)

    # Write CSV
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Done. Wrote {len(rows)} rows to {OUTPUT_CSV.resolve()}")

if __name__ == "__main__":
    main()
