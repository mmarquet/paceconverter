from flask import Flask
from flask import render_template
from flask import request
from flask import send_from_directory
from decimal import Decimal

import datetime
import html
import os

app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def hello():
    if request.method == 'POST':
        print(request.form)
        if 'converttokmperh' in request.form:
            minutes = html.escape(request.form['minutes'])
            seconds = html.escape(request.form['seconds'])
            pace = "{:.2f}".format(minkmtokmperhour(int(minutes), int(seconds)))
        elif 'converttominperkm' in request.form:
            try:
                pace = html.escape(request.form['kmperhour'])
                minutes, seconds = kmperhourtominkm(float(pace))
            except:
                pace = 0
                minutes, seconds = 0, 0
        fivek, tenk, twentyk, half, marathon, o = racecalculator(int(minutes), int(seconds))
        return render_template('mainpage.html', minutes=minutes, seconds=seconds, pace=pace, fivek=fivek, tenk=tenk, twentyk=twentyk, half=half, marathon=marathon, o=o)
    else:
        return render_template('mainpage.html', minutes=0, seconds=0, pace=0, fivek=0, tenk=0, twentyk=0, half=0, marathon=0, o=0)

@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('js', path)

@app.route('/css/<path:path>')
def send_css(path):
    return send_from_directory('css', path)

def minkmtokmperhour(minutes, seconds):
    if minutes == 0 and seconds == 0:
        pace = 0
    else:
        pace = 60 / (minutes + seconds / 60)
    return pace

def kmperhourtominkm(pace):
    if pace <= 0:
        minutes, seconds = 0, 0
    else:
        minutes = int(60 // pace)
        seconds = int(float(Decimal(str(60 / pace)) % 1) * 60)
    return minutes, seconds

def racecalculator(minutes, seconds, other=0):
    x = lambda a : str(datetime.timedelta(seconds=(minutes * 60 * a) + (a * seconds))).split(':')
    y = lambda a : '{}h{}min{}s'.format(a[0], a[1], (a[2].split('.'))[0])
    fivek = y(x(5))
    tenk = y(x(10))
    twentyk = y(x(20))
    half = y(x(21.0975))
    marathon = y(x(42.195))
    o = y(x(other))
    return fivek, tenk, twentyk, half, marathon, o

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False,host='0.0.0.0',port=port)
