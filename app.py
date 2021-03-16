# python app.py --model model/yolov3.weights --config model/yolov3_custom.cfg --names model/obj.names
from flask import Flask, render_template, request, url_for, redirect, make_response
import cv2
import numpy as np
from detect import detect, resize
import argparse
import os
from PIL import Image
import sqlite3
from base64 import b64encode

parser = argparse.ArgumentParser()
parser.add_argument("-m", "--model", required=True, help="Path To Model")
parser.add_argument("-cf", "--config", required=True, help="Path To Config File")
parser.add_argument("-n", "--names", required=True, help="Path To Names of Object")
parser.add_argument("-c", "--confidence", default=0.5, help="Minimum confidence", type=float)
parser.add_argument("-t", "--thresh", default=0.3, help="Threshold", type=float)
args = vars(parser.parse_args())


sql = '''CREATE TABLE IF NOT EXISTS pothole_table(
	NAME TEXT NOT NULL,
    LOCATION TEXT NOT NULL,
    DESCRIPTION TEXT NOT NULL,
    PHOTO BLOB NOT NULL
)'''


conn = sqlite3.connect("records/pothole.db")
cursor = conn.cursor()
cursor.execute(sql)
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

ln = net.getLayerNames()
ln = [ln[i[0] - 1] for i in net.getUnconnectedOutLayers()]

app = Flask(__name__)
app.config["CACHE_TYPE"] = "null"
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 1

app.config['imgdir'] = os.path.sep.join(['static', 'upload', 'images'])


@app.route('/')
def index():
	return render_template('index.html')



@app.route('/main', methods=['POST', "GET"])
def main():
	if request.method == 'POST':
		try:
			file = request.files.get("img","")
			file.save(os.path.join(app.config["imgdir"], file.filename))

			image = cv2.imread(os.path.join(app.config["imgdir"],file.filename))

			image = resize(image, width=600)
			drawed = detect(image.copy(), net, ln, Labels, colors)
			file_path = os.path.join("static", "img.png")
			if os.path.isfile(file_path):
				os.remove(file_path)
			cv2.imwrite(file_path, drawed.copy())
			return render_template("index.html", file=file_path)
		except Exception as e:
			print(e)
			result = ('Please pass proper input :'+ str(e) , 2 )
			return render_template('index.html', msg= result)
	return render_template("index.html")




@app.route("/store", methods=['POST', 'GET'])
def store():
	name = request.form['uname']
	desc = request.form['desc']
	location = request.form['location']
	blobData = convertToBinaryData("static/img.png")

	conn = sqlite3.connect("records/pothole.db")
	cursor = conn.cursor()

	sqlite_insert_blob_query = "INSERT INTO pothole_table (NAME, LOCATION, DESCRIPTION, PHOTO) VALUES (?, ?, ?, ?)"
	data_tuple = (name, location, desc, blobData)
	cursor.execute(sqlite_insert_blob_query, data_tuple)

	conn.commit()
	cursor.close()
	conn.close()

	file_path = os.path.join("static", "img.png")
	return render_template("index.html", file=file_path, msg='Stored Successfully')


@app.route('/show', methods=['POST', "GET"])
def show():
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

		for i in range(len(data1)):
			data1[i][-1] = b64encode(data1[i][-1]).decode("utf-8")
		

	except Exception as e:
		print(e)
	return render_template('show.html', data1=data1, len=len(data1))

	
if __name__ == "__main__":
	app.run(debug=True)