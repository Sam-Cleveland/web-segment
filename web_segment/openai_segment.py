import os
import shutil
import time
import json
import sys
import logging

from openai import OpenAI

chat_tokens_usage = 0
chat_prompt_count = 0
assistant_tokens_usage = 0;
assistant_prompt_count = 0;

OPENAI_API_KEY_COACHIQ='REDACTED_OPENAI_KEY'
MODEL='gpt-3.5-turbo'
RELOAD_TIME_DELAY=5

# System prompts
PAGE_SELECTOR_SYS_PROMPT = '''
You will be given a list of webpage names from a business website. You will decide based on url name which of these webpages would have text which is useful for identifying the following about the website:
What is the business name?
What primary city, state is this business based in?
What language is the website written in?
What sport/topic does this business specialize in? 
Is there a specific element of this sport that they focus on?
What type of business/program is this? 
What product/service do they sell/provide?

Only choose webpages that would have text with useful information. Generally include webpages that would commonly have information such as the home/about/contact page. Respond with a comma separated list of the website urls you decide would have useful information. Pick at most 10 webpages max in order of likely importance. Respond with ONLY the comma separated list and no explanation.
'''
VARIABLE_IDENTIFIER_SYS_PROMPT = '''
You will be provided with a short description of a business.

Your job is to read the description and identify these key classification variables based on the information on the website:
businessName (official name of the business)
location (try to fit [City], [State abbreviation] format or whatever information you have if not possible)
language (what language is the website text written in?)
areaOfFocus (What sport/topic does this business specialize in? Must be one of the following: Soccer, Skateboarding, Running, Rugby, Recruiting, Racquetball, Pickleball, Physical Therapy,  Personal Training, Nutrition, Non-Athletic, Multi-Disciplinary, Movement, MMA, Mental Performance, Lacrosse, Judo, Ice Skating, Hockey,  Gymnastics, Golf, Football, Foot Volley, Flag Football, Fitness, Field Hockey, Equestrian, Cycling, Crossfit, Cricket, Brazilian Jiu Jitsu, Basketball, Baseball, Barre, Badminton, Paddle, Australian Football, Table Tennis, Yoga, Wrestling, Wellness, Weightlifting, Volleyball, Track & Field, Tennis, Tai Chi, Swimming/Diving, Strength & Conditioning, Squash, Sprinting, Sports Performance, Softball)

Respond with JSON text using only variable names from the list above. Match all format/descriptions given in parenthesis. If any of the above variables are said to not apply or can not be identified or inferred based on the input text, use a null value in the JSON. Response should consist of only JSON and no additional text.
'''
ACCOUNT_TYPE_SYS_PROMPT = '''
You will be provided with a short description of a business. Your job is to read the description and identify the account type (what type of business/program it is) as one of the following:
* After School Program
* Parks & Rec Program
* Ice Arena
* Batting Cages Only
* Content Aggregator
* Mentorship Program
* Community
* Content Curator
* Coach-Athlete Marketplace
* 7v7 Team
* Recruiting Coach
* Academy
* Affiliate Network / Franchise
* Brand/League/Conglomerate
* Club Organization
* Camp, Combine, Showcase, Clinic
* Training Facility
* Content Producer
* Skills Trainer
* Prep School
* Pro League
* Club League
* Intl. Club Team
* Professional Team
* College
* High School Coach (Solo)
* High School
* Youth Team
Respond with the most specific of these account types that matches the business.
'''
WEB_SCRAPE_SUMMARIZER_SYS_PROMPT = '''
You will be provided with scraped text file from a sports/fitness related business's website. Your job is to read the text and write a summary containing any information the website has on the following questions. Elaborate as much as possible and include explanations and references to the scraped text. Do not format the summary as a list.
What is the business name?
What primary city, state is this business based in?
What language is the website written in?
What sport/topic does this business specialize in? 
Is there a specific element of this sport that they focus on?
What type of business/program is this? 
What product/service do they sell/provide?

If one of these questions does not have a clear answer or does not apply to the business, state so. Do not guess answers if they are not clear.
'''
WEB_SCRAPE_SUMMARIZER_ASSISTANT_ID = 'REDACTED_ASSISTANT_ID'

AREA_OF_FOCUS = ['Soccer', 'Skateboarding', 'Running', 'Rugby', 'Recruiting', 'Racquetball', 'Pickleball', 'Physical Therapy',  'Personal Training', 'Nutrition', 'Non-Athletic', 'Multi-Disciplinary', 'Movement', 'MMA', 'Mental Performance', 'Lacrosse', 'Judo', 'Ice Skating', 'Hockey',  'Gymnastics', 'Golf', 'Football', 'Foot Volley', 'Flag Football', 'Fitness', 'Field Hockey', 'Equestrian', 'Cycling', 'Crossfit', 'Cricket', 'Brazilian Jiu Jitsu', 'Basketball', 'Baseball', 'Barre', 'Badminton', 'Paddle', 'Australian Football', 'Table Tennis', 'Yoga', 'Wrestling', 'Wellness', 'Weightlifting', 'Volleyball', 'Track & Field', 'Tennis', 'Tai Chi', 'Swimming/Diving', 'Strength & Conditioning', 'Squash', 'Sprinting', 'Sports Performance', 'Softball']

