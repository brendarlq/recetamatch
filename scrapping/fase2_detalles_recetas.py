import requests
import sqlite3
import time
import os

DB_PATH = "foodcom.db"
CHECKPOINT_FILE = "checkpoint_detalles.txt"
FAILED_FILE = "failed_recipes.txt"

def fetch_recipe_details(recipe_url, retries=3):
    url = recipe_url.rstrip("/") + "/as-json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/140.0.0.0 Safari/537.36"
    }
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code == 200:
                return r.json()
            else:
                print(f"⚠️ Error {r.status_code} en {url}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"⏳ Error {e}, intento {attempt+1}/{retries}")
            time.sleep(2)
    return None

def save_failed(recipe_id):
    """Guarda el ID de receta fallida en archivo de texto."""
    with open(FAILED_FILE, "a") as f:
        f.write(str(recipe_id) + "\n")

def save_recipe(recipe_json, recipe_url):
    recipe = recipe_json.get("recipe", {})
    jsonLd = recipe.get("jsonLd", {})

    recipe_id = recipe.get("id")
    if not recipe_id:
        return

    # === Detalles ===
    title = jsonLd.get("name")
    description = jsonLd.get("description")
    prepTime = jsonLd.get("prepTime")
    cookTime = jsonLd.get("cookTime")
    totalTime = jsonLd.get("totalTime")
    author = jsonLd.get("author")
    image = jsonLd.get("image")
    category = jsonLd.get("recipeCategory")
    keywords = jsonLd.get("keywords")

    total_ingredients = len(recipe.get("ingredients", []))
    total_steps = len(recipe.get("directions", []))
    total_reviews = recipe_json.get("reviewFeed", {}).get("total", 0)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # === Tabla details ===
    cur.execute("""
        CREATE TABLE IF NOT EXISTS details (
            recipe_id INTEGER PRIMARY KEY,
            url TEXT,
            title TEXT,
            description TEXT,
            prep_time TEXT,
            cook_time TEXT,
            total_time TEXT,
            author TEXT,
            image TEXT,
            category TEXT,
            keywords TEXT,
            total_ingredients INTEGER,
            total_steps INTEGER,
            total_reviews INTEGER
        )
    """)

    cur.execute("""
        INSERT OR REPLACE INTO details 
        (recipe_id, url, title, description, prep_time, cook_time, total_time, author, image, category, keywords, total_ingredients, total_steps, total_reviews)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (recipe_id, recipe_url, title, description, prepTime, cookTime, totalTime, author, image, category, keywords, total_ingredients, total_steps, total_reviews))

    # === Ingredientes ===
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id INTEGER,
            quantity TEXT,
            text TEXT,
            category_texts TEXT
        )
    """)
    cur.execute("DELETE FROM ingredients WHERE recipe_id = ?", (recipe_id,))

    for ing in recipe.get("ingredients", []):
        qty = ing.get("quantity", "").strip()
        text = ing.get("ingredText", "").strip()

        category_texts = []
        if ing.get("hyperlinkFoodTextList"):
            for key, val in ing["hyperlinkFoodTextList"].items():
                placeholder = f"${key}$"
                replacement = val.get("text", "")
                category_texts.append(replacement)
                text = text.replace(placeholder, replacement)

        cur.execute(
            "INSERT INTO ingredients (recipe_id, quantity, text, category_texts) VALUES (?, ?, ?, ?)",
            (recipe_id, qty, text, ", ".join(category_texts) if category_texts else None)
        )
    
    # === Instrucciones ===
    cur.execute("""
        CREATE TABLE IF NOT EXISTS instructions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id INTEGER,
            step_num INTEGER,
            step_text TEXT
        )
    """)
    cur.execute("DELETE FROM instructions WHERE recipe_id = ?", (recipe_id,))

    for step in recipe.get("directions", []):
        step_num = step.get("stepNum")
        step_text = step.get("stepText") or step.get("text")
        cur.execute("INSERT INTO instructions (recipe_id, step_num, step_text) VALUES (?, ?, ?)",
                    (recipe_id, step_num, step_text))

    conn.commit()
    conn.close()

    print(f"✅ Guardado receta {recipe_id} | {title} | Ingredientes: {total_ingredients} | Pasos: {total_steps} | Reviews: {total_reviews}")

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            return int(f.read().strip())
    return None

def save_checkpoint(recipe_id):
    with open(CHECKPOINT_FILE, "w") as f:
        f.write(str(recipe_id))

def process_all_recipes(limit=None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT recipe_id, url FROM recipes ORDER BY recipe_id")
    rows = cur.fetchall()
    conn.close()

    total = len(rows)
    print(f"📌 Procesando {total} recetas...")
    if limit:
        rows = rows[:limit]

    # cargar checkpoint
    last_recipe = load_checkpoint()
    if last_recipe:
        start_index = next((i for i, (rid, _) in enumerate(rows) if rid == last_recipe), -1) + 1
        print(f"🔄 Reanudando desde recipe {last_recipe} (índice {start_index})")
    else:
        start_index = 0
        print("🚀 Comenzando desde el inicio")

    for i, (rid, url) in enumerate(rows[start_index:], start=start_index + 1):
        data = fetch_recipe_details(url)
        if data:
            save_recipe(data, url)
        else:
            print(f"⚠️ No se pudo obtener la receta {rid}, se omite.")
            save_failed(rid)  # 👉 guardar en archivo de fallos

        save_checkpoint(rid)  # checkpoint después de cada receta

        if i % 50 == 0:
            print(f"--- Progreso: {i}/{total} recetas ---")
        time.sleep(0.5)

    print("🎉 Proceso completo.")

if __name__ == "__main__":
    process_all_recipes(limit=None)
