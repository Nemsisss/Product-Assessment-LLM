import logging
import spacy
import textacy

from utils.csv_reader import read_csv

def input_apply_nlp(rfps_arr):
    logging.info('Applying NLP to input file data')
    toRet = []
    processed=''

    for record in rfps_arr:
        nlp = spacy.load("en_core_web_sm")

        # we only need maximum upto 3 words
        first_word = record.split(" ")[0]
        rest = record.split(" ")[1:]
        rest= " ".join(rest)

        # join the list of the 3 words as a string
        doc= nlp("".join(first_word))

        # check if the first word is a noun, verb or adj
        verb = [token.text for token in doc if token.pos_ == "VERB"]
        noun = [token.text for token in doc if token.pos_ == "NOUN"] 
        adj = [token.text for token in doc if token.pos_ == "ADJ"]

        # if the input rfp starts with a verb
        if len(verb) and first_word == verb[0] :
            print(verb, first_word)
            processed = f"have ability to {first_word.lower()} {rest}"

        # if the input rfp starts with either a noun or an adjective
        elif (len(noun) and first_word == noun[0]) or (len(adj) and first_word == adj[0]):
            processed = f"have {first_word.lower()} {rest}"

        # if the input rfp starts with something not recognized by spaCy and textacy libraries
        else:
            processed = f"provide {first_word.lower()}  {rest}"

        toRet.append(processed)

    return toRet
