import pymysql
import requests
import time
from dotenv import load_dotenv
load_dotenv()
# Database Credentials from Environment Variables
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "geFlipper")

# --- Database Schemas ---

mappings_schema = """
id INT PRIMARY KEY,
members BOOLEAN,
highalch INT,
name VARCHAR(255),
buy_limit INT
"""

# Time-series tables require composite keys (id + timestamp)
schema_5m = """
id INT,
timestamp INT,
avg_high_price INT,
high_price_volume INT,
avg_low_price INT,
low_price_volume INT,
PRIMARY KEY (id, timestamp)
"""

schema_1h = """
id INT,
timestamp INT,
avg_high_price INT,
high_price_volume INT,
avg_low_price INT,
low_price_volume INT,
PRIMARY KEY (id, timestamp)
"""

most_recent_schema = """
id INT PRIMARY KEY,
high_price INT,
high_time INT,
low_price INT,
low_time INT
"""

item_schema = """
id INT,
timestamp INT,
timestep VARCHAR(10),
avg_high_price INT,
high_price_volume INT,
avg_low_price INT,
low_price_volume INT,
PRIMARY KEY (id, timestamp, timestep)
"""

table_names = ["mappings", "5m", "1h", "recent", "item_history"]
schemas = [mappings_schema, schema_5m, schema_1h, most_recent_schema, item_schema]

HEADERS = {
    "User-Agent": "PriceTrackerScript/1.0 (contact: yanallboutros@gmail.com)"
}
BASE_URL = "https://prices.runescape.wiki/api/v1/osrs"


def get_connection(db=DB_NAME):
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=db,
        autocommit=True
    )


def make_db(db_name=DB_NAME):
    connection = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS)
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name};")
            print(f"Database '{db_name}' verified/created successfully.")
    finally:
        connection.close()


def make_table(table_name, schema_string, db_name=DB_NAME):
    connection = get_connection(db_name)
    try:
        with connection.cursor() as cursor:
            # for fresh init, 1. Drop existing table to ensure clean schema update
            drop_query = f"DROP TABLE IF EXISTS `{table_name}`;"
            cursor.execute(drop_query)
            create_query = f"CREATE TABLE IF NOT EXISTS `{table_name}` ({schema_string.strip()}) ENGINE=InnoDB;"
            cursor.execute(create_query)
            
            print(f"Table '{table_name}' verified/created successfully.")
    finally:
        connection.close()

# --- Ingestion Functions ---

def update_mappings():
    response = requests.get(f"{BASE_URL}/mapping", headers=HEADERS)
    response.raise_for_status()
    items = response.json()

    query = """
    INSERT INTO mappings (id, members, highalch, name, buy_limit)
    VALUES (%s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        members = VALUES(members),
        highalch = VALUES(highalch),
        name = VALUES(name),
        buy_limit = VALUES(buy_limit);
    """
    records = [
        (
            item.get("id"),
            1 if item.get("members") else 0,
            item.get("highalch"),
            item.get("name"),
            item.get("limit")
        )
        for item in items
    ]

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.executemany(query, records)
    print(f"[mappings] Processed {len(records)} records.")


def update_aggregated_prices(endpoint, table_name):
    """Handles both /1h and /5m endpoints"""
    response = requests.get(f"{BASE_URL}/{endpoint}", headers=HEADERS)
    response.raise_for_status()
    payload = response.json()

    ts = payload.get("timestamp")
    data = payload.get("data", {})

    query = f"""
    INSERT INTO `{table_name}` (id, timestamp, avg_high_price, high_price_volume, avg_low_price, low_price_volume)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        avg_high_price = VALUES(avg_high_price),
        high_price_volume = VALUES(high_price_volume),
        avg_low_price = VALUES(avg_low_price),
        low_price_volume = VALUES(low_price_volume);
    """
    records = [
        (
            int(item_id),
            ts,
            stats.get("avgHighPrice"),
            stats.get("highPriceVolume"),
            stats.get("avgLowPrice"),
            stats.get("lowPriceVolume")
        )
        for item_id, stats in data.items()
    ]

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.executemany(query, records)
    print(f"[{table_name}] Processed {len(records)} records for timestamp {ts}.")


