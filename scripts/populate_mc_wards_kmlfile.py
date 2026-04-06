# load_navi_mumbai_wards.py
# Run with: python load_navi_mumbai_wards.py

import os
import sys
import django
import xml.etree.ElementTree as ET

# ── Django setup ────────────────────────────────────────────────────────────
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection

# ── Config ──────────────────────────────────────────────────────────────────
KML_FILE = "thane_mc_wards.kml"
MUNICIPAL_CORP_ID = 4  # Navi Mumbai already exists in DB


# ── Helpers ─────────────────────────────────────────────────────────────────
def parse_placemarks(root):
    """Try parsing with KML namespace first, then without."""
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    placemarks = root.findall(".//kml:Placemark", ns)

    if placemarks:
        return placemarks, ns

    # Fallback — no namespace
    return root.findall(".//Placemark"), {}


# def get_ward_name(placemark, ns):
#     """Extract ward name from SchemaData or fallback to <name> tag."""
#     tag = "kml:SchemaData" if ns else "SchemaData"
#     schema_data = placemark.find(f".//{tag}", ns)

#     if schema_data is not None:
#         for simple_data in schema_data:
#             if simple_data.get("name") == "ward_lgd_name":
#                 return simple_data.text

#     # Fallback to <name> tag
#     tag = "kml:name" if ns else "name"
#     name_el = placemark.find(tag, ns)
#     return name_el.text if name_el is not None else None

def get_ward_name(placemark, ns):
    """Extract ward name from SchemaData or fallback to <name> tag."""
    tag = "kml:SchemaData" if ns else "SchemaData"
    schema_data = placemark.find(f".//{tag}", ns)

    if schema_data is not None:
        for simple_data in schema_data:
            if simple_data.get("name") == "ward_lgd_name":
                raw_name = simple_data.text
                return extract_ward_number(raw_name)

    # Fallback to <name> tag
    tag = "kml:name" if ns else "name"
    name_el = placemark.find(tag, ns)
    return extract_ward_number(name_el.text) if name_el is not None else None


def extract_ward_number(raw_name):
    """
    Extracts ward number from full LGD name.
    e.g. 'Kalyan-Dombivli (M Corp.) - Ward No.63' → 'Ward No.63'
         'Navi Mumbai (M Corp.) - Ward No.26'      → 'Ward No.26'
    """
    if not raw_name:
        return None

    # Split on ' - ' and take the last part
    parts = raw_name.split(" - ")
    return parts[-1].strip() if parts else raw_name.strip()

def get_coordinates(placemark, ns):
    """Extract raw coordinates string from Placemark."""
    tag = "kml:coordinates" if ns else "coordinates"
    coords_el = placemark.find(f".//{tag}", ns)
    return coords_el.text.strip() if coords_el is not None else None


def coordinates_to_wkt(coordinates_text):
    """
    Convert KML coordinates to PostGIS WKT POLYGON.
    KML:  lon,lat,alt lon,lat,alt ...
    WKT:  POLYGON((lon lat, lon lat, ...))
    """
    try:
        points = []
        for coord in coordinates_text.split():
            parts = coord.split(",")
            lon, lat = float(parts[0]), float(parts[1])
            points.append(f"{lon} {lat}")

        if len(points) < 3:
            return None

        # Ensure polygon is closed
        if points[0] != points[-1]:
            points.append(points[0])

        return f"POLYGON(({', '.join(points)}))"

    except Exception as e:
        print(f"  [ERROR] Geometry parse failed: {e}")
        return None


def ward_exists(cursor, ward_name):
    cursor.execute(
        "SELECT id FROM ward WHERE name = %s AND municipal_corp_id = %s",
        [ward_name, MUNICIPAL_CORP_ID]
    )
    return cursor.fetchone() is not None


def insert_ward(cursor, ward_name, wkt):
    cursor.execute(
        """
        INSERT INTO ward (name, municipal_corp_id, geometry)
        VALUES (%s, %s, ST_SetSRID(ST_GeomFromText(%s), 4326))
        """,
        [ward_name, MUNICIPAL_CORP_ID, wkt]
    )


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    if not os.path.exists(KML_FILE):
        print(f"[ERROR] KML file not found: {KML_FILE}")
        sys.exit(1)

    print(f"Parsing KML file: {KML_FILE}")
    tree = ET.parse(KML_FILE)
    root = tree.getroot()

    placemarks, ns = parse_placemarks(root)
    print(f"Found {len(placemarks)} placemarks\n")

    inserted = 0
    skipped = 0
    errors = 0

    with connection.cursor() as cursor:
        for placemark in placemarks:
            ward_name = get_ward_name(placemark, ns)
            coordinates_text = get_coordinates(placemark, ns)

            if not ward_name:
                print("  [SKIP] Could not extract ward name")
                skipped += 1
                continue

            if not coordinates_text:
                print(f"  [SKIP] No coordinates found for: {ward_name}")
                skipped += 1
                continue

            if ward_exists(cursor, ward_name):
                print(f"  [EXISTS] {ward_name}")
                skipped += 1
                continue

            wkt = coordinates_to_wkt(coordinates_text)
            if not wkt:
                print(f"  [ERROR] Invalid geometry for: {ward_name}")
                errors += 1
                continue

            try:
                insert_ward(cursor, ward_name, wkt)
                print(f"  [OK] Inserted: {ward_name}")
                inserted += 1
            except Exception as e:
                print(f"  [ERROR] Failed to insert {ward_name}: {e}")
                errors += 1

    print(f"\n── Summary ──────────────────────")
    print(f"  Inserted : {inserted}")
    print(f"  Skipped  : {skipped}")
    print(f"  Errors   : {errors}")
    print(f"─────────────────────────────────")


if __name__ == "__main__":
    main()