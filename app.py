import os
from flask import Flask, request, redirect, url_for, render_template, send_from_directory
from werkzeug.utils import secure_filename
from sentiment import *
from api_calling import *
from datetime import datetime, timedelta

UPLOAD_FOLDER = './tmp/'
ALLOWED_EXTENSIONS = set(['csv', 'xlsx'])

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


@app.route("/get_sentiment")
def analyze_sentiment(messages_df):
    data = json.loads(request.data.decode())
    messages_df = data["messages_df"]
    messages_df = sentiment_main(messages_df)
    return


@app.route("/", methods=['GET', 'POST'])
def index():
    return render_template('index.html')


@app.route("/refresh", methods=['POST'])
def refresh():
    """
    
    """
    daily_transcripts_df = api_calling_main(logger_name='api_calling_logger',
                                            save_dir='./tmp/',
                                            logger_verbosity=10,
                                            transcript_html_save_loc=None,
                                            save_freq=500,
                                            warm_start_daily_transcripts_file=None,
                                            date_target_package=((datetime.today()-timedelta(days=1)).day,
                                                                 (datetime.today()-timedelta(days=1)).month,
                                                                 (datetime.today()-timedelta(days=1)).year))
    daily_transcripts_df = analyze_sentiment(daily_transcripts_df)
    
    return redirect(url_for('analyze_sentiment'), file=daily_transcripts_df)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001)
