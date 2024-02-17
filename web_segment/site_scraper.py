import sys
import logging
import requests
import json
from urllib.parse import urlparse, urlsplit
from datetime import datetime
from dateutil.parser import parse as parse_date

from bs4 import BeautifulSoup
from bs4.element import NavigableString

KEYWORDS = ['home', 'about', 'contact', 'learn', 'importantpage=true']

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}

def get_html(url):
	"""
	This function loads the given page and returns the html as a string.
	
	Parameters:
	url (str): The URL of the page to load.
	
	Returns:
	str: The html of the page.
	"""
	output = {
		'html': '',
		'HTTPS': False,
	}
	response = requests.get(url, headers=HEADERS)
	if response.status_code != 200:
		logging.info('Error loading page ' + url + ' with status code ' + str(response.status_code))
		raise Exception('Error loading page ' + url + ' with status code ' + str(response.status_code))
	if response.url[0:5] == 'https':
		output['HTTPS'] = True
	logging.info('GET ' + url)
	output['html'] = response.text
	return output

def get_text(page_url: str) -> str: 
	"""
	This function scrapes the given page and uses the BeautifulSoup library to parse all text elements from the html and concatenate them into a single string.
	
	Parameters:
	page_url (str): The URL of the page to scrape.

	Returns:
	str: A string containing all the text found on the page.
	"""
	load = get_html(page_url)
	html = load['html']
	parse = BeautifulSoup(html, 'lxml')
	text = ''
    
	for tag in parse.recursiveChildGenerator():
		if type(tag) is NavigableString:
			if (tag.strip() == ''):
				continue
			text += tag.strip() + '\n'
		elif tag.name == 'a' and tag.has_attr('href'):
			text += tag['href'] + '\n'
	# text = [s for s in parse._all_strings()]
	return {'text': text, 'HTTPS': load['HTTPS']}

def extract_sitemap(home_url: str):
	"""
	Extracts the pages from the sitemap of a website. If the sitemap is a sitemap index, it will extract all the sitemaps from the index and then extract the urls from each sitemap.

	Parameters:
	home_url (str): The URL of the website to extract the sitemap from.

	Returns:
	dict: A dictionary containing `date` and `urls` keys. The `date` key contains the date the sitemap was last modified. The `urls` key contains a list of URLs found in the sitemap.
	"""
	output = {
		'date': None,
		'urls': [],
	}
	response = requests.get(home_url + '/sitemap.xml', headers=HEADERS)
	if response.status_code != 200:
		logging.info('No sitemap found for ' + home_url)
		response = requests.get(home_url + '/sitemap_index.xml', headers=HEADERS)
		if response.status_code != 200:
			logging.info('No sitemap index found for ' + home_url)
			return output
	html = response.text
	if '<sitemapindex' in html:
		logging.info('sitemap index found')
		sitemap_output = parse_sitemap(html)
		output['date'] = sitemap_output['date']
		for sitemap in sitemap_output['sitemap']:
			sub_response = requests.get(sitemap, headers=HEADERS);
			if sub_response.status_code != 200:
				logging.info('Error loading sitemap ' + sitemap)
				continue
			sub_sitemap = parse_sitemap(sub_response.text)
			output['urls'].extend(sub_sitemap['sitemap'])
	elif '<urlset' in html:
		logging.info('sitemap found')
		sitemap_output = parse_sitemap(html)
		output['date'] = sitemap_output['date']
		output['urls'].extend(sitemap_output['sitemap'])
	else:
		logging.info('Sitemap seems to be formatted incorrectly.')
	return output

def parse_sitemap(xml: str):
	"""
	Parses a sitemap from XML text.

	Parameters:
	xml (str): The XML text to parse.

	Returns:
	dict: A dictionary containing `date` and `sitemap` keys. The `date` key contains the date the sitemap was last modified. The `sitemap` key contains a list of URLs found in the sitemap.
	"""
	parse = BeautifulSoup(xml, 'lxml-xml')
	output = {
		'date': None,
		'sitemap': [],
	}
	date = datetime.min.replace(tzinfo=None)
	for tag in parse.find_all('loc'):
		output['sitemap'].append(tag.text.strip())
	for tag in parse.find_all('lastmod'):
		try:
			dt = parse_date(tag.text.strip())
		except ValueError:
			continue
		if dt.tzinfo is not None:
			dt = dt.replace(tzinfo=None)
		if dt > date:
			date = dt
	if (date != datetime.min):
		output['date'] = date.strftime('%Y-%m-%d')
	return output

