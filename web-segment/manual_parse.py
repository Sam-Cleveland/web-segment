import re
import sys
import site_scraper
import logging

def find_emails(text):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    matches = re.findall(regex, text)
    return [''.join(match) for match in matches]
def extract_emails(jsonScrape):
    return list(set(find_emails(json_to_text(jsonScrape))))

def find_phone_numbers(text):
    regex = r'''[\.\-)( ]*([0-9]{3})[\.\-)( ]*([0-9]{3})[\.\-)( ]*([0-9]{4})'''
    matches = re.findall(regex, text)
    return [''.join(match) for match in matches]

def extract_phone_numbers(jsonScrape):
    return list(set(find_phone_numbers(json_to_text(jsonScrape))))

def find_social_media_links(text):
    regex = r'(https?://(?:www\.)?(?:facebook|twitter|instagram|linkedin|youtube)\.com/[^\s]+)'
    matches = re.findall(regex, text)
    return [''.join(match) for match in matches];

def extract_social_media_links(jsonScrape):
    return list(set(find_social_media_links(json_to_text(jsonScrape))));

def json_to_text(jsonScrape):
    text = jsonScrape['mainPageText']
    if jsonScrape['pages'] == None:
        return text
    for page in jsonScrape['pages']:
        text += '\n\n' + jsonScrape['pages'][page]
    return text

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

    if len(sys.argv) == 1:
        print('Usage: python -m site_scraper <url>')
        sys.exit(1)
    
    deep = False
    if len(sys.argv) == 3:
        deep = sys.argv[2] == 'deep';
    
    segmentation_variables = {};

    # Scrape text from web pages
    site_scrape = site_scraper.scrape_site(sys.argv[1], False)

    emails = extract_emails(site_scrape);
    emails = ', '.join(emails);
    phone_numbers = extract_phone_numbers(site_scrape);
    phone_numbers = ', '.join(phone_numbers);
    social_media_links = extract_social_media_links(site_scrape);
    social_media_links = ', '.join(social_media_links);

    logging.info(emails)
    logging.info(phone_numbers)
    logging.info(social_media_links)
    logging.info(site_scrape['lastModified'])
