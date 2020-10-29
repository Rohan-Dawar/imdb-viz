# Dependencies
import os, secrets, requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from flask import Flask, flash, render_template, request, redirect, url_for, abort, \
    send_from_directory
from werkzeug.utils import secure_filename

# Flask Init
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
app.config['UPLOAD_EXTENSIONS'] = ['.csv']
app.config['UPLOAD_PATH'] = 'uploads'
app.secret_key = secrets.token_urlsafe(32)

# File (csv) Too Large Error Handling
@app.errorhandler(413)
def too_large(e):
    return "File is too large", 413

# Index Route - Return HTML page with uploaded csv file
@app.route('/')
def index():
    files = os.listdir(app.config['UPLOAD_PATH'])
    return render_template('index.html', files=files)

# Upload File Route
@app.route('/', methods=['POST'])
def upload_files():
    uploaded_file = request.files['file']
    filename = secure_filename(uploaded_file.filename)
    if filename != '':
        file_ext = os.path.splitext(filename)[1]
        uploaded_file.save(os.path.join(app.config['UPLOAD_PATH'], filename))
    return '', 204

# File Path
@app.route('/uploads/<filename>')
def upload(filename):
    return send_from_directory(app.config['UPLOAD_PATH'], filename)

# Pandas Dataframe from CSV
def create_df(csv):
	ratings = pd.read_csv(os.path.join(app.config['UPLOAD_PATH'], csv), encoding='unicode_escape')
	ratings = ratings.rename(columns={
	    "Your Rating" : "YourRating",
	    "Date Rated" : "DateRated",
	    "Title Type" : "Type",
	    "IMDb Rating" : "IMDbRating",
	    "Runtime (mins)" : "RuntimeMins",
	    "Num Votes" : "NumVotes",
	    "Release Date" : "Release"})
	ratings['RatingDelta'] = ratings.YourRating - ratings.IMDbRating
	return ratings

def get_poster(url):
	"""Given the IMDB URL, return the image png of the movie poster"""
	htmlPage = requests.get(url).text
	soup = BeautifulSoup(htmlPage, 'html.parser')
	for link in soup.findAll('img'):
		return link['src']

def return_vizObj(df):
	#[0] Runtime Histogram:
	RuntimeHistogram = tuple(map(lambda x: x.tolist(), np.histogram(df['RuntimeMins'].to_list(),bins=15)))

	#[1] YourRating Histogram:
	YourRatingHistogram = tuple(map(lambda x: x.tolist(), np.histogram(df['YourRating'].to_list())))

	#[2]: Release Year Histogram:
	ReleaseHistogram = tuple(map(lambda x: x.tolist(), np.histogram(df['Year'].to_list(),bins=100)))

	#[3]: Average Rating by Year BarChart
	AvgRatingbyYear = df.groupby('Year')[['YourRating']].mean().reset_index()
	AvgRatingYearList = []
	for year in range(AvgRatingbyYear['Year'].min(), AvgRatingbyYear['Year'].max()+1):
		if year in AvgRatingbyYear['Year'].tolist():
			AvgRatingYearList.append(AvgRatingbyYear[(AvgRatingbyYear.Year == year)].YourRating.values[0])
		else:
			AvgRatingYearList.append(0)

	#[4]: Means:
	meanstats = (df["YourRating"].mean(), df["IMDbRating"].mean())

	#[5/6]: Relative UP Rating:
	relativeUP, relativeDOWN = [], []
	topNum = 5
	#Top Num Over
	topOver = df.sort_values('RatingDelta', ascending=False).head(topNum)
	topUnder = df.sort_values('RatingDelta', ascending=False).tail(topNum)

	for film in range(topNum):
		bundleUP = (topOver.Title.values[film], get_poster(topOver.URL.values[film]),
			topOver.YourRating.values[film], topOver.IMDbRating.values[film])
		relativeUP.append(bundleUP)
		bundleDOWN = (topUnder.Title.values[film], get_poster(topUnder.URL.values[film]),
			topUnder.YourRating.values[film], topUnder.IMDbRating.values[film])
		relativeDOWN.append(bundleDOWN)

	return (RuntimeHistogram, YourRatingHistogram, ReleaseHistogram, AvgRatingYearList, meanstats, relativeUP, relativeDOWN)

@app.route('/submit', methods=['POST'])
def submit():
	df = create_df('ratings.csv')
	vizObj = return_vizObj(df)

	flash(f'You Have Rated {len(df.index)} Films on IMDB!')
	
	return render_template('index.html',  tables=vizObj,
		fulltable=[df.sort_values('RatingDelta', ascending=False).to_html(classes='data', header="true")])

# Flask RUN:
if __name__ == "__main__":
	app.run()