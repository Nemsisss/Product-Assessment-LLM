# basic imports
import requests
import json
import os
import spacy
import textacy
import logging

# user defined imports
from dotenv import load_dotenv

# setting configs
load_dotenv()
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)

def apply_nlp(clean_records):
    logging.info('Applying NLP to Airtable data')
    toRet = []

    for record in clean_records:
        nlp = spacy.load("en_core_web_sm")

        # extract the requirment field
        requirement = record['fields'].get('Requirement')

        # we only need maximum upto 3 words
        first_3_words = requirement.split(" ")[0:3]
        
        # join the list of the 3 words as a string
        doc= nlp(" ".join(first_3_words))

        # look for verbs, nouns, adjs in those 3 words
        verbs = [token.text for token in doc if token.pos_ == "VERB"]
        nouns = [token.text for token in doc if token.pos_ == "NOUN"] 
        adjs = [token.text for token in doc if token.pos_ == "ADJ"]

        # we only need the first of each occurance
        adj, verb,noun = '','',''
        if len(verbs):
            verb=verbs[0]
        if len(adjs):
            adj=adjs[0]
        if len(nouns):
            noun=nouns[0]
            
        
        processed=''
        # compare the first word of each requirement with the verb, noun and adj extracted above
        # based on comparison results, process each requirement accordingly
        if first_3_words[0] == verb and record['fields'].get('Opt In')is not None:
            processed = f"ION does {record['fields']['Requirement']}"

        elif first_3_words[0] == verb :
            processed = f"ION does not {record['fields']['Requirement']}"

        elif first_3_words[0] == noun and record['fields'].get('Opt In')is not None:
            processed = f"ION provides {record['fields']['Requirement']}"

        elif first_3_words[0] == noun:
            processed = f"ION does not provide {record['fields']['Requirement']}"

        elif first_3_words[0] == adj and record['fields'].get('Opt In')is not None:
            processed = f"ION has {record['fields']['Requirement']}"    
        elif first_3_words[0] == adj:
            processed = f"ION does not have {record['fields']['Requirement']}"
        else:   
            if record['fields'].get('Opt In')is not None:
                processed =  f"softwaredoes: {record['fields']['Requirement']}"
            else:
                processed =  f"softwaredoes not: {record['fields']['Requirement']}"
        toRet.append(processed)

    return toRet


    

def remove_empty_records(records):
    logging.info('Removing empty records from Airtable data')
    records=records
    for record in records:
        # print(record['fields'])
        if record['fields'].get('Requirement')is None:
            records.remove(record)
    return records


def send_request(end_point, offset):
    logging.info('Sending request to Airtable API')
    print(f'Fetching records offset: {offset} at: {end_point}')
    token = os.environ['AT_TOKEN']
    headers = {
        'Authorization': f"Bearer {token}",
        'Content-Type': 'application/json',
    }
    if offset is not None:
        end_point += f'&offset={offset}'
    res = requests.get(end_point, headers=headers)
    print(res)
    return res.json()

def get_all_records(endpoint):
    logging.info("Getting all Airtable records")
    records = []
    contains_more_items = True
    offset = None
    while contains_more_items:
        data = send_request(endpoint, offset)
        # Airtable returns an offset with the value of the record id
        offset = data.get('offset')
        if offset is None:
            contains_more_items = False
        records.extend(data['records'])
        print(f'Length of records: {len(records)}')

    return records

def parse_airtable(airtable_data, file_path):
    logging.info("Converting airtable records to JSON objects and saving them to airtable_file_path")
    json_list = []
    for row in airtable_data:
        json_object = {
            "page_content": row,
            "metadata": {
                "source": "",
                "title": "Airtable data",
            },
        }
        json_list.append(json_object)

    with open(file_path, "w") as file:
        json.dump(json_list, file)


def process_airtable(airtable_file_path):
    logging.info("Airtable parsing started")
    # fetch all data from Requirement Airtable
    records = get_all_records('')
    
    # remove empty rows
    clean_records= remove_empty_records(records)
    
    # apply nlp to requirements
    results=apply_nlp(clean_records)
    
    # save airtable data to airtable_file_path
    parse_airtable(results, airtable_file_path)
