## Setup

1. Create a .env file in the application root copying it from `example.env`
1. Run `pip install -r dev-requirements.txt`
1. Follow the instructions [here](https://developers.google.com/sheets/api/quickstart/python)
   to get a `credentials.json` file
1. Run `./run.py setup_gsheet`

## Usage

To import files from a folder run:

    ./run.py import_files  # you can specify the folder, default is set in .env file
