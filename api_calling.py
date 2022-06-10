import requests
from requests import Session
import json
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import os
from concurrent.futures import as_completed, ProcessPoolExecutor
from requests_futures.sessions import FuturesSession
import calendar
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv


load_dotenv('.env')
pd.options.mode.chained_assignment = None # default='warn'

def setup_logging(save_dir, logger_name, verbosity=10):
    """
    Establish logging configurations such as verbosity and output file location for the 
    remainder of the program.

    Parameters
    ----------
    save_dir : str, optional
        String path to directory in which logging should be recorded. 
        The default is 'C:/Users/rburns/Documents/5-10-22 Migration (Personal)/'.
    verbosity : int, optional
        Integer representation of the threshold at which a record will be logged. Options
        range from 0 (NOTSET threshold) to 50 (CRITICAL threshold). The default is 10 (DEBUG).

    Returns
    -------
    None.

    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(verbosity)
    logger.handlers = []
    logger.propogate = False
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(message)s')
    # logger.setFormatter(formatter)
    handler = RotatingFileHandler(filename=os.path.join(save_dir, 'logging_output.log'),
                                  mode='w',
                                  maxBytes=2000000,
                                  backupCount=10)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.info('-----------------------------')
    logger.info('--BEGINNING NEW PROGRAM RUN--')
    logger.info('Start Time: %s' % datetime.datetime.now())
    logger.info('-----------------------------')
    logger.info(f'Logging Level set to: {logger.getEffectiveLevel()}')
    return


def build_url(logger_name, today=True, year=None, month=None):
    logger = logging.getLogger(f'{logger_name}.build_url')
    full_api_url = ''
    api_url_base = os.getenv('TRANSCRIPT_API_URL_BASE')
    if today:
        bothDates_val = datetime.today().strftime('%Y-%m-%d')
        date_spec = f'&startDate={bothDates_val}&endDate={bothDates_val}'
        full_api_url = api_url_base + date_spec
    else:
        if month != None:
            if year == None:
                year = str(datetime.today().year)
            date_spec = f'&startDate={year}-{month}-01&endDate={year}-{month}-{calendar.monthrange(int(year), int(month))[1]}'
        elif year != None:
            date_spec = f'&startDate={year}-01-01&endDate={year}-12-31'
        full_api_url = api_url_base + date_spec
    if full_api_url == '':
        full_api_url = api_url_base
    return full_api_url


def call_api_for_daily_csv(full_api_url, logger_name):
    logger = logging.getLogger(f'{logger_name}.call_api_for_daily_csv')
    logger.info(f'Calling daily prospect csv file via url: {full_api_url}')
    response = requests.get(full_api_url, allow_redirects=True)
    if not os.path.exists(os.path.join(os.getcwd(), '/csv_temp/')):
        os.mkdir(os.path.join(os.getcwd(), '/csv_temp/'))
        logger.info('./csv_temp subdirectory created.')
    csv_file_path = os.path.join(os.getcwd(), f'/csv_temp/{full_api_url[-39:]}.csv')
    with open(csv_file_path, 'wb+') as f:
        f.write(response.content)
    logger.info('Daily prospect response from chatbot saved in ./csv_temp subdirectory.')
    df = pd.read_csv(csv_file_path)
    return df


def cross_reference_past_transcript_copies_for_no_change(transcript_source_length_lookup_dict, transcript_response_text, transcript_url, logger_name):
    """_summary_

    Args:
        transcript_source_length_lookup_dict (dict): 
        transcript_response_text (str): _description_
        transcript_url (str): _description_

    Returns:
        no_change_val (str): _description_
        transcript_source_length_lookup_dict (dict): 
    """    
    logger = logging.getLogger(f'{logger_name}.cross_reference_past_transcript_copies_for_no_change')
    prior_response_length = transcript_source_length_lookup_dict.get(transcript_url)
    if prior_response_length == len(transcript_response_text):
        no_change_val = True
        logger.info(f'No change in transcript response length for {transcript_url}.')
    else:
        no_change_val = False
        logger.info(f'A change to the transcript response length for {transcript_url} was detected.')
        transcript_source_length_lookup_dict.update({transcript_url: len(transcript_response_text)})
        logger.info('Updated transcript_source_length_lookup_dict with new transcript response length.')
    return no_change_val, transcript_source_length_lookup_dict


def read_transcripts(df, logger_name):
    """
    
    """
    logger = logging.getLogger(f'{logger_name}.read_transcripts')
    day_transcripts_df = pd.DataFrame()
    try:
        with open(os.path.join(os.getcwd(), '/csv_temp/transcript_source_lookup_length_dict.json'), 'r+') as json_file:
            transcript_source_length_lookup_dict = json.load(json_file)
        logger.info('Transcript_source_length_lookup_dict dictionary loaded from memory.')
    except FileNotFoundError:
        transcript_source_length_lookup_dict = dict()
        logger.info('FileNotFoundError occurred. No existing transcript_source_length_lookup_dict found. An empty dict has been created.')
    s = FuturesSession(executor=ProcessPoolExecutor(max_workers=16), session=Session())
    futures = []
    for index, transcript_row in df.iterrows():
        transcript_url = transcript_row['transcript']
        future = s.get(transcript_url)
        futures.append(future)
        for future in as_completed(futures):
            response2 = future.result()
            no_change_flag, transcript_source_length_lookup_dict = cross_reference_past_transcript_copies_for_no_change(transcript_source_length_lookup_dict, response2.text, transcript_url)
            if no_change_flag:
                continue
            transcript_soup = BeautifulSoup(response2.text, features='html.parser')
            soup_script_string = transcript_soup.find('script').text
            messages_list = json.loads(soup_script_string[soup_script_string.index('"messages"')+11:-len('},"messageId":null} })')+1])
            transcript_df = pd.DataFrame()
            for message in messages_list:
                temp_df = pd.DataFrame(message, index=[0])
                transcript_df = pd.concat([transcript_df, temp_df],
                                          axis=0,
                                          ignore_index=True)
            transcript_row_dict = transcript_row.to_dict()
            for key, value in transcript_row_dict.items():
                transcript_df[key] = value
            day_transcripts_df = pd.concat([day_transcripts_df, transcript_df],
                                            axis=0,
                                            ignore_index=True)
    day_transcripts_df['timeCreated'] = pd.to_datetime(day_transcripts_df['timeCreated'])
    day_transcripts_df['timeCreated'] = [timestamp.to_pydatetime() for timestamp in day_transcripts_df['timeCreated']]
    # os.chdir('/csv_temp/')
    day_transcripts_df.to_csv(os.path.abspath('all_transcripts_df.csv'), index=False)
    return day_transcripts_df


def is_target_prospect(single_transcript_df, logger_name):
    logger = logging.getLogger(f'{logger_name}.is_target_prospect')
    target_prospect = False
    last_interaction = single_transcript_df.iloc[-1]
    prior_interaction = single_transcript_df.iloc[-2]
    if last_interaction['isInbound']==False and prior_interaction['isInbound']==True:
        # if last_interaction['messageType']=='VOICE':
        target_prospect = True
        logger.info('Prospect is a target. Last interaction was not "isInbound" to chatbot and prior interaction was "isInbound" to chatbot.')
    else:
        logger.info('Prospect is not a target. Last interaction was "isInbound" to chatbot or prior interaction was not "isInbound" to chatbot.')
    return target_prospect


def check_for_targets_and_time_elapsed(day_transcripts_df, logger_name):
    logger = logging.getLogger(f'{logger_name}.check_for_targets_and_time_elapsed')
    outreach_flag_df = pd.DataFrame()
    hour_waitlist_df = pd.DataFrame()
    for prospect_transcript in day_transcripts_df['transcript'].unique():
        single_prospect_transcript_df = day_transcripts_df[day_transcripts_df['transcript']==prospect_transcript]
        target_prospect_bool = is_target_prospect(single_prospect_transcript_df)
        if target_prospect_bool:
            seconds_elapsed = (single_prospect_transcript_df['timeCreated'][-1] - datetime.now(timezone.utc)).total_seconds()
            single_prospect_transcript_df['seconds_elapsed'] = seconds_elapsed
            if seconds_elapsed > 3600:
                outreach_flag_df = pd.concat([outreach_flag_df, single_prospect_transcript_df],
                                            axis=0,
                                            ignore_index=True)
            else:
                hour_waitlist_df = pd.concat([hour_waitlist_df, single_prospect_transcript_df],
                                            axis=0,
                                            ignore_index=True)
    return outreach_flag_df, hour_waitlist_df


def update_outreach_dashboard(outreach_flag_df, logger_name):
    # need to understand Azure Functions a bit better first
    return


def save_and_update_hour_waitlist_backups(hour_waitlist_df, logger_name):
    logger = logging.getLogger(f'{logger_name}.save_and_update_hour_waitlist_backups')
    if not os.path.exists(os.path.abspath('/hour_waitlist_data/')):
        os.mkdir(os.path.abspath('/hour_waitlist_data/'))
    os.chdir(os.path.abspath('/hour_waitlist_data/'))
    old_hour_waitlist_file_path = os.path.abspath('/most_recent_hour_waitlist.csv')
    if os.path.exists(old_hour_waitlist_file_path):
        now_val = datetime.now()
        os.rename(old_hour_waitlist_file_path, os.path.abspath(f'hour_waitlist_data/hour_waitlist_backup_{now_val.month}-{now_val.date}_{now_val.hour}-{now_val.min}.csv'))
    hour_waitlist_df.to_csv(old_hour_waitlist_file_path, index=False)
    list_of_files = os.listdir()
    full_path = [os.path.abspath(file_name) for file_name in list_of_files]
    if len(list_of_files) > 10:
        oldest_file = min(full_path, key=os.path.getctime)
        os.remove(oldest_file)
    os.chdir(os.path.dirname(os.getcwd()))
    return


def api_calling_main(logger_name, save_dir, logger_verbosity):
    setup_logging(save_dir=save_dir,
                  logger_name=logger_name,
                  verbosity=logger_verbosity)
    daily_prospects_df = call_api_for_daily_csv(build_url(logger_name, today=False, year='2022', month='05'), logger_name)
    daily_transcripts_df = read_transcripts(daily_prospects_df, logger_name)
    outreach_flag_df, hour_waitlist_df = check_for_targets_and_time_elapsed(daily_transcripts_df, logger_name)
    update_outreach_dashboard(outreach_flag_df, logger_name)
    save_and_update_hour_waitlist_backups(hour_waitlist_df, logger_name)
    return


if __name__=="__main__":
    api_calling_main(logger_name='chatbot_prospect_api_calling',
                     save_dir='C:/Users/rburns/Documents/Chatbot_Prospect_Workspace/',
                     logger_verbosity=10)
