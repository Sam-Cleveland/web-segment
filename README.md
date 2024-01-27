# Web Segment

This project contains scripts for scraping websites and extracting useful information such as emails, phone numbers, and social media links. As well as finding segmentation variables via the openAI and Page Speed APIs.

## Files

- [manual_parse.py](web_segment/manual_parse.py): Contains functions for finding and extracting emails, phone numbers, and social media links from text.
- [openai_segment.py](web_segment/openai_segment.py): Contains the code for interfacing with the OpenAI Platform API.
- [site_scraper.py](web_segment/site_scraper.py): Contains functions for scraping the contents of the webpage itself and parsing it into useable plain text.
- [site_segmentation.py](web_segment/site_segmentation.py): Main file which combines all the tools and provides a compiled output.
- [webhook.py](web_segment/webhook.py): File for hosting the web segment tool as a webhook using Flask.

## Installation

1. Clone the repository
2. Install the required packages using pip:

```sh
pip install -r requirements.txt
```

## Usage

To use the website segment tool manually:

```sh
python web_segment/site_segmentation.py <url> [basic or nothing]
```

Replace `<url>` with the URL of the site you want to scrape, add `basic` for a basic scrape (defaults to deep).

To start the webhook in developement mode:

```sh
python web_segment/webhook.py [port=5000] [host=127.0.0.1] [debug or nothing]
```

Optionally add port and host (default to 127.0.0.1:5000). Add `debug` for debug output

To deploy the webhook, you should use a production WSGI server such as `gunicorn`:

```sh
pip install gunicorn
gunicorn -b [host]:[port] web_segment.webhook:app
```