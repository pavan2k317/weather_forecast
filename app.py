from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from pymongo import MongoClient
from bson.objectid import ObjectId
import requests, os

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# MongoDB
client = MongoClient(os.getenv("MONGO_URI"))
db = client["weather_app"]
users = db.users

# Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Weather API
API_KEY = os.getenv("WEATHER_API_KEY")
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']

@login_manager.user_loader
def load_user(user_id):
    user_data = users.find_one({"_id": ObjectId(user_id)})
    return User(user_data) if user_data else None

@app.route('/')
@login_required
def home():
    return render_template("index.html", user=current_user)

@app.route('/', methods=['POST'])
@login_required
def weather():
    city = request.form.get('city')
    geo_url = "http://api.openweathermap.org/geo/1.0/direct"
    geo_params = {'q': city, 'limit': 1, 'appid': API_KEY}
    geo_res = requests.get(geo_url, params=geo_params)
    geo_data = geo_res.json()

    if geo_res.status_code == 200 and geo_data:
        lat = geo_data[0]['lat']
        lon = geo_data[0]['lon']
        country = geo_data[0]['country']
        search_city = geo_data[0]['name']

        weather_url = "http://api.openweathermap.org/data/2.5/weather"
        weather_params = {'lat': lat, 'lon': lon, 'appid': API_KEY, 'units': 'metric'}
        weather_res = requests.get(weather_url, params=weather_params)
        weather_data = weather_res.json()

        if weather_res.status_code == 200:
            weather = {
                'search_city': search_city,
                'city': weather_data['name'],
                'temperature': weather_data['main']['temp'],
                'feels_like': weather_data['main']['feels_like'],
                'humidity': weather_data['main']['humidity'],
                'wind': weather_data['wind']['speed'],
                'description': weather_data['weather'][0]['description'],
                'icon': weather_data['weather'][0]['icon'],
                'pressure': weather_data['main']['pressure'],
                'clouds': weather_data['clouds']['all'],
                'country': country
            }
            return render_template('index.html', weather=weather, user=current_user)

    flash("Location not found. Please try a nearby area or check spelling.", "danger")
    return render_template('index.html', weather={'error': f"'{city}' not found."}, user=current_user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if users.find_one({'username': username}):
            flash('User already exists!', 'danger')
            return redirect(url_for('register'))
        users.insert_one({
            'username': username,
            'password': generate_password_hash(password)
        })
        flash('Registered successfully! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_data = users.find_one({'username': username})
        if user_data and check_password_hash(user_data['password'], password):
            login_user(User(user_data))
            flash("Logged in successfully!", "success")
            return redirect(url_for('home'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))

@app.route('/about')
def about():
    return render_template("about.html", user=current_user if current_user.is_authenticated else None)

@app.route('/contact')
def contact():
    return render_template("contact.html", user=current_user if current_user.is_authenticated else None)

if __name__ == "__main__":
    app.run(debug=True)
