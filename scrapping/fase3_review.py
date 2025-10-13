import sqlite3
import requests
import time
import os

DB_PATH = "foodcom.db"
CHECKPOINT_FILE = "checkpoint.txt"
FAILED_FILE = "failed_reviews.txt"

def create_table():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY,
        recipe_id INTEGER,
        author_id INTEGER,
        author TEXT,
        rating INTEGER,
        likes INTEGER,
        submitted TEXT,
        text TEXT
    )
    """)
    conn.commit()
    conn.close()

def fetch_reviews(recipe_id, retries=3):
    """Descarga todas las reviews de una receta con paginación y reintentos."""
    url_template = f"https://api.food.com/external/v1/recipes/{recipe_id}/feed/reviews"
    page = 1
    all_reviews = []
    total = None

    for attempt in range(1, retries + 1):
        try:
            while True:
                params = {"pn": page, "sortBy": "-time"}
                r = requests.get(url_template, params=params, timeout=20)
                if r.status_code != 200:
                    print(f"❌ Error {r.status_code} en recipe {recipe_id}, page {page}")
                    return []

                data = r.json()
                if total is None:
                    total = data.get("total", 0)

                items = data.get("data", {}).get("items", [])
                if not items:
                    break

                for rev in items:
                    all_reviews.append((
                        str(rev.get("id")),              # id de la review
                        recipe_id,                       # receta
                        rev.get("memberId"),             # id del autor
                        rev.get("memberName"),           # nombre del autor
                        rev.get("rating"),               # rating
                        rev.get("counts", {}).get("like", 0),
                        rev.get("submitted"),            # fecha
                        rev.get("text", "").replace("\n", " ").strip()
                    ))

                if len(all_reviews) >= total:
                    break

                page += 1
                time.sleep(0.5)  # anti-baneo

            return all_reviews

        except Exception as e:
            print(f"⚠️ Error en recipe {recipe_id}, intento {attempt}/{retries}: {e}")
            time.sleep(2)

    # Si llega acá, falló en todos los intentos
    with open(FAILED_FILE, "a") as f:
        f.write(f"{recipe_id}\n")
    print(f"❌ No se pudo traer reviews de receta {recipe_id}, guardado en {FAILED_FILE}")
    return []

def save_reviews(batch):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executemany("""
        INSERT OR REPLACE INTO reviews 
        (id, recipe_id, author_id, author, rating, likes, submitted, text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()
    conn.close()

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            return int(f.read().strip())
    return None

def save_checkpoint(recipe_id):
    with open(CHECKPOINT_FILE, "w") as f:
        f.write(str(recipe_id))

def main():
    create_table()

    # cargar todos los recipe_id
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT recipe_id FROM recipes ORDER BY recipe_id")
    recipe_ids = [row[0] for row in cur.fetchall()]
    conn.close()

    total_recipes = len(recipe_ids)
    total_saved = 0

    # cargar checkpoint
    last_recipe = load_checkpoint()
    if last_recipe and last_recipe in recipe_ids:
        start_index = recipe_ids.index(last_recipe) + 1
        print(f"🔄 Reanudando desde recipe {last_recipe} (índice {start_index})")
    else:
        start_index = 0
        print("🚀 Comenzando desde el inicio")

    for i, rid in enumerate(recipe_ids[start_index:], start=start_index + 1):
        reviews = fetch_reviews(rid)
        if reviews:
            save_reviews(reviews)
            total_saved += len(reviews)
            print(f"💾 Guardadas {len(reviews)} reviews para receta {rid} "
                  f"(Total acumulado: {total_saved})")
        else:
            print(f"ℹ️ Receta {rid} no tiene reviews o falló la descarga")

        # guardar checkpoint después de cada receta
        save_checkpoint(rid)

        print(f"✅ Receta {i}/{total_recipes} procesada. "
              f"Faltan {total_recipes - i} recetas.")

    print(f"🎉 Proceso completo: {total_saved} reviews guardadas en total "
          f"para {total_recipes} recetas.")

if __name__ == "__main__":
    main()
