import os
from utils import json_response
from flask import Flask, request, redirect, url_for, render_template, send_from_directory
from werkzeug.utils import secure_filename
from . import sentiment
from . import api_calling
from datetime import datetime, timedelta

UPLOAD_FOLDER = './tmp/'
ALLOWED_EXTENSIONS = set(['pdf'])

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

app = Flask(__name__, template_folder=tmpl_dir, static_folder=static_dir, static_url_path='')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists('./tmp/'):
    os.mkdir('./tmp/')


def allowed_file(filename):
    """
    allowed_file just checks the acceptable extensions
      it could be extended to check the fileheader/mimetype
    """
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/get_sentiment", methods=['GET'])
def apply_sentiment_analysis(messages_df):
    if request.method == 'GET':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
    messages_df = sentiment.main(messages_df)
    return


@app.route("/", methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('index'))
    files = dict(
        zip(os.listdir(app.config['UPLOAD_FOLDER']),
            ["/v/{}".format(k) for k in os.listdir(app.config['UPLOAD_FOLDER'])]))
    return render_template('/upload_index.html', file_list=files)


@app.route("/refresh", methods=['GET'])
def refresh():
    """
    
    """
    daily_transcripts_df = api_calling.main(logger_name='api_calling_logger',
                                            save_dir='./tmp/',
                                            logger_verbosity=10,
                                            transcript_html_save_dir=None,
                                            save_freq=500,
                                            warm_start_daily_transcripts_file=None,
                                            date_target_package=((datetime.today()-timedelta(days=1)).day,
                                                                 (datetime.today()-timedelta(days=1)).month,
                                                                 (datetime.today()-timedelta(days=1)).year))
    daily_transcripts_df = apply_sentiment_analysis(daily_transcripts_df)
    
    return redirect(url_for('apply_sentiment_analysis'), file=daily_transcripts_df)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001)
