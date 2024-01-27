import sys
import os
import json
import requests
import logging

import site_scraper
import openai_segment
import manual_parse

def main(url, accountId, deep):
    # Initialize output object
    site_scrape_data = {
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

    # Scrape text from web pages
    logging.info('Scraping ' + url + ' ...')
    # Site scrape keys: mainPageText, hasSitemap, lastModified, pages, HTTPS
    site_scrape = site_scraper.scrape_site(url, deep)
    logging.info('Scraped ' + url)

    # Save site scrape to file
    file = open('output.json', 'w')
    file.write(json.dumps(site_scrape, indent=2))

    # Add manually found segmentation variables to output object
    site_scrape_data['site_analysis']['hasSitemap'] = site_scrape['hasSitemap']
    site_scrape_data['site_analysis']['lastModified'] = site_scrape['lastModified']
    site_scrape_data['tech_analysis']['HTTPS'] = site_scrape['HTTPS']

    # Test Site Security + Uptime
    PAGESPEED_API_URL = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed'
    params = {
        'url': url,
        'strategy': 'desktop',
        'category': ['performance', 'accessibility', 'best-practices', 'seo'],
    }
    logging.info('Getting info via PageSpeed API...')
    response = requests.get(PAGESPEED_API_URL, params=params)
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
    
    # Use regex to find all phone numbers, emails, and social media links in the text
    logging.info('Extracting emails, phone numbers, and social media links with regex...')
    emails = ', '.join(manual_parse.extract_emails(site_scrape));
    phone_numbers = ', '.join(manual_parse.extract_phone_numbers(site_scrape));
    social_media_links = ', '.join(manual_parse.extract_social_media_links(site_scrape));
    logging.info('Extracted emails, phone numbers, and social media links with regex')

    # Add emails, phone numbers, and social media links to output object
    site_scrape_data['contact_info']['emails'] = emails
    site_scrape_data['contact_info']['phoneNumbers'] = phone_numbers
    site_scrape_data['contact_info']['socialMediaLinks'] = social_media_links

    # Use openai model to identify segmentation variables
    logging.info('Identifying segmentation variables with OpenAI...')
    openai_segmentation_variables = openai_segment.segment_variables(open('output.json', 'rb'))
    logging.info('Identified segmentation variables with OpenAI')

    # Add openai segmentation variables to output object
    site_scrape_data['segmentation']['businessName'] = openai_segmentation_variables['businessName']
    site_scrape_data['site_analysis']['language'] = openai_segmentation_variables['language']
    site_scrape_data['segmentation']['areaOfFocus'] = openai_segmentation_variables['areaOfFocus']
    site_scrape_data['segmentation']['accountType'] = openai_segmentation_variables['accountType']
    site_scrape_data['segmentation']['location'] = openai_segmentation_variables['location']

    # Delete output.json
    os.remove('output.json')

    # # Save segmentation to output file
    # filename = 'output.json'
    # if site_scrape_data['segmentation']['businessName'] != None:
    #     filename = site_scrape_data['segmentation']['businessName'] + '.json'
    # file = open(filename, 'w')
    # file.write(json.dumps(site_scrape_data, indent=2))

    return site_scrape_data

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    deep = True
    if len(sys.argv) < 3:
        print('Usage: python site_segmentation.py <url> <accountId> <deep|basic>')
        sys.exit(1)
    if len(sys.argv) >= 4:
        deep = sys.argv[3] == 'deep';
    url = sys.argv[1]
    accountId = sys.argv[2]
    site_scrape = main(url, accountId, deep)

    # Connect to CRM / Next steps
    logging.info('Sending output to Zoho')
    ZOHO_API_URL = 'https://www.zohoapis.com/crm/v2/functions/url_scrape_results/actions/execute?auth_type=apikey&zapikey=REDACTED_ZOHO_KEY'
    headers = {
        'Content-Type': 'application/json'
    }
    data = site_scrape
    response = requests.post(ZOHO_API_URL, headers=headers, data=json.dumps(data))