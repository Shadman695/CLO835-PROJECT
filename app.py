from flask import Flask, render_template, request
from pymysql import connections
import boto3
import os
import logging
import argparse
import random  # Import the random module

app = Flask(__name__)

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables for MySQL database
DBHOST = os.environ.get("DBHOST") or "localhost"
DBUSER = os.environ.get("MYSQL_USERNAME") or "root"
DBPWD = os.environ.get("MYSQL_PASSWORD") or "password"
DATABASE = os.environ.get("DATABASE") or "employees"
DBPORT = int(os.environ.get("DBPORT", 3306))

# Environment variables for the application
COLOR_FROM_ENV = os.environ.get('APP_COLOR') or "lime"
BACKGROUND_IMAGE_URL = os.environ.get('BACKGROUND_IMAGE_URL')
YOUR_NAME = os.environ.get('YOUR_NAME')
S3_BUCKET = os.environ.get('S3_BUCKET')
S3_KEY = os.environ.get('S3_KEY')

# Create a connection to the MySQL database
db_conn = connections.Connection(
    host=DBHOST,
    port=DBPORT,
    user=DBUSER,
    password=DBPWD,
    db=DATABASE
)
output = {}
table = 'employee'

# Define the supported color codes
color_codes = {
    "red": "#e74c3c",
    "green": "#16a085",
    "blue": "#89CFF0",
    "blue2": "#30336b",
    "pink": "#f4c2c2",
    "darkblue": "#130f40",
    "lime": "#C1FF9C",
}

# Create a string of supported colors
SUPPORTED_COLORS = ",".join(color_codes.keys())

# Generate a random color
COLOR = random.choice(list(color_codes.keys()))



# S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    aws_session_token=os.environ.get('AWS_SESSION_TOKEN')
)

def download_image_from_s3(bucket, key, local_filename):
    if not os.path.exists(os.path.dirname(local_filename)):
        os.makedirs(os.path.dirname(local_filename))
    s3_client.download_file(bucket, key, local_filename)

@app.route("/", methods=['GET', 'POST'])
def home():
    download_image_from_s3(S3_BUCKET, S3_KEY, 'static/background.png')
    logger.info(f"Background image URL: {BACKGROUND_IMAGE_URL}")
    return render_template('addemp.html', color=f"url('/static/background.png')")

@app.route("/about", methods=['GET','POST'])
def about():
    download_image_from_s3(S3_BUCKET, S3_KEY, 'static/background.png')
    return render_template('about.html', color=f"url('/static/background.png')", name=YOUR_NAME)

@app.route("/addemp", methods=['POST'])
def AddEmp():
    emp_id = request.form['emp_id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    primary_skill = request.form['primary_skill']
    location = request.form['location']

    insert_sql = "INSERT INTO employee VALUES (%s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    try:
        cursor.execute(insert_sql, (emp_id, first_name, last_name, primary_skill, location))
        db_conn.commit()
        emp_name = "" + first_name + " " + last_name
    finally:
        cursor.close()

    logger.info("Employee added to the database")
    return render_template('addempoutput.html', name=emp_name, color=f"url('/static/background.png')")

@app.route("/getemp", methods=['GET', 'POST'])
def GetEmp():
    download_image_from_s3(S3_BUCKET, S3_KEY, 'static/background.png')
    return render_template("getemp.html", color=f"url('/static/background.png')")

@app.route("/fetchdata", methods=['GET','POST'])
def FetchData():
    emp_id = request.form['emp_id']

    output = {}
    select_sql = "SELECT emp_id, first_name, last_name, primary_skill, location from employee where emp_id=%s"
    cursor = db_conn.cursor()

    try:
        cursor.execute(select_sql, (emp_id,))
        result = cursor.fetchone()
        
        # Add No Employee found form
        output["emp_id"] = result[0]
        output["first_name"] = result[1]
        output["last_name"] = result[2]
        output["primary_skills"] = result[3]
        output["location"] = result[4]
    except Exception as e:
        logger.error(e)
    finally:
        cursor.close()

    return render_template("getempoutput.html", id=output["emp_id"], fname=output["first_name"],
                           lname=output["last_name"], interest=output["primary_skills"], location=output["location"], color=f"url('/static/background.png')")

if __name__ == '__main__':
    # Check for Command Line Parameters for color
    parser = argparse.ArgumentParser()
    parser.add_argument('--color', required=False)
    args = parser.parse_args()

    if args.color:
        logger.info("Color from command line argument =" + args.color)
        COLOR = args.color
        if COLOR_FROM_ENV:
            logger.info("A color was set through environment variable -" + COLOR_FROM_ENV + ". However, color from command line argument takes precedence.")
    elif COLOR_FROM_ENV:
        logger.info("No Command line argument. Color from environment variable =" + COLOR_FROM_ENV)
        COLOR = COLOR_FROM_ENV
    else:
        logger.info("No command line argument or environment variable. Picking a Random Color =" + COLOR)

    # Check if input color is a supported one
    if COLOR not in color_codes:
        logger.error("Color not supported. Received '" + COLOR + "' expected one of " + SUPPORTED_COLORS)
        exit(1)

    app.run(host='0.0.0.0', port=81, debug=True)

