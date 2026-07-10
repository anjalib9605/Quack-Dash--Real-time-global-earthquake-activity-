import requests, os
import pandas as pd
from datetime import timedelta
import pycountry
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# ==========================================================
# Load & Update Dataset
# ==========================================================

# Extra aliases for USGS place names
ALIASES = {
    "United States": [
        "Alaska", "California", "Nevada", "Hawaii",
        "Oklahoma", "Puerto Rico", "Washington",
        "Oregon", "Texas", "Montana", "Idaho"
    ],

    "Japan": [
        "Honshu", "Hokkaido", "Kyushu",
        "Ryukyu", "Bonin", "Izu", "Japan", "Kyoto"
    ],

    "Russia": [
        "Kuril", "Kamchatka", "Russia"
    ],

    "Indonesia": [
        "Java", "Sumatra", "Sulawesi",
        "Banda Sea", "Flores",
        "Indonesia", "Molucca"
    ],

    "New Zealand": [
        "Kermadec", "New Zealand"
    ],

    "Papua New Guinea": [
        "New Britain",
        "New Ireland",
        "Papua New Guinea"
    ],

    "Philippines": [
        "Luzon",
        "Mindanao",
        "Philippines"
    ]
}

# Official country names
COUNTRIES = sorted(
    [c.name for c in pycountry.countries],
    key=len,
    reverse=True
)

def get_country(place):

      if pd.isna(place):
          return "Other"

      place = place.lower()

      # Check aliases first
      for country, words in ALIASES.items():

          for word in words:

              if word.lower() in place:
                  return country

      # Then check official country names
      for country in COUNTRIES:

          if country.lower() in place:
              return country

      return "Other"


def update_dataset():

    engine = create_engine(DATABASE_URL)

    # Get latest earthquake time from PostgreSQL
    latest_time = pd.read_sql(
        "SELECT MAX(time) AS latest_time FROM earthquakes",
        engine
    )["latest_time"][0]

    latest_time = pd.to_datetime(latest_time).tz_localize(None)

    print(f"Checking for earthquakes after {latest_time}")

    start_time = (
        latest_time + timedelta(seconds=1)
    ).strftime("%Y-%m-%dT%H:%M:%S")

    url = (
        "https://earthquake.usgs.gov/fdsnws/event/1/query"
        f"?format=geojson"
        f"&starttime={start_time}"
    )

    try:

        response = requests.get(url, timeout=20)
        response.raise_for_status()

        data = response.json()

        if not data["features"]:
            print("No new earthquakes found.")
            return 0

        print(f"Found {len(data['features'])} new earthquakes.")

        rows = []

        for feature in data["features"]:

            p = feature["properties"]
            g = feature["geometry"]

            rows.append({

                "time": pd.to_datetime(p["time"], unit="ms").tz_localize(None),

                "latitude": g["coordinates"][1],
                "longitude": g["coordinates"][0],
                "depth": g["coordinates"][2],

                "mag": p.get("mag"),
                "magType": p.get("magType"),

                "nst": p.get("nst"),
                "gap": p.get("gap"),
                "dmin": p.get("dmin"),
                "rms": p.get("rms"),

                "net": p.get("net"),
                "id": feature.get("id"),

                "updated": pd.to_datetime(
                    p["updated"], unit="ms"
                ).tz_localize(None),

                "place": p.get("place"),
                "type": p.get("type"),

                "horizontalError": p.get("horizontalError"),
                "depthError": p.get("depthError"),
                "magError": p.get("magError"),
                "magNst": p.get("magNst"),

                "status": p.get("status"),
                "locationSource": p.get("net"),
                "magSource": p.get("net")

            })

        new_df = pd.DataFrame(rows)

        # Extra columns
        new_df["date"] = new_df["time"].dt.normalize()
        new_df["country"] = new_df["place"].apply(get_country)

        # Extra safety against duplicates
        # existing_ids = pd.read_sql(
        #     "SELECT id FROM earthquakes",
        #     engine
        # )

        # new_df = new_df[
        #     ~new_df["id"].isin(existing_ids["id"])
        # ]

        if new_df.empty:

            print("No unique earthquakes to insert.")
            return

        new_df.to_sql(
            "earthquakes",
            engine,
            if_exists="append",
            index=False
        )
        print(f"Inserted {len(new_df)} new earthquakes.")
        return len(new_df)

    except Exception as e:

        print("Could not update database.")
        print(e)

if __name__ == "__main__":
    update_dataset()