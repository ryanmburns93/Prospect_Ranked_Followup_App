import os
from flask import Flask, request, redirect, url_for, render_template, send_from_directory
from werkzeug.utils import secure_filename
from sentiment import *
from api_calling import *
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, update, select, func
from sqlalchemy.types import BIGINT, INTEGER, VARCHAR, FLOAT, DATETIME
import pyodbc  # Needs to be imported to support string connector of sql alchemy engine
import urllib
import os
import pandas as pd


load_dotenv('.env')
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER')
ALLOWED_EXTENSIONS = os.getenv('ALLOWED_EXTENSIONS')

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

app = Flask(__name__, template_folder=tmpl_dir, static_folder=static_dir, static_url_path='')

# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.mkdir(UPLOAD_FOLDER)


@app.route("/", methods=['GET', 'POST'])
def index():
    return render_template('index.html')


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
    return redirect(url_for('post_transcripts_to_db'), file=messages_df)


@app.route("/refresh", methods=['POST'])
def refresh():
    """
    
    """
    
    return


@app.route("/check_refresh_needed")
def check_db_timeLastMessage():
    sql_connection_string = os.getenv('SQL_CONNECTION_STRING')
    sql_table_name = os.getenv('SQL_TABLE_NAME')
    quoted = urllib.parse.quote_plus(sql_connection_string)
    engine = create_engine('mssql+pyodbc:///?odbc_connect={}'.format(quoted))

    md = MetaData(bind=engine, schema='dbo')
    md.reflect(only=[sql_table_name])
    transcript_table = md.tables['dbo.' + sql_table_name]
    get_timeLastMessage_statement = (select(transcript_table.c.timeLastMessage).
                                        where(transcript_table.c.timeLastMessage == (
                                            select(func.max(transcript_table.c.timeLastMessage)))))
    result = engine.execute(get_timeLastMessage_statement)
    result_datetime_object = datetime.strptime(result, '%m/%d/%Y %H:%M')
    if (datetime.today()-timedelta(days=1)).day == result_datetime_object.day:
        return redirect(url_for('refresh'))
    else:
        return redirect(url_for('call_transcript_api'))

    
@app.route('/call_api')
def call_transcript_api():
    api_url_base = os.getenv('TRANSCRIPT_API_URL_BASE')
    yd = datetime.today()-timedelta(days=1) #yesterday
    date_spec = f'&startDate={yd.year}-{yd.month:02d}-{yd.day:02d}&endDate={yd.year}-{yd.month:02d}-{yd.day:02d}'
    full_api_url = api_url_base + date_spec
    response = requests.get(full_api_url, allow_redirects=True)
    csv_file_path = os.path.join(os.path.abspath(UPLOAD_FOLDER), f'{full_api_url[-39:]}.csv')
    with open(csv_file_path, 'wb+') as f:
        f.write(response.content)
    transcript_df = pd.read_csv(csv_file_path)
    return redirect(url_for('analyze_sentiment'), file=transcript_df)
    return redirect(url_for('post_transcripts_to_db'), file=transcript_df)


@app.route('/post_to_sql')
def post_transcripts_to_db(transcripts_df):
    """
    Post latest transcript messages to SQL Server DB.

    Parameters
    ----------
    transcripts_df : Pandas DataFrame
        The dataframe containing the daily transcript messages from the previous day
        needing injection into the SQL table.

    Returns
    -------
    None
    
    """
    sql_connection_string = os.getenv('SQL_CONNECTION_STRING')
    sql_table_name = os.getenv('SQL_TABLE_NAME')
    quoted = urllib.parse.quote_plus(sql_connection_string)
    engine = create_engine('mssql+pyodbc:///?odbc_connect={}'.format(quoted))

    md = MetaData(bind=engine, schema='dbo')
    md.reflect(only=[sql_table_name])

    transcripts_df.to_sql(name=sql_table_name,
                          schema="dbo",
                          con=engine,
                          if_exists='append',
                          index=False,
                          chunksize=100,
                          dtype={})
    return

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001)
