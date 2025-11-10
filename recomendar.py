## version: 1.0 -- recomendaciones al azar

from flask import request
from math import log
import sqlite3
import os
import random

import metricas


#DATABASE_FILE = os.path.dirname(os.path.abspath("__file__")) + "/datos/qll.db"
DATABASE_FILE = os.path.dirname(__file__) + "/datos/foodcom.db"

###

def sql_execute(query, params=None):
    con = sqlite3.connect(DATABASE_FILE)
    cur = con.cursor()
    if params:
        res = cur.execute(query, params)
    else:
        res = cur.execute(query)

    con.commit()
    con.close()
    return res

def sql_select(query, params=None):
    con = sqlite3.connect(DATABASE_FILE)
    con.row_factory = sqlite3.Row # esto es para que devuelva registros en el fetchall
    cur = con.cursor()
    if params:
        res = cur.execute(query, params)
    else:
        res = cur.execute(query)

    ret = res.fetchall()
    con.close()
    return ret

###

def crear_usuario(name):
    query = "INSERT INTO users(name) VALUES (?) ON CONFLICT DO NOTHING;" # si el name existe, se produce un conflicto y le digo que no haga nada
    sql_execute(query, [name])
    return

def insertar_review(recipe_id, author_id, rating):
    query = f"INSERT INTO reviews(recipe_id, author, rating) VALUES (?, ?, ?) ON CONFLICT (recipe_id, author) DO UPDATE SET rating=?;" # si el rating existia lo actualizo
    sql_execute(query, [recipe_id, author_id, rating, rating])
    return

def reset_usuario(author_id):
    query = f"DELETE FROM reviews WHERE author_id = ?;"
    sql_execute(query, [author_id])
    return

def obtener_receta(recipe_id):
    query = "SELECT * FROM recipes WHERE recipe_id = ?;"
    recipe = sql_select(query, [recipe_id])[0]
    return recipe

def items_valorados(author_id):
    query = f"SELECT recipe_id FROM reviews WHERE author = ? AND rating > 0"
    rows = sql_select(query, [author_id])
    return [i["recipe_id"] for i in rows]

def items_vistos(author_id):
    query = f"SELECT recipe_id FROM reviews WHERE author = ? AND rating = 0"
    rows = sql_select(query, [author_id])
    return [i["recipe_id"] for i in rows]

def items_desconocidos(author_id):
    query = f"SELECT recipe_id FROM recipes WHERE recipe_id NOT IN (SELECT recipe_id FROM reviews WHERE author = ? AND rating IS NOT NULL)"
    rows = sql_select(query, [author_id])
    return [i["recipe_id"] for i in rows]

def datos_recipes(id_recipes):
    query = f"SELECT DISTINCT * FROM recipes WHERE recipe_id IN ({','.join(['?']*len(id_recipes))})"
    recipes = sql_select(query, id_recipes)
    return recipes

def buscar_recetas(query):
    texto = f"%{query.lower()}%"
    sql = """
        SELECT recipe_id, title
        FROM recipes
        WHERE LOWER(title) LIKE ?
        ORDER BY num_ratings DESC
        LIMIT 15
    """
    return sql_select(sql, (texto,))



###

def recomendador_azar(id_usuario, recipes_relevantes, recipes_desconocidos, N=16):
    id_recipes = random.sample(recipes_desconocidos, N)
    return id_recipes

def recomendador_top_n(id_usuario, recipes_relevantes, recipes_desconocidos, N):
    res = sql_select(f"""
        SELECT recipe_id
        FROM recipes
        WHERE recipe_id IN ({",".join("?"*len(recipes_desconocidos))})
        ORDER BY (rating * log(num_ratings + 1)) DESC
        LIMIT ?
    """, recipes_desconocidos + [N])
    return [r["recipe_id"] for r in res]

def recomendador_pares(id_usuario, recipes_relevantes, recipes_desconocidos, N):
    if len(recipes_relevantes) == 0:
        return recomendador_top_n(id_usuario, recipes_relevantes, recipes_desconocidos, N)

    res = sql_select(f"""
        SELECT recipe_id
        FROM reviews AS r1
        JOIN reviews AS r2 ON r1.author = r2.author
        WHERE r1.recipe_id IN ({",".join("?"*len(recipes_relevantes))})
          AND r2.recipe_id IN ({",".join("?"*len(recipes_desconocidos))})
          AND r1.recipe_id != r2.recipe_id
          AND r1.rating > 3
          AND r2.rating > 3
        GROUP BY recipe_id
        ORDER BY count(*) DESC
        LIMIT ?
    """, recipes_relevantes + recipes_desconocidos + [N])

    return [r["recipe_id"] for r in res]

### Router basado en cookie ###
def recomendar(id_usuario, relevantes=None, desconocidos=None, N=16):
    relevantes = relevantes or items_valorados(id_usuario)
    desconocidos = desconocidos or items_desconocidos(id_usuario)

    algoritmo = request.cookies.get("algoritmo", "azar")

    if algoritmo == "top_n":
        return recomendador_top_n(id_usuario, relevantes, desconocidos, N)
    elif algoritmo == "pares":
        return recomendador_pares(id_usuario, relevantes, desconocidos, N)
    else:
        return recomendador_azar(id_usuario, relevantes, desconocidos, N)

def recomendador_contexto(id_usuario, id_recipe, recipes_relevantes=None, recipes_desconocidos=None, N=4):
    recipes_relevantes = recipes_relevantes or items_valorados(id_usuario)
    recipes_desconocidos = recipes_desconocidos or items_desconocidos(id_usuario)

    algoritmo = request.cookies.get("algoritmo", "azar")

    funcs = {
        "azar": recomendador_azar,
        "top_n": recomendador_top_n,
        "pares": recomendador_pares,
    }

    func = funcs.get(algoritmo, recomendador_azar)

    return func(id_usuario, recipes_relevantes, recipes_desconocidos, N)

ALGORITHM_FUNCTIONS = {
    "azar": recomendador_azar,
    "top_n": recomendador_top_n,
    "pares": recomendador_pares, 
}

###

def test(id_usuario):
    recipes_relevantes = items_valorados(id_usuario)
    recipes_desconocidos = items_vistos(id_usuario) + items_desconocidos(id_usuario)

    random.shuffle(recipes_relevantes)

    corte = int(len(recipes_relevantes)*0.8)
    recipes_relevantes_training = recipes_relevantes[:corte]
    recipes_relevantes_testing = recipes_relevantes[corte:] + recipes_desconocidos

    recomendacion = recomendar(id_usuario, recipes_relevantes_training, recipes_relevantes_testing, 20)

    relevance_scores = []
    for id_recipe in recomendacion:
        res = sql_select("SELECT rating FROM reviews WHERE author = ? AND recipe_id = ?;", [id_usuario, id_recipe])
        if res is not None and len(res) > 0:
            rating = res[0][0]
        else:
            rating = 0


        relevance_scores.append(rating)
    score = metricas.normalized_discounted_cumulative_gain(relevance_scores)
    return score

if __name__ == '__main__':
    id_users = sql_select("SELECT name FROM users WHERE (SELECT count(*) FROM reviews WHERE author = users.name) >= 100 limit 50;")
    id_users = [i["name"] for i in id_users]

    scores = []
    for name in id_users:
        score = test(name)
        scores.append(score)
        print(f"{name} >> {score:.6f}")

    print(f"NDCG: {sum(scores)/len(scores):.6f}")


