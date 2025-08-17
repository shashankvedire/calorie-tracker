from flask import Flask, request, render_template, session, redirect, url_for
import requests
from food_classifier import classify_food  # Import the classification function

app = Flask(__name__)
app.secret_key = 'supersecretkey'

API_KEY = '4e04e088e81a441f81e77fd09d2aa021'


# Function to search for food items as an ingredient
def search_food(food_name):
    api_url = "https://api.spoonacular.com/food/ingredients/search"
    params = {"query": food_name, "apiKey": API_KEY, "number": 10}
    response = requests.get(api_url, params=params)

    if response.status_code == 200:
        data = response.json()
        if data['results']:
            return data['results'][0]['id']  # Return the first ingredient's ID
        else:
            return None
    else:
        return None


# Function to get nutritional information for an ingredient
def get_nutrition_info(ingredient_id, amount=1, unit='cup'):
    api_url = f"https://api.spoonacular.com/food/ingredients/{ingredient_id}/information"
    params = {"apiKey": API_KEY, "amount": amount, "unit": unit}
    response = requests.get(api_url, params=params)

    if response.status_code == 200:
        data = response.json()
        nutrition_data = data['nutrition']['nutrients']

        basic_nutrients = {"Calories": 0, "Protein": 0, "Fat": 0, "Carbohydrates": 0}
        for nutrient in nutrition_data:
            if nutrient['name'] in ['Calories', 'Protein', 'Fat', 'Carbohydrates']:
                basic_nutrients[nutrient['name']] = nutrient['amount']

        return basic_nutrients
    else:
        return None


# Function to search for restaurant menu items
def search_menu_item(item_name):
    api_url = "https://api.spoonacular.com/food/menuItems/search"
    params = {"query": item_name, "apiKey": API_KEY, "number": 10}
    response = requests.get(api_url, params=params)

    if response.status_code == 200:
        data = response.json()
        if data['menuItems']:
            return data['menuItems'][0]  # Return the first menu item
        else:
            return None
    else:
        return None


# Route to display and handle the calorie tracker
@app.route("/", methods=["GET", "POST"])
def index():
    if 'calorie_goal' not in session:
        session['calorie_goal'] = 2000  # Default daily calorie goal

    if 'food_items' not in session:
        session['food_items'] = []

    if 'meal_nutrients' not in session:
        session['meal_nutrients'] = {"breakfast": [], "lunch": [], "dinner": [], "snacks": []}

    total_calories = sum(item['calories'] for item in session['food_items'])
    total_protein = sum(item['protein'] for item in session['food_items'])
    total_fat = sum(item['fat'] for item in session['food_items'])
    total_carbs = sum(item['carbohydrates'] for item in session['food_items'])

    if request.method == "POST":
        food_name = request.form["food_name"]
        amount = float(request.form["amount"])
        unit = request.form["unit"]
        meal_type = request.form["meal_type"]

        # Step 1: Try searching as an ingredient
        ingredient_id = search_food(food_name)

        if ingredient_id:
            # Found as an ingredient, fetch nutrition data
            nutrients = get_nutrition_info(ingredient_id, amount, unit)
            if nutrients:
                # Classify the food based on its nutritional content
                classification = classify_food(nutrients)

                food_item = {
                    "food_name": food_name,
                    "amount": amount,
                    "unit": unit,
                    "calories": nutrients["Calories"],
                    "protein": nutrients["Protein"],
                    "fat": nutrients["Fat"],
                    "carbohydrates": nutrients["Carbohydrates"],
                    "classification": classification  # Add classification result
                }
                session['food_items'].append(food_item)
                session['meal_nutrients'][meal_type].append(food_item)
                session.modified = True
                return redirect(url_for('index'))

        else:
            # Step 2: Try searching as a menu item
            menu_item = search_menu_item(food_name)
            if menu_item:
                # Classify the menu item based on its nutritional content
                classification = classify_food({
                    "Calories": menu_item['nutrition']['calories'],
                    "Protein": menu_item['nutrition'].get('protein', 0),
                    "Fat": menu_item['nutrition'].get('fat', 0),
                    "Carbohydrates": menu_item['nutrition'].get('carbs', 0)
                })

                food_item = {
                    "food_name": menu_item['title'],
                    "amount": 1,  # Menu items typically don't have varying amounts
                    "unit": "serving",
                    "calories": menu_item['nutrition']['calories'],
                    "protein": menu_item['nutrition'].get('protein', 0),
                    "fat": menu_item['nutrition'].get('fat', 0),
                    "carbohydrates": menu_item['nutrition'].get('carbs', 0),
                    "classification": classification  # Add classification result
                }
                session['food_items'].append(food_item)
                session['meal_nutrients'][meal_type].append(food_item)
                session.modified = True
                return redirect(url_for('index'))

    return render_template(
        "index.html",
        total_calories=total_calories,
        total_protein=total_protein,
        total_fat=total_fat,
        total_carbs=total_carbs,
        calorie_goal=session['calorie_goal'],
        food_items=session['food_items'],
        meal_nutrients=session['meal_nutrients'],
    )


# Route to remove a food item
@app.route("/remove/<int:index>")
def remove_item(index):
    if 'food_items' in session:
        session['food_items'].pop(index)
        session.modified = True
    return redirect(url_for('index'))


# Route to update the daily calorie goal
@app.route("/set_goal", methods=["POST"])
def set_goal():
    session['calorie_goal'] = int(request.form['calorie_goal'])
    session.modified = True
    return redirect(url_for('index'))


if __name__ == "__main__":
    app.run(debug=True)
