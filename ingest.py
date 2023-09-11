# basic imports
import json
import os
import shutil
import logging
import chromadb

# langchain imports
from langchain.document_loaders import GitbookLoader
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings.openai import OpenAIEmbeddings

from dotenv import load_dotenv

# user defined imports
from utils.migrate import process_airtable

# setting configs
load_dotenv()
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)

def clear_chromadb(directory_path):
    # clear all files in the directory
    for root, dirs, files in os.walk(directory_path, topdown=False):
        logging.info("clearing chromadb...")
        for file_name in files:
            logging.info("clearing files...")
            file_path = os.path.join(root, file_name)
            os.remove(file_path)
        for dir_name in dirs:
            logging.info("clearing sqlite")
            dir_path = os.path.join(root, dir_name)
            shutil.rmtree(dir_path)


def get_or_create_chromadb(file_path, collection_name, documents, embedding_function):

    # the directory is empty, create a new chromadb
    if not os.listdir(file_path):
        logging.info("Creating the chroma vector DB...")
        db = Chroma.from_documents(
            documents=documents,
            embedding=embedding_function,
            collection_name=collection_name,
            persist_directory=file_path,
        )
    else:
        logging.info("DB already exists, creating an instance from it")
        # if the db already exists create a Chroma instance from a collection
        client = chromadb.PersistentClient(path=file_path)
        db = Chroma(
            client=client,
            collection_name=collection_name,
            embedding_function=embedding_function
        )
    return db


def create_docs_from_json(json_objects_list):

    # create document objects from json objects
    raw_documents = []
    for obj in json_objects_list:
        raw_documents.append(
            Document(page_content=obj["page_content"], metadata=obj["metadata"])
        )
    return raw_documents


def load_from_file(file_path):
    # load from file and convert to a list of json objects
    with open(file_path, "r") as file:
        json_object_string = file.read()
        json_object_list = json.loads(json_object_string)
    return json_object_list


def parse_manual(file_path):
    loader = GitbookLoader("https://manual.company_name.io/", load_all_paths=True)
    all_pages_data = loader.load()
    json_list = []
    for page in all_pages_data:
        json_object = {
            "page_content": page.page_content,
            "metadata": {
                "source": page.metadata["source"],
                "title": page.metadata["title"],
            },
        }
        json_list.append(json_object)

    with open(file_path, "w") as file:
        json.dump(json_list, file)


def ingest_docs():
  
    openai_api_key = os.environ["OPENAI_API_KEY"]
    manual_file_path = "ION-manual/manual.json"
    airtable_file_path = "Airtable_data/airtable.json"
    chromadb_path = "chroma_persist"
    collection_name = "ion-manual"
    # parse the manual only if the file is empty
    if not os.path.getsize(manual_file_path) or not os.path.getsize(airtable_file_path):
        # if the manual file is empty:
        if not os.path.getsize(manual_file_path): 
            parse_manual(manual_file_path)

        # if the airtable data file is empty:
        if not os.path.getsize(airtable_file_path):
            process_airtable(airtable_file_path)
        
        # clear chromadb to trigger get_or_create_chromadb() to create a new db based on newly parsed manual
        logging.info("Resetting ChromaDB")
        clear_chromadb(chromadb_path)
        logging.info("Cleared ChromaDB")

    # read the manual json file
    json_object_list = load_from_file(manual_file_path)
    # load the airtable json file
    airtable_json_list = load_from_file(airtable_file_path)
    # concatenate the two lists
    json_object_list.extend(airtable_json_list)
    
    # create a list of Document objects based on the saved json objects
    # for llama cpp version chunk_size=600, chunk_overlap=100 work best
    raw_documents = create_docs_from_json(json_object_list)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=100, separators=["\n\n", "\n", " ", ""]
    )
    # split the manual into chunks
    documents = text_splitter.split_documents(raw_documents)

    # for llama cpp version, use huggingface's embedding
    # embedding_function = HuggingFaceEmbeddings(
    #     model_name="sentence-transformers/all-MiniLM-L6-v2"
    # )

    # OpenAI's model works best with OpenAI's embedding
    embedding_function = OpenAIEmbeddings(openai_api_key=openai_api_key)

    # create the db only if it's not already saved to the disk
    # if you need to save updated data in the db and reset it, delete the two files inside the chroma_persist directory and run ingest.py
    db = get_or_create_chromadb(collection_name=collection_name, file_path=chromadb_path, documents=documents,
                                embedding_function=embedding_function)
    logging.info("Finished creating the chroma vector DB...")
    # # uncomment the following for testing purposes
    # docs = db.similarity_search(
    #     query="login to MES for accountability and tracking",
    #     k=10,
    #     embedding_function=embedding_function,
    # )
    # print(len(docs))
    # print(docs)
    # print("****** Added to Chromadb *******")

    return db
