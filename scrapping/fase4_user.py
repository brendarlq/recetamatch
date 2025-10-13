import requests
import sqlite3
import time
import os

DB_PATH = "foodcom.db"
BATCH_SIZE = 1000
CHECKPOINT_FILE = "users_checkpoint.txt"
FAILED_FILE = "failed_users.txt"

def create_users_table():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            profile_url TEXT,
            avatar_url TEXT,
            date_joined TEXT,
            followers INTEGER,
            following INTEGER,
            total_activities INTEGER,
            total_reviews INTEGER,
            total_photos INTEGER,
            total_likes INTEGER
        )
    """)
    conn.commit()
    conn.close()

def fetch_user_feed(user_id, page=1, size=20, retries=3):
    url = f"https://api.food.com/external/v1/members/{user_id}/feed"
    params = {"pn": page, "size": size, "blockGdpr": "false"}
    headers = {"User-Agent": "Mozilla/5.0"}

    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=20)
            if r.status_code == 200:
                return r.json()
            else:
                print(f"❌ Error {r.status_code} en usuario {user_id}, intento {attempt}")
        except Exception as e:
            print(f"⚠️ Error en usuario {user_id}, intento {attempt}: {e}")
        time.sleep(2)

    # Si no se pudo traer nada en los 3 intentos, guardamos en archivo
    with open(FAILED_FILE, "a") as f:
        f.write(f"{user_id}\n")
    print(f"❌ Usuario {user_id} no se pudo descargar, guardado en {FAILED_FILE}")
    return None

def summarize_user(user_id):
    page = 1
    total_activities = 0
    total_reviews = 0
    total_photos = 0
    total_likes = 0
    name = None
    profile_url = None
    avatar_url = None
    date_joined = None
    followers = None
    following = None

    while True:
        data = fetch_user_feed(user_id, page)
        if not data or "data" not in data:
            # si en la primera página no trae nada, abortamos rápido
            if page == 1:
                print(f"⚠️ Usuario {user_id} no tiene datos (salteado).")
                return {
                    "user_id": user_id,
                    "name": None,
                    "profile_url": None,
                    "avatar_url": None,
                    "date_joined": None,
                    "followers": 0,
                    "following": 0,
                    "total_activities": 0,
                    "total_reviews": 0,
                    "total_photos": 0,
                    "total_likes": 0,
                }
            break

        # Info del usuario (solo viene en la primera página)
        if page == 1 and "user" in data.get("data", {}):
            user_info = data["data"]["user"]
            date_joined = user_info.get("createdOn")
            followers = user_info.get("followerCount", 0)
            following = user_info.get("followingCount", 0)

        items = data["data"].get("items", [])
        if not items:
            break

        total_activities += len(items)
        for item in items:
            if not name:
                name = item.get("memberName")
                profile_url = item.get("memberProfileUrl")
                avatar_url = item.get("memberAvatar")
            if item.get("type") == "review":
                total_reviews += 1
            elif item.get("type") == "photo":
                total_photos += 1
            total_likes += item.get("counts", {}).get("like", 0)

        if len(items) < 20:
            break
        page += 1
        time.sleep(0.3)

    return {
        "user_id": user_id,
        "name": name,
        "profile_url": profile_url,
        "avatar_url": avatar_url,
        "date_joined": date_joined,
        "followers": followers,
        "following": following,
        "total_activities": total_activities,
        "total_reviews": total_reviews,
        "total_photos": total_photos,
        "total_likes": total_likes,
    }

def save_users(batch):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executemany("""
        INSERT OR REPLACE INTO users (
            user_id, name, profile_url, avatar_url, date_joined,
            followers, following, total_activities, total_reviews, total_photos, total_likes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        (
            u["user_id"], u["name"], u["profile_url"], u["avatar_url"],
            u["date_joined"], u["followers"], u["following"],
            u["total_activities"], u["total_reviews"], u["total_photos"], u["total_likes"]
        ) for u in batch
    ])
    conn.commit()
    conn.close()

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            return int(f.read().strip())
    return 0

def save_checkpoint(index):
    with open(CHECKPOINT_FILE, "w") as f:
        f.write(str(index))

def main():
    create_users_table()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT author_id FROM reviews WHERE author_id IS NOT NULL")
    all_user_ids = [row[0] for row in cur.fetchall()]
    conn.close()

    start_index = load_checkpoint()
    total_users = len(all_user_ids)
    print(f"📊 Usuarios a procesar: {total_users}, reanudando en {start_index}")

    batch = []
    processed = start_index

    for idx, user_id in enumerate(all_user_ids[start_index:], start=start_index):
        print(f"➡️ Procesando usuario {user_id} ({idx+1}/{total_users})")
        summary = summarize_user(user_id)
        if summary["name"]:  # solo guardamos si existe info
            batch.append(summary)
        processed += 1

        if len(batch) >= BATCH_SIZE:
            save_users(batch)
            save_checkpoint(processed)
            print(f"💾 Guardados {processed}/{total_users} usuarios...")
            batch = []

    if batch:
        save_users(batch)
        save_checkpoint(processed)
        print(f"💾 Guardados {processed}/{total_users} usuarios (final).")

    print("🎉 Proceso completo.")

if __name__ == "__main__":
    main()
