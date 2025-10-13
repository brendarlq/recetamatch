from flask import Flask, request, render_template, make_response, redirect, jsonify
import recomendar

app = Flask(__name__)
app.debug = True

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
    return render_template('login.html')

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

    return render_template("recomendaciones.html", recipes_recomendados=recipes_recomendados, name=name, cant_valorados=cant_valorados, cant_vistos=cant_vistos)

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

    id_recipes = recomendar.recomendar_contexto(name, receipe_id)

    # pongo recipes vistos con rating = 0
    for id_recipe in id_recipes:
        recomendar.insertar_review(id_recipe, name, 0)

    recipes_recomendados = recomendar.datos_recipes(id_recipes)
    cant_valorados = len(recomendar.items_valorados(name))
    cant_vistos = len(recomendar.items_vistos(name))

    recipe = recomendar.obtener_receta(receipe_id)

    return render_template("detalles.html", recipe=recipe, recipes_recomendados=recipes_recomendados, name=name, cant_valorados=cant_valorados, cant_vistos=cant_vistos)


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



if __name__ == '__main__':
    app.run()
    



