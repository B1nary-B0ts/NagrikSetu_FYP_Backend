import json
from shapely.geometry import shape
from sqlalchemy import create_engine, text

DB_URL = "postgresql://postgres:postgres@localhost:5433/civic_issues_db"
engine = create_engine(DB_URL)

MUNICIPAL_FILE = "thane.geojson"
# WARD_FILE = "wards_mumbai.geojson"


def load_geojson(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# def create_tables(conn):
#     # Enable PostGIS
#     conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))

#     conn.execute(text("""
#         CREATE TABLE IF NOT EXISTS municipal_corporation (
#             id SERIAL PRIMARY KEY,
#             name VARCHAR(100),
#             geometry geometry(MULTIPOLYGON, 4326)
#         );
#     """))

#     conn.execute(text("""
#         CREATE TABLE IF NOT EXISTS ward (
#             id SERIAL PRIMARY KEY,
#             name VARCHAR(100),
#             municipal_corp_id INTEGER REFERENCES municipal_corporation(id) ON DELETE CASCADE,
#             geometry geometry(MULTIPOLYGON, 4326)
#         );
#     """))

#     # Add spatial indexes
#     conn.execute(text("CREATE INDEX IF NOT EXISTS mc_geom_idx ON municipal_corporation USING GIST (geometry);"))
#     conn.execute(text("CREATE INDEX IF NOT EXISTS ward_geom_idx ON ward USING GIST (geometry);"))

#     print("PostGIS tables created with spatial indexes.")


def insert_municipal_corp(conn, feature):
    name = feature["properties"].get("name")
    geom = shape(feature["geometry"]).wkt

    result = conn.execute(
        text("""
            INSERT INTO municipal_corporation (name, geometry)
            VALUES (:name, ST_GeomFromText(:geom, 4326))
            RETURNING id;
        """),
        {"name": name, "geom": geom}
    )

    return result.scalar()


# def insert_ward(conn, feature, municipal_corp_id):
#     name = feature["properties"].get("name")
#     geom = shape(feature["geometry"]).wkt

#     conn.execute(
#         text("""
#             INSERT INTO ward (name, municipal_corp_id, geometry)
#             VALUES (:name, :mcid, ST_GeomFromText(:geom, 4326));
#         """),
#         {"name": name, "mcid": municipal_corp_id, "geom": geom}
#     )


def populate():
    municipal_data = load_geojson(MUNICIPAL_FILE)
    # ward_data = load_geojson(WARD_FILE)

    with engine.begin() as conn:

        # create_tables(conn)

        # mc_feature = municipal_data["features"][0]
        # mc_id = insert_municipal_corp(conn, mc_feature)
        # print(f"✔ Inserted Municipal Corporation (ID {mc_id})")

        for f in municipal_data["features"]:
            mc_id = insert_municipal_corp(conn, f)
            print(f"✔ Municipal Corporation inserted: {f['properties'].get('name')} (ID {mc_id})")

    

        # for f in ward_data["features"]:
        #     insert_ward(conn, f, mc_id)
        #     print(f"✔ Ward inserted: {f['properties'].get('name')}")

        # print("🎉 All wards inserted successfully with PostGIS geometry!")


if __name__ == "__main__":
    populate()
