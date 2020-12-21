# Welcome to Trademe Scraper

This is a scraper that extracts pricing information on Trademe using its own searching engine.

## To have things working alone in this repo
	
	```console
	$ git clone git@github.com:Gabriel1443/trademe-search-engine.git
	$ cd trademe-search-engine
	$ python3 -m venv env
	$ source env/bin/activate
	$ pip install pip-tools
	(env) $ pip-sync
	```
	
## Functionality now

- `python3 trademe_scraper.py` will scrapes all prices under keyword "makeup container". The infrastructure will be fixed when needed, still a young programme. Everything should be modified under `trademe_scraper.py`.