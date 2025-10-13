#!/usr/bin/env python3
# fase1_recetas_100k.py
# Descarga hasta 100.000 recetas desde api.food.com usando collectionId=17
# Guarda en SQLite en bloques (BATCH_SIZE). Incluye checkpoint para reanudar.

import requests
import sqlite3
import time
import math
import json
import os
from requests.adapters import HTTPAdapter, Retry

DB_PATH = "foodcom.db"
BATCH_SIZE = 1000
MAX_RECIPES = 100000
RECIPES_PER_PAGE = 10  # confirmado: endpoint devuelve 10 por página
CHECKPOINT_PATH = "progress.json"
COLLECTION_ID = 17
SLEEP_BETWEEN_PAGES = 0.5  # podés ajustar a 0.2 si querés más rápido (más riesgo de baneo)

# --- sesión con retries ---
def make_session(retries=3, backoff=0.5, status_forcelist=(500,502,503,504)):
    s = requests.Session()
    retry = Retry(total=retries, backoff_factor=backoff, status_forcelist=status_forcelist)
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    s.headers.update({"User-Agent": "Mozilla/5.0 (compatible; food-scraper/1.0)"})
    return s

SESSION = make_session()

# --- DB ---
def create_tables():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS recipes (
        recipe_id INTEGER PRIMARY KEY,
        title TEXT,
        description TEXT,
        image_url TEXT,
        url TEXT,
        category TEXT,
        rating REAL,
        num_ratings INTEGER,
        prep_time INTEGER,
        cook_time INTEGER,
        total_time INTEGER,
        author_id INTEGER,
        author_name TEXT,
        author_url TEXT,
        author_avatar TEXT
    )
    """)
    conn.commit()
    conn.close()

def save_batch(batch):
    if not batch:
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executemany("""
        INSERT OR REPLACE INTO recipes (
            recipe_id, title, description, image_url, url,
            category, rating, num_ratings,
            prep_time, cook_time, total_time,
            author_id, author_name, author_url, author_avatar
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()
    conn.close()

# --- checkpoint ---
def load_checkpoint():
    if os.path.exists(CHECKPOINT_PATH):
        try:
            with open(CHECKPOINT_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_page": 0, "total_saved": 0}

def save_checkpoint(last_page, total_saved):
    data = {"last_page": last_page, "total_saved": total_saved}
    with open(CHECKPOINT_PATH, "w") as f:
        json.dump(data, f)

# --- fetch ---
def fetch_recipes(page, collection_id=COLLECTION_ID):
    url = "https://api.food.com/services/mobile/fdc/search/sectionfront"
    params = {
        "pn": page,
        "recordType": "Recipe",
        "collectionId": collection_id
    }
    try:
        r = SESSION.get(url, params=params, timeout=15)
        if r.status_code != 200:
            print(f"⚠️  Status {r.status_code} en página {page}")
            return []
        data = r.json()
        return data.get("response", {}).get("results", [])
    except Exception as e:
        print(f"⚠️  Error de conexión en página {page}: {e}")
        return []

# --- crawler principal ---
def crawl_recipes():
    create_tables()
    checkpoint = load_checkpoint()
    last_page = int(checkpoint.get("last_page", 0))
    total_saved = int(checkpoint.get("total_saved", 0))

    total_pages = math.ceil(MAX_RECIPES / RECIPES_PER_PAGE)

    print(f"Inicio: total_saved={total_saved}, last_page={last_page}")
    print(f"Objetivo: {MAX_RECIPES} recetas -> páginas necesarias: {total_pages}")

    batch = []
    page = last_page + 1 if last_page >= 1 else 1

    try:
        while page <= total_pages and total_saved < MAX_RECIPES:
            recipes = fetch_recipes(page)
            if not recipes:
                print(f"✅ El endpoint no devolvió recetas en la página {page}. Terminando.")
                break

            for r in recipes:
                try:
                    recipe_id = int(r.get("recipe_id") or r.get("id") or 0)
                except:
                    recipe_id = None

                batch.append((
                    recipe_id,
                    r.get("title"),
                    r.get("description"),
                    r.get("recipe_photo_url"),
                    r.get("record_url"),
                    r.get("primary_category_name"),
                    float(r.get("main_rating", 0)) if r.get("main_rating") not in (None, "") else None,
                    int(r.get("main_num_ratings", 0)) if r.get("main_num_ratings") not in (None, "") else 0,
                    int(r.get("recipe_preptime", 0)) if r.get("recipe_preptime") not in (None, "") else None,
                    int(r.get("recipe_cooktime", 0)) if r.get("recipe_cooktime") not in (None, "") else None,
                    int(r.get("recipe_totaltime", 0)) if r.get("recipe_totaltime") not in (None, "") else None,
                    int(r.get("main_userid")) if r.get("main_userid") not in (None, "") else None,
                    r.get("main_username"),
                    r.get("recipe_user_url"),
                    r.get("user_avatar_url"),
                ))

                if total_saved + len(batch) >= MAX_RECIPES:
                    needed = MAX_RECIPES - total_saved
                    if needed > 0:
                        batch = batch[:needed]
                        save_batch(batch)
                        total_saved += len(batch)
                    save_checkpoint(page, total_saved)
                    print(f"💾 Guardadas {total_saved}/{MAX_RECIPES} recetas (Página {page}/{total_pages})")
                    print("🎉 Límite alcanzado. Terminando.")
                    return

            if len(batch) >= BATCH_SIZE:
                save_batch(batch[:BATCH_SIZE])
                total_saved += BATCH_SIZE
                batch = batch[BATCH_SIZE:]
                save_checkpoint(page, total_saved)
                print(f"💾 Guardadas {total_saved}/{MAX_RECIPES} recetas (Página {page}/{total_pages})")

            save_checkpoint(page, total_saved)

            page += 1
            time.sleep(SLEEP_BETWEEN_PAGES)

        if batch:
            save_batch(batch)
            total_saved += len(batch)
            save_checkpoint(page-1, total_saved)
            print(f"💾 Guardadas {total_saved}/{MAX_RECIPES} recetas (final).")

        print(f"🎉 Descarga completa: {total_saved} recetas.")
    except KeyboardInterrupt:
        print("⏸ Interrumpido por el usuario. Guardando checkpoint...")
        save_checkpoint(page-1, total_saved)
    except Exception as e:
        print(f"❌ Error inesperado: {e}. Guardando checkpoint...")
        save_checkpoint(page-1, total_saved)

if __name__ == "__main__":
    crawl_recipes()
