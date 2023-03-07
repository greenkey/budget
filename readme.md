## Setup

1. Create a .env file in the application root copying it from `example.env`
1. Run `pip install -r dev-requirements.txt`
1. Follow the instructions [here](https://developers.google.com/sheets/api/quickstart/python)
   to get a `credentials.json` file
1. Run `./run.py setup_gsheet`

## If you want to connect to Splitwise API

1. Register a new app [here](https://secure.splitwise.com/oauth_clients)
1. Create an API key too
1. Set `SPLITWISE_CONSUMER_KEY`, `SPLITWISE_CONSUMER_SECRET` and `SPLITWISE_API_KEY` in your `.env`


## Usage

To import files from a folder run:

    ./run.py import_files  # you can specify the folder, default is set in .env file
