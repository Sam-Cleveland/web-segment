import re
import sys
import logging

from bs4 import NavigableString

def find_emails(text):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    matches = re.findall(regex, text)
    return [''.join(match) for match in matches]
def extract_emails(pages):
    return list(set(find_emails(full_text(pages))))

def find_phone_numbers(text):
    regex = r"(?:\+\d{1,2}\s)?(?:\(?\d{3}\)?)?[\s.-]?\d{3}[\s.-]?\d{4}"
    matches = re.findall(regex, text)
    matches = [match.replace(' ', '').replace('-', '').replace('(', '').replace(')', '') for match in matches]
    return matches

def extract_phone_numbers(pages):
    return list(set(find_phone_numbers(full_text(pages))))

def find_social_media_links(text):
    regex = r'(https?://(?:www\.)?(?:facebook|twitter|instagram|linkedin|youtube|tiktok)\.com/[^\s]+)'
    matches = re.findall(regex, text)
    return [''.join(match) for match in matches];

def extract_social_media_links(pages):
    return list(set(find_social_media_links(full_text(pages))));

def full_text(pages):
    text = ''
    for page in pages:
        for tag in page.recursiveChildGenerator():
            if type(tag) is NavigableString:
                if (tag.strip() == ''):
                    continue
                if tag.parent.has_attr('style') and ('display:none' in tag.parent['style'] or 'display: none' in tag.parent['style']):
                    continue
                text += tag.strip() + '\n'
            elif tag.name == 'a' and tag.has_attr('href'):
                text += tag['href'] + '\n'
    return text

def text(pages):
    text = ''
    for page in pages:
        for tag in page.recursiveChildGenerator():
            if type(tag) is NavigableString:
                if (tag.strip() == ''):
                    continue
                if tag.parent.has_attr('style') and ('display:none' in tag.parent['style'] or 'display: none' in tag.parent['style']):
                    continue
                text += tag.strip() + '\n'
    return text
