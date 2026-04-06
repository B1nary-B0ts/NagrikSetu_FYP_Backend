import json
from shapely.geometry import shape, MultiPolygon, Polygon
from shapely.ops import polygonize
from sqlalchemy import create_engine, text

DB_URL = "postgresql://postgres:postgres@localhost:5433/civic_issues_db"
engine = create_engine(DB_URL)

MUNICIPAL_FILE = "thane.geojson"


def load_geojson(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def convert_to_multipolygon(geom):
    """
    Convert any geometry to MultiPolygon.
    - Polygon → MultiPolygon
    - MultiPolygon → unchanged
    - LineString → attempt to polygonize
    Returns None if conversion not possible
    """
    geom_shape = shape(geom)

    if geom_shape.geom_type == "Polygon":
        return MultiPolygon([geom_shape])
    elif geom_shape.geom_type == "MultiPolygon":
        return geom_shape
    elif geom_shape.geom_type == "LineString":
        # attempt to polygonize line
        polys = list(polygonize([geom_shape]))
        if polys:
            return MultiPolygon(polys)
        else:
            print(f"⚠ Skipping LineString geometry, cannot polygonize")
            return None
    else:
        print(f"⚠ Skipping unsupported geometry type: {geom_shape.geom_type}")
        return None


def insert_municipal_corp(conn, feature):
    name = feature["properties"].get("name")
    geom = convert_to_multipolygon(feature["geometry"])
    if geom is None:
        return None  # skip this feature

    result = conn.execute(
        text("""
            INSERT INTO municipal_corporation (name, geometry)
            VALUES (:name, ST_GeomFromText(:geom, 4326))
            RETURNING id;
        """),
        {"name": name, "geom": geom.wkt}
    )
    return result.scalar()


def populate():
    municipal_data = load_geojson(MUNICIPAL_FILE)

    with engine.begin() as conn:
        for f in municipal_data["features"]:
            mc_id = insert_municipal_corp(conn, f)
            if mc_id:
                print(f"✔ Municipal Corporation inserted: {f['properties'].get('name')} (ID {mc_id})")
            else:
                print(f"❌ Skipped: {f['properties'].get('name')}")


if __name__ == "__main__":
    populate()
