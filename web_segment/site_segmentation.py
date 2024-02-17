import sys
import os
import json
import traceback
from urllib.parse import urlsplit
import requests
import logging

from openai import BadRequestError

try:
    import web_segment.site_scraper as site_scraper
    import web_segment.openai_segment as openai_segment
    import web_segment.manual_parse as manual_parse
    from web_segment.site_scraper import KEYWORDS
except ModuleNotFoundError:
    import site_scraper
    import openai_segment
    import manual_parse
    from site_scraper import KEYWORDS


def main(url, accountId, use_pagespeed=True, use_openai=True, openai_model='gpt-3.5-turbo', save_output=False):
    # Initialize output object
    site_scrape_data = {
        'status': 'success',
        'url': url,
        'accountId': accountId,
        'contact_info':{
            'emails': None,
            'phoneNumbers': None,
            'socialMediaLinks': None,
        },
        'segmentation':{
            'businessName': None,
            'areaOfFocus': None,
            'accountType': None,
            'location': None,
        },
        'site_analysis':{
            'language': None,
            'hasSitemap': None,
            'pageCount': None,
            'lastModified': None,
            'performance': None,
            'accessibility': None,
            'best_practices': None,
            'seo': None,
        },
        'tech_analysis':{
            'HTTPS': None,
        }
    };
    try:
        # Scrape text from web pages
        logging.info('Scraping ' + url + ' ...')
        # Site scrape keys: mainPageText, hasSitemap, lastModified, pages, HTTPS
        site_scrape = site_scraper.scrape_site(url, True)
        logging.info('Scraped ' + url)

        # Add manually found segmentation variables to output object
        site_scrape_data['site_analysis']['hasSitemap'] = site_scrape['hasSitemap']
        site_scrape_data['site_analysis']['lastModified'] = site_scrape['lastModified']
        site_scrape_data['site_analysis']['pageCount'] = len(site_scrape['pages'])
        site_scrape_data['tech_analysis']['HTTPS'] = site_scrape['HTTPS']
        
        # Use regex to find all phone numbers, emails, and social media links in the text
        pages = site_scrape['pages'].values()
        logging.info('Extracting emails, phone numbers, and social media links with regex...')
        emails = ', '.join(manual_parse.extract_emails(pages));
        phone_numbers = ', '.join(manual_parse.extract_phone_numbers(pages));
        social_media_links = ', '.join(manual_parse.extract_social_media_links(pages));
        logging.info('Extracted emails, phone numbers, and social media links with regex')

        # Add emails, phone numbers, and social media links to output object
        site_scrape_data['contact_info']['emails'] = emails
        site_scrape_data['contact_info']['phoneNumbers'] = phone_numbers
        site_scrape_data['contact_info']['socialMediaLinks'] = social_media_links

        if use_openai:
            # Use openai model to identify segmentation variables
            logging.info('Identifying segmentation variables with OpenAI...')
            openai_segment.MODEL = openai_model
            pages = site_scrape['pages'].keys()
            logging.info('Pages in website: ' + ', '.join(pages))
            selected_pages = [site_scrape['url']]
            # Only include urls that have one of KEYWORDS in it
            selected_pages += [page for page in pages if any(keyword in page.lower() for keyword in KEYWORDS)]
            if len(pages) >= (10-len(selected_pages)):
                selected_pages += openai_segment.select_pages(pages)
            else:
                selected_pages += pages
            selected_pages = list(set(selected_pages))
            temp = []
            for page in selected_pages:
                if page in site_scrape['pages']:
                    temp.append(site_scrape['pages'][page])
            selected_pages = temp
            text = manual_parse.text(selected_pages)
            openai_segmentation_variables = openai_segment.segment(text)
            logging.info('Identified segmentation variables with OpenAI')

            # Add openai segmentation variables to output object
            site_scrape_data['segmentation']['businessName'] = openai_segmentation_variables['businessName']
            site_scrape_data['site_analysis']['language'] = openai_segmentation_variables['language']
            site_scrape_data['segmentation']['areaOfFocus'] = openai_segmentation_variables['areaOfFocus']
            site_scrape_data['segmentation']['accountType'] = openai_segmentation_variables['accountType']
            site_scrape_data['segmentation']['location'] = openai_segmentation_variables['location']

        if use_pagespeed:
            # Test Site Security + Uptime
            PAGESPEED_API_URL = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed'
            params = {
                'url': url,
                'strategy': 'desktop',
                'category': ['performance', 'accessibility', 'best-practices', 'seo'],
            }
            logging.info('Getting info via PageSpeed API...')
            response = requests.get(PAGESPEED_API_URL, params=params)
            logging.info('GET ' + response.url)
            data = response.json()
            logging.info('Got info via PageSpeed API')

            # Extract the four scores
            performance = data['lighthouseResult']['categories'].get('performance', {}).get('score', None)
            accessibility = data['lighthouseResult']['categories'].get('accessibility', {}).get('score', None)
            best_practices = data['lighthouseResult']['categories'].get('best-practices', {}).get('score', None)
            seo = data['lighthouseResult']['categories'].get('seo', {}).get('score', None)

            # Add lighthouse scores to output object
            site_scrape_data['site_analysis']['performance'] = performance
            site_scrape_data['site_analysis']['accessibility'] = accessibility
            site_scrape_data['site_analysis']['best_practices'] = best_practices
            site_scrape_data['site_analysis']['seo'] = seo

        if save_output:
            # # Save segmentation to output file
            filename = 'output.json'
            file = open(filename, 'w')
            file.write(json.dumps(site_scrape_data, indent=2))
    except Exception as e:
        site_scrape_data['status'] = 'failure'
        logging.error('Error: ' + str(e))
        logging.error(traceback.format_exc())
        site_scrape_data['error'] = str(e)
    
    # Send output to Zoho
    # logging.info('Sending output to Zoho...')
    # ZOHO_API_URL = 'https://www.zohoapis.com/crm/v2/functions/url_scrape_results/actions/execute?auth_type=apikey&zapikey=REDACTED_ZOHO_KEY'
    # response = requests.post(ZOHO_API_URL, json=site_scrape_data)
    # logging.info('POST ' + response.url)
    # logging.info('Sent output to Zoho')
    return site_scrape_data

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    if len(sys.argv) < 2 or sys.argv[1] == 'help':
        print('Usage: python web-segment/site_segmentation.py <url> [basic or nothing]')
        sys.exit(1)
    url = sys.argv[1]
    deep = not (sys.argv[2].lower() == 'basic') if len(sys.argv) > 2 else True
    
    site_scrape = main(url, None, deep)
    
    # Write output to file
    filename = 'output/' + urlsplit(site_scrape['url']).netloc + '.json'

    with open(filename, 'w') as f:
        f.write(json.dumps(site_scrape, indent=2))

    # Print output to console
    print(json.dumps(site_scrape, indent=2))
    print('Chat token usage: ' + str(openai_segment.chat_tokens_usage))
    print('Chat prompt count: ' + str(openai_segment.chat_prompt_count))
    print('Assistants token usage: ' + str(openai_segment.assistant_tokens_usage))
    print('Assistants prompt count: ' + str(openai_segment.assistant_prompt_count))