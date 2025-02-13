from flask import Flask, make_response, render_template, redirect, request, flash
import requests
import redis
from dotenv import load_dotenv
import os
from os.path import join, dirname
import json
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Regexp
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)

# limiter = Limiter(get_remote_address, 
#                   app=app, 
#                   default_limits=["30 per hour"], 
#                   storage_uri="redis://localhost:6379")

#create form to validate input from FlaskForm
class LocationForm(FlaskForm):
     location = StringField('Location', validators=[DataRequired(), Regexp('[a-zA-Z]+', message='Please input without number or symbols')])
     submit = SubmitField('Submit')

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)   

redis_client = redis.Redis(host=os.getenv('LOCAL_HOST'), port=os.getenv('PORT'), db=0)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

def render_weather_template(data):
     return render_template('home.html', weather_data=data, form=LocationForm())

@app.route("/", methods=['GET', 'POST'])
def home():
     api_key = os.getenv("API_KEY")
     # Handling Redis and Json
     form = LocationForm() 
     """
     Object of Location Form must be the same object. Otherwise, 
     the input wont be received or validated
     """
     # print(request.form['location'])
     # print(request.args.get('location'))
     if form.validate_on_submit() and request.method == 'POST':
          try: 
               redis_key = request.form['location']
               weather_data = redis_client.get(redis_key) 
               if weather_data:
                    return render_weather_template(json.loads(weather_data))
          except json.decoder.JSONDecodeError:
               return make_response({"error": "Invalid JSON"})
          except Exception as e:
               flash(f"{status_code} {e}")
               return make_response({"error" : f'Unknown Error - {str(e)}'})
          # Handling API Call
          try:
               # with limiter.limit('2/hour'):
                    #source of wanted data
               api_link = f'https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{redis_key}?unitGroup=metric&key={api_key}'
               #request to get data from that source
               response = requests.get(api_link)
               #receive HTTPError status if occured
               response.raise_for_status()
               #return the fetched data
               redis_client.setex(redis_key, 300, json.dumps(response.json()))
               return render_weather_template(response.json())
          #If HTTPError is occured
          except requests.exceptions.HTTPError as e:
               #return the error's details
               status_code = response.status_code
               error_details = '' 
               if status_code == 401:
                    error_details = 'API key is invalid!'
                    return render_template('home.html', form=form, error=error_details)               
               
               elif status_code == 400 : 
                    error_details = 'Invalid Location!'
               else:
                    error_info = ' '.join(str(e).split(" ")[:3])
                    error_details = f'Unknown error - {error_info}'
               
               # return make_response({"error": error_details}, status_code)
               return render_template("400.html", error=error_details)
     return render_template('home.html', form=form)
if __name__ == '__main__':
    app.run()