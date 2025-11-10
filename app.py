from flask import Flask, request, render_template, make_response, redirect, jsonify
from datetime import date
import recomendar

app = Flask(__name__)
app.debug = True

LAST_UPDATE = "09/11/2025"
ALGORITHMS = {
    "azar": "🌀 Azar",
    "top_n": "⭐ Top N",
    "pares": "🤝 Pares",
}

@app.get('/')
def get_index():
    return render_template('login.html')

@app.post('/')
def post_index():
    name = request.form.get('name', None)

    if name: # si me mandaron el id_lector
        recomendar.crear_usuario(name)

        # mando al usuario a la página de recomendaciones
        res = make_response(redirect("/recomendaciones"))

        # pongo el name en una cookie para recordarlo
        res.set_cookie('name', name)
        return res

    # sino, le muestro el formulario de login
    return render_template('login.html', LAST_UPDATE=LAST_UPDATE)

@app.get('/recomendaciones')
def get_recomendaciones():
    name = request.cookies.get('name')

    id_recipes = recomendar.recomendar(name)

    # pongo recipe vistos con rating = 0
    for id_recipe in id_recipes:
        recomendar.insertar_review(id_recipe, name, 0)

    recipes_recomendados = recomendar.datos_recipes(id_recipes)
    cant_valorados = len(recomendar.items_valorados(name))
    cant_vistos = len(recomendar.items_vistos(name))

    return render_template("recomendaciones.html", recipes_recomendados=recipes_recomendados, name=name, cant_valorados=cant_valorados, cant_vistos=cant_vistos, LAST_UPDATE=LAST_UPDATE)

@app.get('/logout')
def logout():
    # Crea una respuesta que redirige al login
    res = make_response(redirect('/'))
    # Elimina la cookie del usuario
    res.delete_cookie('name')
    return res

@app.get('/recomendaciones/<string:receipe_id>')
def get_recomendaciones_recipes(receipe_id):
    name = request.cookies.get('name')

    id_recipes = recomendar.recomendador_contexto(name, receipe_id)

    # pongo recipes vistos con rating = 0
    for id_recipe in id_recipes:
        recomendar.insertar_review(id_recipe, name, 0)

    recipes_recomendados = recomendar.datos_recipes(id_recipes)
    cant_valorados = len(recomendar.items_valorados(name))
    cant_vistos = len(recomendar.items_vistos(name))

    recipe = recomendar.obtener_receta(receipe_id)

    return render_template("detalles.html", recipe=recipe, recipes_recomendados=recipes_recomendados, name=name, cant_valorados=cant_valorados, cant_vistos=cant_vistos, LAST_UPDATE=LAST_UPDATE)


@app.post('/recomendaciones')
def post_recomendaciones():
    id_usuario = request.cookies.get('name')

    # inserto los ratings enviados como interacciones
    for id_recipe in request.form.keys():
        rating = int(request.form[id_recipe])
        if rating > 0: # 0 es que no puntuó
            recomendar.insertar_review(id_recipe, id_usuario, rating)

    return make_response(redirect("/recomendaciones"))

@app.get('/reset')
def get_reset():
    id_usuario = request.cookies.get('name')
    recomendar.reset_usuario(id_usuario)

    return make_response(redirect("/recomendaciones"))

@app.route('/api/buscar_recetas')
def api_buscar_recetas():
    q = request.args.get('q', '').strip().lower()
    if not q:
        return jsonify([])

    results = recomendar.buscar_recetas(q)
    # devolvemos solo lo necesario
    return jsonify([
        {"recipe_id": r["recipe_id"], "title": r["title"]}
        for r in results[:10]
    ])

@app.context_processor
def inject_globals():
    return {
        "ALGORITHMS": ALGORITHMS
    }

@app.get("/set_algoritmo")
def set_algoritmo():
    alg = request.args.get("alg", "azar")

    # seguridad: solo permitir algoritmos válidos
    if alg not in ALGORITHMS:
        alg = "azar"

    res = make_response(redirect(request.referrer or "/recomendaciones"))
    res.set_cookie("algoritmo", alg)
    return res


if __name__ == '__main__':
    app.run()
    



