#import fast_bert
#from fast_bert.data_cls import BertDataBunch
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import pandas as pd
from textblob import TextBlob
from textblob.sentiments import NaiveBayesAnalyzer
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from flair.models import TextClassifier
from flair.data import Sentence
import string


def calculate_vader_sentiment(messages_df, filtered=False):
    # calculate score from vaderSentiment
    if filtered:
        target_col = 'no_stopwords_message_text'
        filtered_flag = '_filtered'
    else:
        target_col = 'censoredShortBody'
        filtered_flag = ''
    analyzer = SentimentIntensityAnalyzer()
    scored_messages_df = pd.DataFrame()
    for index, sentence_transcript_entry in enumerate(messages_df):
        vader_scores = analyzer.polarity_scores(sentence_transcript_entry[target_col])
        temp_df = pd.DataFrame({f'compound_polarity{filtered_flag}_VS': vader_scores['compound'],
                                f'positive_ratio{filtered_flag}_VS': vader_scores['pos'],
                                f'negative_ratio{filtered_flag}_VS': vader_scores['neg'],
                                f'neutral_ratio{filtered_flag}_VS': vader_scores['neu']},
                               index=[0])
        temp_df = pd.concat([sentence_transcript_entry.to_frame().T, temp_df],
                            axis=1,
                            ignore_index=True)
        scored_messages_df = pd.concat([scored_messages_df, temp_df], axis=0, ignore_index=True)
    return scored_messages_df


def calculate_textblob_sentiment(messages_df, filtered=False):
    # calculate score from TextBlob - uses both the default PatternAnalyzer and the alternative NaiveBayesAnalyzer
    if filtered:
        target_col = 'no_stopwords_message_text'
        filtered_flag = '_filtered'
    else:
        target_col = 'censoredShortBody'
        filtered_flag = ''
    tb_sentiment_PA_polarity = [TextBlob(message).sentiment.polarity for message in messages_df[target_col]]
    tb_sentiment_PA_subj = [TextBlob(message).sentiment.subjectivity for message in messages_df[target_col]]
    tb_sentiment_NBA = [TextBlob(message, analyzer=NaiveBayesAnalyzer()).sentiment for message in messages_df[target_col]]
    tb_sentiment_NBA_class = [sentiment['classification'] for sentiment in tb_sentiment_NBA]
    tb_sentiment_NBA_pos_ratio = [sentiment['p_pos'] for sentiment in tb_sentiment_NBA]
    messages_df[f'sentiment_polarity{filtered_flag}_TB_PA'] = tb_sentiment_PA_polarity
    messages_df[f'sentiment_subjectivity{filtered_flag}_TB_PA'] = tb_sentiment_PA_subj
    messages_df[f'sentiment_classification{filtered_flag}_TB_NBA'] = tb_sentiment_NBA_class
    messages_df[f'sentiment_pos_percent_TB{filtered_flag}_NBA'] = tb_sentiment_NBA_pos_ratio
    return messages_df


def remove_stopwords_from_mesages(messages_df, filter_punctuation=True):
    stop_words = set(stopwords.words('english'))
    if filter_punctuation:
        stop_words = stop_words + list(string.punctuation)
    no_sw_message_list = []
    for index, sentence_transcript_entry in enumerate(messages_df):
        message_word_tokens = word_tokenize(sentence_transcript_entry['censoredShortBody'])
        filtered_sentence = [word for word in message_word_tokens if not word.lower() in stop_words]
        no_sw_message_list.append(filtered_sentence)
    messages_df['no_stopwords_message_text'] = no_sw_message_list
    return messages_df


def calculate_flair_sentiment(messages_df, filtered=False):
    classifier = TextClassifier.load('en-sentiment')
    flair_sentiment_score_list = []
    if filtered:
        target_col = 'no_stopwords_message_text'
        filtered_flag = '_filtered'
    else:
        target_col = 'censoredShortBody'
        filtered_flag = ''
    for message in messages_df[target_col]:
        message = Sentence(message)
        classifier.predict(message)
        value = message.labels[0].to_dict()['value']
        if value == 'POSITIVE':
            result = message.to_dict()['labels'][0]['confidence']
        else:
            result = -(message.to_dict()['labels'][0]['confidence'])
        result = round(result, 3)
        flair_sentiment_score_list.append(result)
    messages_df[f'flair_sentiment_score{filtered_flag}'] = flair_sentiment_score_list
    return messages_df


def main(messages_df):
    messages_df = calculate_vader_sentiment(messages_df)
    messages_df = calculate_textblob_sentiment(messages_df)
    messages_df = calculate_flair_sentiment(messages_df)
    messages_df = remove_stopwords_from_mesages(messages_df, filter_punctuation=True)
    messages_df = calculate_vader_sentiment(messages_df, filtered=True)
    messages_df = calculate_textblob_sentiment(messages_df, filtered=True)
    messages_df = calculate_flair_sentiment(messages_df, filtered=True)
    return messages_df


if __name__=='__main__':
    main(messages_df='')