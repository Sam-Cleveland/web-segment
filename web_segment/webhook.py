import logging
import os
import sys
from flask import Flask, request
from urllib.parse import urlsplit
from threading import Thread
from datetime import datetime

import web_segment.site_segmentation as site_segmentation

app = Flask(__name__)

API_KEY = 'REDACTED_WEBHOOK_KEY'

@app.route('/scrape_site', methods=['POST'])
def webhook():
    # Check if API key is valid
    api_key = request.headers.get('Authorization')
    if not api_key or api_key != API_KEY:
        return 'Invalid API key', 401
    if request.method == 'POST':
        # Get all variables from request
        deep = False if request.json.get('deep') is None else True
        url = request.json.get('url')
        accountId = request.json.get('accountId')

        # If any variables are missing, return error
        if url is None:
            return 'No \'url\' provided', 400
        if accountId is None:
            return 'No \'accountId\' provided', 400
        
        # If logs/ directory does not exist, create it
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        # Start site segmentation in a new thread
        filename = 'logs/' + urlsplit(url).netloc + datetime.now().strftime('_%Y-%m-%d_%H-%M-%S') + '.log'
        logging.basicConfig(level=logging.INFO, filename=filename, format='%(asctime)s - %(message)s')
        thread = Thread(target=site_segmentation.main, args=(url, accountId, deep))
        thread.start()
        
        return 'success', 200
    else:
        return 'Invalid request', 400

if __name__ == '__main__':
    # # get IP and port from python arguments
    # print(len(sys.argv))
    # if len(sys.argv) > 1 and sys.argv[1] == 'help':
    #     print('Usage: python web-segment/webhook.py [port=5000] [host=127.0.0.1] [debug or nothing]')
    #     sys.exit(0)
    # port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    # host = sys.argv[2] if len(sys.argv) > 2 else '127.0.0.1'
    # debug = sys.argv[3].lower() == 'debug' if len(sys.argv) > 3 else False
    # app.run(host=host, port=port, debug=debug)
    app.run(host='127.0.0.1', port=80, debug=False)