client = OpenAI(api_key=OPENAI_API_KEY_COACHIQ)

def segment(scrape: str) -> dict:
    summary = summarize_scrape(scrape)
    while len(summary) < 300:
        logging.info('Summary likely failed: ' + summary)
        logging.info('Retrying summary...')
        summary = summarize_scrape(scrape)
    variables = identify_variables(summary)
    account_type = identify_account_type(summary)

    variables['accountType'] = account_type

    return variables

def summarize_scrape(scrape: str) -> str:
    global assistant_tokens_usage
    global assistant_prompt_count
    logging.info('Summarizing scrape with OpenAI...')
    with open('output.txt', 'w') as file:
        file.write(scrape)
        file.close()
    file = client.files.create(
        file=open("output.txt", "rb"),
        purpose="assistants"
    )

    thread = client.beta.threads.create(
        messages=[
            {
                'role': 'user',
                'content': 'Try this',
                'file_ids': [file.id]
            }
        ]
    )

    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=WEB_SCRAPE_SUMMARIZER_ASSISTANT_ID
    )

    # Wait for run to complete
    while run.status in ['queued', 'in_progress']:
        time.sleep(RELOAD_TIME_DELAY)
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id)
    try:
        assistant_tokens_usage += run.usage['total_tokens']
    except TypeError:
        try:
            assistant_tokens_usage += run.usage.total_tokens
        except AttributeError:
            logging.info('Assistant usage not found in run: ' + str(run))
    assistant_prompt_count += 1
    # Throw exception if run failed
    if run.status != 'completed':
        raise Exception('OpenAI Run failed with status: {}'.format(run.status))
    
    thread_messages = client.beta.threads.messages.list(thread.id)
    summary = thread_messages.data[0].content[0].text.value

    client.files.delete(file.id)
    client.beta.threads.delete(thread.id)
    os.remove('output.txt')

    logging.info('Summary completed:')
    logging.info(summary)

    return summary

def identify_variables(summary: str) -> dict:
    global chat_tokens_usage
    global chat_prompt_count
    logging.info('Identifying Variables with OpenAI...')
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {'role': 'system', 'content': VARIABLE_IDENTIFIER_SYS_PROMPT},
            {'role': 'user', 'content': summary}
        ]
    )
    output_text = completion.choices[0].message.content

    chat_tokens_usage += completion.usage.total_tokens
    chat_prompt_count += 1
    try:
        variables = json.loads(output_text)
        logging.info('Successfully Identified Variables: ')
        logging.info(str(variables))
        if (variables['areaOfFocus'] not in AREA_OF_FOCUS):
            logging.info('Area of Focus not recognized: ' + variables['areaOfFocus'])
            for area in AREA_OF_FOCUS:
                if area.lower() in variables['areaOfFocus'].lower():
                    variables['areaOfFocus'] = area
                    break
        return variables
    except json.JSONDecodeError:
        logging.info('Identify Variables OpenAI response did not match json: ' + output_text)
        return {
            'businessName': None,
            'language': None,
            'areaOfFocus': None,
            'location': None
        }

def identify_account_type(summary: str) -> str:
    global chat_tokens_usage
    global chat_prompt_count
    logging.info('Identifying Account Type with OpenAI...')
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {'role': 'system', 'content': ACCOUNT_TYPE_SYS_PROMPT},
            {'role': 'user', 'content': summary}
        ]
    )
    output_text = completion.choices[0].message.content
    chat_tokens_usage += completion.usage.total_tokens
    chat_prompt_count += 1
    logging.info('Successfully Identified Account Type as ' + output_text)
    return output_text

def select_pages(urls: list) -> list:
    global chat_tokens_usage
    global chat_prompt_count
    logging.info('Selecting Pages with OpenAI...')
    urls_text = ', '.join(urls)

    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {'role': 'system', 'content': PAGE_SELECTOR_SYS_PROMPT},
            {'role': 'user', 'content': urls_text}
        ]
    )


    output_text = completion.choices[0].message.content
    chat_tokens_usage += completion.usage.total_tokens
    chat_prompt_count += 1
    urls = [url for url in list(map(lambda url: url.strip(), output_text.split(','))) if url != '']

    logging.info('Selected Pages: ' + ', '.join(urls))
    return urls
