# basic imports
import sys
import os
import logging
import chromadb

# langchain imports
from langchain import PromptTemplate, LlamaCpp
from langchain.callbacks import StreamingStdOutCallbackHandler
from langchain.callbacks.manager import CallbackManager
from langchain.chat_models import ChatOpenAI
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
from langchain.llms import CTransformers
from langchain.chains import RetrievalQA
from langchain.embeddings.openai import OpenAIEmbeddings
# from langchain.embeddings.openai import OpenAIEmbeddings

# user defined imports
from ingest import ingest_docs
from dotenv import load_dotenv


# setting configs
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)
load_dotenv()
openai_api_key = os.environ["OPENAI_API_KEY"]
chromadb_path = "chroma_persist"

# better prompts ==  better responses
custom_prompt_template = """
    Use the following pieces of context to answer the question at the end.
    Answer with either yes or no and an explanation about whysoftwarecan or cannot do the task mentioned in the prompt.
    If you don't find enough information in the context, just say that you don't know the answer, do not make up an answer.
    {context}
    Question: Doessoftware{question} ?
    Helpful Answer:
"""


def set_custom_prompt():
    """
    Prompt template for QA retrieval  for each vector store
    """
    logging.info('Setting the custom prompt')
    prompt = PromptTemplate(
        template=custom_prompt_template, input_variables=["context", "question"]
    )
    return prompt


def load_llm():

    # callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
    # n_gpu_layers = 32 # Metal set to 1 is enough.
    # n_batch = 512 # Should be between 1 and n_ctx, consider the amount of RAM of your Apple Silicon Chip.

    # llm = LlamaCpp(
    #     model_path="llama-2-13b-chat.ggmlv3.q4_0.bin",
    #     temperature=0,
    #     n_ctx= 2048,
    #     n_gpu_layers=n_gpu_layers,
    #     n_batch=n_batch,
    #     f16_kv=True,  # MUST set to True, otherwise you will run into problem after a couple of calls
    #     callback_manager=callback_manager,
    #     verbose=True,
    # )


    logging.info('Loading LLM')
    llm=ChatOpenAI(verbose=True, temperature=0, openai_api_key=openai_api_key)
    return llm

def retrieval_qa_chain(llm, prompt, db):

    # k=7 ,the retriever will get the 7 most relevant pieces of data from the chromadb, however apple M2 16GB RAM often crashes with k=7, works fine with k=5 but less accuracy
    # for llama cpp version, set k =5

    #  for llama cpp version, use huggingface's embedding
    # embedding_function = HuggingFaceEmbeddings(
    #     model_name="sentence-transformers/all-MiniLM-L6-v2"
    # )
    logging.info('Creating the QA chain')

    # OpenAI's model works best with OpenAI's embedding
    embedding_function = OpenAIEmbeddings(openai_api_key=openai_api_key)
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=db.as_retriever(search_kwargs={"k": 6}, search_type="mmr", embedding=embedding_function),
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt},
    )
    return qa_chain


def qa_bot(db):
    logging.info("Calling retrieval QA chain")
    llm = load_llm()
    qa_prompt = set_custom_prompt()
    qa = retrieval_qa_chain(llm, qa_prompt, db)
    return qa


def generate_response(query, db):
    logging.info('Generating response')
    qa_result = qa_bot(db)
    response = qa_result({"query": query})
    return response
