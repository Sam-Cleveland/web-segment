import time
import json
import sys
import logging

from openai import OpenAI

OPENAI_API_KEY_COACHIQ='REDACTED_OPENAI_KEY'
THREAD_ID_2='thread_WQ92L2Vndm7msVyw6NonSo0O'
ASSISTANT_ID="REDACTED_ASSISTANT_ID"
RELOAD_TIME_DELAY=5

client = OpenAI(api_key=OPENAI_API_KEY_COACHIQ)

def segment_variables(jsonFile):
    file = client.files.create(
        file=jsonFile,
        purpose='assistants'
    )

    # thread_message = client.beta.threads.messages.create(
    #     thread_id=THREAD_ID_2,
    #     role='user',
    #     content='Do this file:',
    #     file_ids=[file.id]
    # )

    run = client.beta.threads.runs.create(
      thread_id=THREAD_ID_2,
      assistant_id=ASSISTANT_ID
    )

    # Wait for run to complete
    while run.status in ['queued', 'in_progress']:
        time.sleep(RELOAD_TIME_DELAY)
        run = client.beta.threads.runs.retrieve(
            thread_id=THREAD_ID_2,
            run_id=run.id)
    
    # Throw exception if run failed
    if run.status != 'completed':
        raise Exception('OpenAI Run failed with status: {}'.format(run.status))
    
    client.files.delete(file.id)

    thread_messages = client.beta.threads.messages.list(THREAD_ID_2)
    message = thread_messages.data[0].content[0].text.value
    try:
        message = message[message.find('{'):message.rfind('}')+1]
        segmentation_variables = json.loads()
        return segmentation_variables
    except:
        logging.info('OpenAI response did not match json: ' + message)
        return {
            'businessName': None,
            'language': None,
            'areaOfFocus': None,
            'accountType': None,
            'location': None
        }

if __name__ == '__main__':
    with open(sys.argv[1], 'r') as file:
        print(segment_variables(file.read()))