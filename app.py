# python app.py --model model/yolov3.weights --config model/yolov3_custom.cfg --names model/obj.names
from flask import Flask, render_template, request, url_for, redirect, make_response, session
import cv2
import numpy as np
from detect import detect, resize
# import argparse
import os, io
from PIL import Image
import sqlite3
import base64


# parser = argparse.ArgumentParser()
# parser.add_argument("-m", "--model", required=True, help="Path To Model")
# parser.add_argument("-cf", "--config", required=True, help="Path To Config File")
# parser.add_argument("-n", "--names", required=True, help="Path To Names of Object")
# parser.add_argument("-c", "--confidence", default=0.5, help="Minimum confidence", type=float)
# parser.add_argument("-t", "--thresh", default=0.3, help="Threshold", type=float)
# args = vars(parser.parse_args())


args = {
	"model": "model/yolov3.weights",
	"config": "model/yolov3_custom.cfg",
	"names": "model/obj.names",
	"confidence": 0.5,
	"thresh": 0.3
}


sql = '''CREATE TABLE IF NOT EXISTS pothole_table(
	NAME TEXT NOT NULL,
    LOCATION TEXT NOT NULL,
    DESCRIPTION TEXT NOT NULL,
    PHOTO BLOB NOT NULL
)'''

sql2 = 'DROP TABLE IF EXISTS admin'

sql3 = '''CREATE TABLE IF NOT EXISTS admin(
	"username"	TEXT NOT NULL UNIQUE,
	"email"	TEXT NOT NULL UNIQUE,
	"password"	TEXT NOT NULL
)'''


sql4 = '''INSERT INTO admin VALUES ('admin', 'admin@admin.com', 'admin')'''

conn = sqlite3.connect("records/pothole.db")
cursor = conn.cursor()
cursor.execute(sql)
cursor.execute(sql2)
cursor.execute(sql3)
cursor.execute(sql4)

conn.commit()

cursor.close()
conn.close()


labelPaths = args["names"]

def convertToBinaryData(filename):
    #Convert digital data to binary format
    with open(filename, 'rb') as file:
        blobData = file.read()
    return blobData

Labels = open(labelPaths).read().strip().split("\n")
np.random.seed(15)
colors = np.random.randint(0, 255, size=(len(Labels), 3),
	dtype="uint8")

weightsPath = args["model"]
configPath = args["config"]

net = cv2.dnn.readNetFromDarknet(configPath, weightsPath)

print( net.getUnconnectedOutLayers())
ln = net.getLayerNames()
ln = [ln[i - 1] for i in net.getUnconnectedOutLayers()]

app = Flask(__name__)

app.config["CACHE_TYPE"] = "null"
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 1

app.config['imgdir'] = os.path.sep.join(['static', 'upload', 'images'])
app.config['SECRET_KEY'] = "AllSilverTeaCup" 

# 127:0.0.1:5000/
@app.route('/')
def index():
	session['verified'] = False
	return render_template('index.html')



@app.route('/main', methods=['POST', "GET"])
def main():
	if request.method == 'POST':
		try:
			# file = request.files.get("img","")
			# file.save(os.path.join(app.config["imgdir"], file.filename))

			# image = cv2.imread(os.path.join(app.config["imgdir"],file.filename))

			image = request.files["img"]
			image = Image.open(image)
			image = np.array(image)
			image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)


			image = resize(image, width=600)
			drawed, rects = detect(image.copy(), net, ln, Labels, colors, return_cords=True)
			if len(rects) == 0:
				return render_template('index.html', msg="Image Doesn't contain pothole")

			drawed = cv2.cvtColor(drawed, cv2.COLOR_BGR2RGB)
			drawed = Image.fromarray(drawed)
			data = io.BytesIO()
			drawed.save(data, "JPEG")
			drawed = base64.b64encode(data.getvalue()).decode('utf-8')

			return render_template("index.html", file=drawed)
		except Exception as e:
			print(e)
			result = ('Please pass proper input :'+ str(e) , 2)
			return render_template('index.html', msg=result)
	return render_template("index.html")




@app.route("/store", methods=['POST', 'GET'])
def store():

	name = request.form['uname']
	desc = request.form['desc']
	location = request.form['location']
	# blobData = convertToBinaryData("static/img.png")
	# print(type(blobData))
	blobData = request.form['hiddenImage']
	# print(type(blobData))


	conn = sqlite3.connect("records/pothole.db")
	cursor = conn.cursor()

	sqlite_insert_blob_query = "INSERT INTO pothole_table (NAME, LOCATION, DESCRIPTION, PHOTO) VALUES (?, ?, ?, ?)"
	data_tuple = (name, location, desc, blobData)
	cursor.execute(sqlite_insert_blob_query, data_tuple)

	conn.commit()
	cursor.close()
	conn.close()

	# file_path = os.path.join("static", "img.png")
	return render_template("index.html", file=blobData, msg='Stored Successfully')


@app.route('/show', methods=['POST', "GET"])
def show():
	if not session['verified']:
		return render_template("adminlogin.html")
	try:
		conn = sqlite3.connect("records/pothole.db")
		cursor = conn.cursor()
		cursor.execute("SELECT * FROM pothole_table")
		my_list = cursor.fetchall()

		data1 = []
		for i in range(len(my_list)):
			a = []
			for j in range(len(my_list[0])):
				a.append(my_list[i][j])
			data1.append(a)

	except Exception as e:
		print("Error", e)
	return render_template('show.html', data1=data1, len=len(data1))



@app.route('/login', methods=['POST', "GET"])
def login():
	name = request.form['uname']
	password = request.form['password']
	try:
		conn = sqlite3.connect("records/pothole.db")
		cursor = conn.cursor()
		cursor.execute("SELECT * FROM admin WHERE (username=? OR email=?) AND (password=?)", (name, name, password))
		result = cursor.fetchone()
		if result is None:
			return render_template("adminlogin.html")
		session['verified'] = True
		return redirect("/show")
	except Exception as e:
		print(e)

if __name__ == "__main__":
	app.run(debug=True)