def scrape_links(home_url: str) -> list:
	"""
	Finds all the internal links on the given page.
	
	Parameters:
	home_url (str): The URL of the page to scrape.

	Returns:
	list: A list of URLs found on the page. 
	"""
	html = get_html(home_url)['html']

	hostname = urlsplit(home_url).hostname
	parse = BeautifulSoup(html, 'lxml')
	urls = []
	for a in parse.find_all('a'):
		if not a.has_attr('href') or a['href'] == '':
			continue
		if hostname in a['href']:
			urls.append(a['href'])
		elif a['href'][0] == '/':
			urls.append('https://' + hostname + a['href'])
		# If link text contains any of the keywords, mark it as important
		if any(keyword in a.get_text().lower() for keyword in KEYWORDS):
			urls[-1] += '?importantpage=true'
	return urls

def get_pages(url: str):
	"""
	This function returns a list of all the pages on the given site.
	
	Parameters:
	url (str): The URL of the site to scrape.

	Returns
	"""
	sitemap = extract_sitemap(url)
	hostname = urlsplit(url).hostname
	if len(sitemap['urls']) == 0:
		sitemap['hasSitemap'] = False
	else:
		sitemap['hasSitemap'] = True
	sitemap['urls'].extend(scrape_links(url))
	sitemap['urls'] = [url.strip() for url in sitemap['urls'] if hostname in url]
	sitemap['urls'] = [normalize_url(url) for url in sitemap['urls']]
	sitemap['urls'] = list(set(sitemap['urls']))
	return sitemap

def normalize_url(url):
    parsed = urlparse(url)
    scheme = parsed.scheme or 'http'
    netloc = parsed.netloc or parsed.path
    if netloc.startswith('www.'):
        netloc = netloc[4:]
    return scheme + '://' + netloc

def scrape_site(url: str, deep: bool) -> dict:
	"""
	This function scrapes the given site.

    Parameters:
    url (str): The URL of the site to scrape.
    deep (bool): If True, the function will perform a deep scrape.

    Returns:
    dict: An object containing information about the site matching the following format:
	{
		'hasSitemap': bool,
		'lastModified' : str (yyyy-mm-dd),
		'pages' : dict,
		'HTTPS' : bool,
	}
	"""
	# Initialize output object
	output = {
		'url': None,
		'hasSitemap': None,
		'lastModified' : None,
		'pages' : {},
		'HTTPS' : False,
	}

	# Scrape main page
	url = 'https://' + urlsplit(url).netloc
	output['url'] = url
	load = get_html(url)
	output['pages'][url] = BeautifulSoup(load['html'], 'lxml')
	output['HTTPS'] = load['HTTPS']
	sitemap_output = get_pages(url)


	output['hasSitemap'] = sitemap_output['hasSitemap']
	if sitemap_output['date'] is not None:
		output['lastModified'] = sitemap_output['date']

	# Deep scrape
	if deep:
		sitemap = sitemap_output['urls']
		sitemap = list(set(sitemap))

		# Scrape all pages
		for page in sitemap:
			try:
				page_parse = BeautifulSoup(get_html(page)['html'], 'lxml')
			except:
				logging.info('Error loading page ' + page)
				continue
			if (page == url):
				continue
			output['pages'][page] = page_parse
	return output

if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
	
	# Parse input arguments
	deep = True
	if len(sys.argv) >= 2:
		URL = sys.argv[1]
		URL = 'https://' + urlsplit(URL).netloc
	else:
		print('No URL found in arguments')
		exit(1)
	if len(sys.argv) >= 3 and (sys.argv[2] == 'basic'):
		depp = False
	
	scrape = scrape_site(URL, deep)
	print(scrape['lastModified'])
	with open('output.json', 'w') as f:
		f.write(json.dumps(scrape, indent=2))
