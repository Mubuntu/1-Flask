# -*- coding: utf-8 -*-

import os
from sqlite3 import dbapi2 as sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
    render_template, flash

# create our little application :)
app = Flask(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'recipes.db'),
    DEBUG=True,
    SECRET_KEY='development key'
))
app.config.from_envvar('RECIPES_SETTINGS', silent=True)


def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


def init_db():
    """Initializes the database."""
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


@app.cli.command('initdb')
def initdb_command():
    """Creates the database tables."""
    init_db()
    print('Initialized the database.')


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


@app.route('/')
def show_recipes():
    db = get_db()
    cur = db.execute('select id, name from recipes')
    recipes = cur.fetchall()
    return render_template('show_recipes.html', recipes=recipes)

@app.route('/<recipe_id>')
def show_recipe(recipe_id):
    db = get_db()
    cur = db.execute('SELECT id, name FROM recipes WHERE id=' + recipe_id)
    recipes = cur.fetchall()
    cur = db.execute('SELECT ingredients.name FROM recipes_ingredients \
                                INNER JOIN recipes ON recipes_ingredients.recipe_id=recipes.id \
                                INNER JOIN ingredients ON recipes_ingredients.ingredient_id=ingredients.id \
                                WHERE recipes_ingredients.recipe_id=' + recipe_id)
    ingredients = cur.fetchall()
    return render_template('show_recipe.html', recipes=recipes, ingredients=ingredients)

@app.route('/search', methods=['POST'])
def search_recipe():
    name = request.form['name']
    recipes = []
    db = get_db()
    cur = db.execute('SELECT id FROM ingredients WHERE id=' + name + "'")
    ingredient = cur.fetchall()
    if len(ingredient)>0:
        cur = db.execute('SELECT recipe_id FROM recipes_ignredients WHERE ingredient_id=' +str(ingredient[0][0]))
        for recipe in cur.fetchall():
            cur.fetchall()
    return render_template('search_recipes.html', recipes=recipes)

@app.route('/add', methods=['POST'])
def add_entry():
    db = get_db()
    try:
        cur = db.execute('SELECT MAX(id) as max FROM recipes')
        max_id_recipes = cur.fetchall()[0][0] + 1
        cur = db.execute('SELECT MAX(id) as max FROM ingredients')
        max_id_ingredients = cur.fetchall()[0][0] + 1
    except:
        # nog geen recepten en ingrediënten
        max_id_recipes = 1
        max_id_ingredients = 1

    db.execute('INSERT INTO recipes (name) VALUES (?)',
                                [request.form['name']])
    ingredients = request.form['ingredients']
    for ingredient in ingredients.splitlines():
        cur = db.execute("SELECT id FROM ingredients WHERE name='" + ingredient + "'")
        existing_ingredient = cur.fetchall()
        if len(existing_ingredient) > 0:
            db.execute('INSERT INTO recipes_ingredients (ingredient_id, recipe_id) VALUES (?, ?)',
                                                        [existing_ingredient[0][0], max_id_recipes])
        else:
            db.execute('INSERT INTO ingredients (name) VALUES (?)',
                                                        [ingredient])
            db.execute('INSERT INTO recipes_ingredients (ingredient_id, recipe_id) VALUES (?, ?)',
                                                        [max_id_ingredients, max_id_recipes])
            max_id_ingredients += 1
    db.commit()
    flash('New recipe was successfully added')
    return redirect(url_for('show_recipes'))