def update_recent_prices():
    response = requests.get(f"{BASE_URL}/latest", headers=HEADERS)
    response.raise_for_status()
    data = response.json().get("data", {})

    query = """
    INSERT INTO recent (id, high_price, high_time, low_price, low_time)
    VALUES (%s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        high_price = VALUES(high_price),
        high_time = VALUES(high_time),
        low_price = VALUES(low_price),
        low_time = VALUES(low_time);
    """
    records = [
        (
            int(item_id),
            stats.get("high"),
            stats.get("highTime"),
            stats.get("low"),
            stats.get("lowTime")
        )
        for item_id, stats in data.items()
    ]

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.executemany(query, records)
    print(f"[recent] Processed {len(records)} records.")


def fetch_item_history(item_id, timestep="5m"):
    """Fetches historical 5m resolution timeseries for a specific item (up to 1 year back)"""
    url = f"{BASE_URL}/timeseries?timestep={timestep}&id={item_id}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    history = response.json().get("data", [])

    query = """
    INSERT INTO item_history (id, timestamp, avg_high_price, high_price_volume, avg_low_price, low_price_volume)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        avg_high_price = VALUES(avg_high_price),
        high_price_volume = VALUES(high_price_volume),
        avg_low_price = VALUES(avg_low_price),
        low_price_volume = VALUES(low_price_volume);
    """
    records = [
        (
            item_id,
            entry.get("timestamp"),
            entry.get("avgHighPrice"),
            entry.get("highPriceVolume"),
            entry.get("avgLowPrice"),
            entry.get("lowPriceVolume")
        )
        for entry in history
    ]

    if records:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, records)
        print(f"[item_history] Inserted {len(records)} 5m records for item {item_id}.")

def sync_all_item_histories(timesteps=["5m", "1h", "6h", "24h"]):
    """
    Iterates over every item ID in mappings and fetches historical timeseries
    for each requested timestep (5m, 1h, 6h, 24h).
    """
    # 1. Get list of item IDs from local database
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM mappings;")
            item_ids = [row[0] for row in cursor.fetchall()]

    print(f"[item_history] Starting historical sync for {len(item_ids)} items across timesteps: {timesteps}...")

    insert_query = """
    INSERT INTO item_history (id, timestamp, timestep, avg_high_price, high_price_volume, avg_low_price, low_price_volume)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        avg_high_price = VALUES(avg_high_price),
        high_price_volume = VALUES(high_price_volume),
        avg_low_price = VALUES(avg_low_price),
        low_price_volume = VALUES(low_price_volume);
    """

    total_records_inserted = 0

    for index, item_id in enumerate(item_ids, 1):
        for step in timesteps:
            try:
                url = f"{BASE_URL}/timeseries?timestep={step}&id={item_id}"
                response = requests.get(url, headers=HEADERS)
                if response.status_code != 200:
                    continue

                history = response.json().get("data", [])
                if not history:
                    continue

                records = [
                    (
                        item_id,
                        entry.get("timestamp"),
                        step,
                        entry.get("avgHighPrice"),
                        entry.get("highPriceVolume"),
                        entry.get("avgLowPrice"),
                        entry.get("lowPriceVolume")
                    )
                    for entry in history
                ]

                with get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.executemany(insert_query, records)

                total_records_inserted += len(records)
                time.sleep(0.05)  # Rate limiting safety delay (~20 req/s max)

            except Exception as e:
                print(f"[item_history] Error processing item {item_id} (timestep: {step}): {e}")

        if index % 100 == 0 or index == len(item_ids):
            print(f"[item_history] Progress: {index}/{len(item_ids)} items processed ({total_records_inserted} total rows updated).")

    print(f"[item_history] Complete. Total records synced: {total_records_inserted}.")


def main():
    make_db()
    for table_name, schema in zip(table_names, schemas):
        make_table(table_name, schema)

    # Populate tables from API
    update_mappings()
    update_aggregated_prices(endpoint="5m", table_name="5m")
    update_aggregated_prices(endpoint="1h", table_name="1h")
    update_recent_prices()
    sync_all_item_histories(timesteps=["5m", "1h", "6h", "24h"])

    # Optional: Example backfill for Abyssal Whip (ID: 4151)
    # fetch_item_history(4151, timestep="5m")


if __name__ == "__main__":
    main()
