# Prospect_Ranked_Follow-up_App
 An application for pulling daily prospects 

## Project Overview ##
 This serverless app is designed to automate the daily collection of prospect outreach transcripts from a chatbot service, identify prospects who did not respond to the last outreach from the chatbot for manual follow-up the following day. The application also employs multiple out-of-the-box sentiment analysis libraries to enable ranked order of prospect follow-up by message sentiment. The ranked outreach lists are hosted 

 The application is built with Python 3.10.4 and Flask. Additional dependencies are listed in the requirements.txt file. Commands provided in this document are designed to be run in Powershell on Windows 10.

### Build From Scratch Walkthrough ###

1. Create a new GitHub repository locally. Create and activate a virtual environment.
```
python -m venv .venv
.\.venv\Scripts\activate.ps1
```

2. Create project files.
```
New-Item -Path . -Name ".env" -ItemType "file"
```

3. Install the required dependencies from requirements.txt into the virtual environment.
```
pip install -r requirements.txt
```

Additionally, flair currently has a dependency on the sentencepiece library which does not have a compatible wheel for Python 3.10 to enable installation via pip. Instead, I recommend downloading and installing the sentencepiece library separately using the conda command below in Anaconda Prompt. After the install command is complete, copy the package files from /anaconda3/Lib/site-packages into your virtual environment at ./.venv/Lib/site-packages.
```
conda install -c sentencepiece
```

Finally, run the below commands to install the NLTK and Textblob corpora to enable sentiment analysis and stopword removal from our messages.
```
python -m textblob.download_corpora
python -m nltk.downloader popular
```

