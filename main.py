# basic imports
import datetime
import csv
import os.path
import time
import shutil
import logging


# streamlit imports
import streamlit as st
from streamlit_option_menu import option_menu
from st_on_hover_tabs import on_hover_tabs
from streamlit_elements import elements, mui, nivo


# user defined imports
from ingest import ingest_docs, parse_manual
from model import generate_response
from utils.csv_reader import read_csv
from utils.response_analysis import extract, calc_compliance, create_piechart
from utils.input_file_cleanup import input_apply_nlp

# setting configs
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)

#global variables
compliance_score=0
total_num_prompts = -1 #can't be 0 since progress is being divided by this number
rows = [] # rows read from the input file (stored as strings in an array)

# common file paths
response_folder_path = "responses"
history_file_path=os.path.join(response_folder_path, "history.csv")
manual_file_path = "ION-manual/manual.json"
airtable_file_path = "Airtable_data/airtable.json"



def append_to_csv(file_path, data):
    with open(file_path, mode='a', newline='') as f:
        writerr = csv.writer(f)
        writerr.writerow(data)
    f.close()

def is_history_empty(history_file_path):
    history_is_empty=True
    try:
        with open(history_file_path, 'r', newline='') as file:
            csv_reader = csv.reader(file)
            first_row = next(csv_reader)
            # Check if the first row contains strings (header)
            if len(first_row)!=0 and first_row[0].replace(" ","") != "":
                history_is_empty = False
    except (FileNotFoundError, StopIteration):
        history_is_empty=True

    file.close()
    return history_is_empty


def parse_manual_airtable():
    
    logging.info("Parsing manual and airtable")
    placeholder = st.empty()
    # clear manual and airtable so that when ingest_docs() is called, it will detect files are empty and will call parsers
    with open(manual_file_path, 'w') as file:
        pass
    file.close()
    with open(airtable_file_path, 'w') as file:
        pass
    ingest_docs()
    placeholder.empty()
    # clear flag once it's done
    st.session_state["parsing_manual_airtable"] = False
        

def delete_response_files():
    logging.info("Deleting response files")
    file_to_retain = "history.csv"
    for filename in os.listdir(response_folder_path):
        file_path = os.path.join(response_folder_path, filename)
        if filename != file_to_retain and filename != unique_file_name:
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)  # Delete subdirectories recursively
    logging.info('Deleting all response files!')


def start_over_fn():
    st.session_state.clear()
    logging.info('Starting over...')
    # enable upload 
    browser_placeholder.file_uploader('Upload your RFP CSV file to begin processing',
                                      accept_multiple_files=False, key="done", disabled=False,
                                      type=['csv'])

def clear_history():
    with open(history_file_path, 'w') as file:
        pass
    file.close()
    logging.info('Clearing history file.')

def start_process(db, response_file_path):
    short_responses=[]
    logging.info('Starting the RFP processor')
    for num, prompt in enumerate(rows):
        response_data = generate_response(prompt, db)

        # store unique sources only
        sources = set(doc.metadata['source'] for doc in response_data["source_documents"])

        # extract prompt, response and sources
        response = response_data["result"]
        query = response_data["query"]

        # store responses and prompts in session for persistence
        st.session_state["prompts"].append(query)
        st.session_state["responses"].append(response_data)
        left_col, right_col = st.columns([0.9,0.1])
        # display the results as they get processed
        with left_col:
            with st.expander(f"Doessoftware{query} ?"):
                st.write(response)
                st.write("Sources:")
                for source in sources:
                    st.write(source)
        with right_col:
            res = extract(response)
            short_responses.append(res)
            if res == "Yes":
                st.write(f":green[{extract(response)}]")
            elif res == "No":
                st.write(f":red[{extract(response)}]")
            else:
                st.write(f":orange[{extract(response)}]")
        
        # check if history file is empty, if so, add header
        history_is_empty = is_history_empty(history_file_path=history_file_path)

        # if history file is empty, write the header first
        if history_is_empty:
            with open(history_file_path, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['prompt', 'response', 'sources'])
            file.close()

        # store the responses in the csv file and also append them to the history file
        data=[f"Doessoftware{query} ?", response, sources]
        append_to_csv(response_file_path, data)
        append_to_csv(history_file_path, data)
        # update the progress bar
        percentage = ((num + 1) / total_num_prompts) * 100
        progress_bar.progress((num + 1) / total_num_prompts,
                              text=f"Progress: {'{:.2f}'.format(percentage)}%")
        
    # add time date/time to seperate each session
    data = ["-----------------",f"End of file ----- {str(datetime.datetime.now())}","-----------------"]
    append_to_csv(history_file_path, data)
        
    return short_responses


def load_processed_from_session():
    logging.info('Loading prompts, responses and sources from the streamlit\'s session_state')
    for resp_data in st.session_state["responses"]:
        srcs = set(doc.metadata['source'] for doc in resp_data["source_documents"])
        resp = resp_data["result"]
        q = resp_data["query"]
        left_col, right_col = st.columns([0.9,0.1])
        # display the results as they get processed
        with left_col:
            with st.expander(f"Doessoftware{q} ?"):
                st.write(resp)
                st.write("Sources:")
                for source in srcs:
                    st.write(source)
        with right_col:
            res = extract(resp)
            if res == "Yes":
                st.write(f":green[{extract(resp)}]")
            elif res == "No":
                st.write(f":red[{extract(resp)}]")
            else:
                st.write(f":orange[{extract(resp)}]")


if __name__ == "__main__":

    
    #this section contains thenentire code for UI and frontend logic for streamlit 
    
    logging.info('Starting program')
    file_path = "rfps/rfps.csv" #the path for input file
    # to preserve the prompts and the corresponding responses on button clicks
    if "prompts" not in st.session_state:
        st.session_state["prompts"] = []
    if "responses" not in st.session_state:
        st.session_state["responses"] = []
    if "doneProcessing" not in st.session_state:
        st.session_state["doneProcessing"] = False
    if "unique_file_name" not in st.session_state:
        st.session_state["unique_file_name"] = str(datetime.datetime.now()).replace(" ", "_")
    if "uploaded_file" not in st.session_state:
        st.session_state["uploaded_file"] = None
    if "stopped_midway" not in st.session_state:
        st.session_state["stopped_midway"] = False
    if "parsing_manual_airtable" not in st.session_state:
        st.session_state["parsing_manual_airtable"] = False
    if "response_results" not in st.session_state:
        st.session_state["response_results"]=[]


    # create filename for the response file (unique so that it does not overwrite an existing response file)
    unique_file_name = st.session_state["unique_file_name"] + ".csv"
    response_file_path = os.path.join(response_folder_path, unique_file_name)
    st.markdown('<style>' + open('style/style.css').read() + '</style>', unsafe_allow_html=True)
    st.title("<I🟢N> RFP Processor")

    # to add space between the header and rest of the content
    st.text("")
    st.text("")

    browser_placeholder = st.empty()
    warnings_placeholder = st.empty()


    with st.sidebar:
        tabs = on_hover_tabs(tabName=['Home', 'Download History', 'Clear History', 'Parse Data', 'Delete Responses'], 
                            iconName=['home','history', 'backspace', 'source', 'delete' ],  
                            styles = {'navtab': {'background-color':'#363636',
                                                  'color': '#ffffff',
                                                  'font-size': '16px',
                                                  'transition': '.3s',
                                                  'white-space': 'nowrap',
                                                  'text-transform': 'none'},                                       
                                                  'tabOptionsStyle': {':hover :hover': {'color': '#0bfc03',
                                                                      'cursor': 'pointer'}},
                                                'tabStyle' : {'list-style-type': 'none',
                                                     'margin-bottom': '40px',
                                                     'padding-left': '20px'}}
                                                                      ,default_choice=0)
    

    if tabs =='Home':
        # enable upload button
        if st.session_state["uploaded_file"] is None and not st.session_state["parsing_manual_airtable"]:
            uploaded_file = browser_placeholder.file_uploader('Upload your RFP CSV file to begin processing',
                                                            accept_multiple_files=False, key="enabled", disabled=False,
                                                            type=['csv'])
            # store the uploaded file inside session_state
            st.session_state["uploaded_file"] = uploaded_file
        placeholder = st.empty()
        start_over_placeholder = st.empty()
        percentage_placeholder = st.empty()
        piechart_placeholder = st.empty()

        # disable download before process completion
        download_button = placeholder.download_button(label='Download Responses', key='download_btn',
                                                        data=response_file_path, mime="text/csv",
                                                        disabled=True, file_name="processed_rfps.csv")
        # disable start_over button before process completion
        start_over = start_over_placeholder.button(label='Start Over', key='start_over', disabled=True)
        # ingest data and recreate the chromadb only when necessary
        # clearing the manual.json file will trigger manual parsing and recreation of chromadb
        db = ingest_docs()

        # if the file is uploaded and we are not parsing the manual or airtable
        if st.session_state["uploaded_file"] is not None and not st.session_state["parsing_manual_airtable"] :
            # read the input file (the uploaded_file) and write it to the file_path in order to later read from it
            with open(file_path, "wb") as file:
                # check that the file is still uploaded
                if st.session_state["uploaded_file"]:
                    file.write(st.session_state["uploaded_file"].getbuffer())
                file.close()
            try:
                rows = read_csv(file_path)
                total_num_prompts = len(rows)
                # with st.spinner("Processing the uploaded file..."):
                #     rows = input_apply_nlp(rows)
            except StopIteration:
                # the following except block applies to the case where llama2 is used as the LLM 
                # this does actually not quit the metal runner, program may crash if the user does not refresh the page and instead uploads a new file
                st.session_state.clear()
                warnings_placeholder = st.empty()
                with st.spinner("Stopping the program, this may take upto 60 seconds..."):
                    warnings_placeholder.warning(
                        "File was removed. Please wait for the program to stop. Refreshing the page before the program stops may cause it to crash.",
                        icon="⚠️")
                    # make the program sleep for 60 seconds until Metal stops execution
                    # this is mainly used if we are using a local LLM
                    time.sleep(60)
                    warnings_placeholder.empty()
                    st.stop()

            # if the data is already stored in the session, don't run the model
            if st.session_state["stopped_midway"] or len(st.session_state["prompts"]) != 0 and len(st.session_state["responses"]) != 0:
                # disable the upload button
                browser_placeholder.file_uploader('Upload your RFP CSV file to begin processing',
                                                accept_multiple_files=False, key="done", disabled=True,
                                                type=['csv'])
                load_processed_from_session()
                compliance_score = calc_compliance(st.session_state["response_results"] )
                create_piechart(compliance_score[1], compliance_score[2], percentage_placeholder,piechart_placeholder, compliance_score)

            else:
                # create a new csv file for responses with a unique filename
                with open(response_file_path, mode='w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(['prompt', 'response', 'sources'])
                file.close()
                with st.spinner("Generating the response document..."):

                    # disable the upload button
                    browser_placeholder.file_uploader('Upload your RFP CSV file to begin processing',
                                                    accept_multiple_files=False, disabled=True, type=['csv'],
                                                    key="disabled", )
                    warnings_placeholder.warning(
                        "Please wait for the program to complete its execution. If you click on menu options before the program completes, it will cause the program to terminate the process at the current prompt.",
                        icon="⚠️")
                    progress_bar = st.progress(0.0, text="Progress: 0%")
                    st.session_state["stopped_midway"] = True
                    response_results = start_process(db, response_file_path)
                    compliance_score = calc_compliance(response_results)
                    st.session_state["response_results"] = response_results
                    create_piechart(compliance_score[1], compliance_score[2], percentage_placeholder,piechart_placeholder,  compliance_score)


            file.close()
            # update states
            st.session_state["doneProcessing"] = True
            st.session_state["stopped_midway"] = False
            # clear the warnings
            warnings_placeholder.empty()
            # enable download button
            if st.session_state.doneProcessing :
                with open(response_file_path, "r") as file:
                    if st.session_state["uploaded_file"]:
                        placeholder.download_button(label='Download Responses', key='download_btn_2', data=file,
                                                    mime="text/csv", disabled=False, file_name="processed_rfps.csv")
                        
                    # enable start over button
                    if not st.session_state["parsing_manual_airtable"]:
                        start_over = start_over_placeholder.button(label='Start Over', key='start_over_2',
                                                                disabled=False, on_click=start_over_fn)
                file.close()

        # do not let user upload an RFP file for processing if manual and airtable parsing are not completed
        elif st.session_state["parsing_manual_airtable"]:
            st.warning( 'Please go back to "Parse Data" tab and click on "Start Parsing". Make sure to wait until parsing is done before switching back to "Home" tab.',
                        icon="⚠️")
            uploaded_file = browser_placeholder.file_uploader('Upload your RFP CSV file to begin processing',
                                                accept_multiple_files=False, key="enabled", disabled=True,
                                                type=['csv'])


    elif tabs == 'Download History':
        st.info('The history file contains all the processed RFPs in CSV format.', icon="ℹ️")
        dl_file_path = "responses/history.csv"
        with open(dl_file_path, "r") as file:
            st.download_button(label='Download History', key='download_hist', data=file,
                                                    mime="text/csv", disabled=False, file_name="rfps_history.csv")
        file.close()


    elif tabs == 'Clear History':
        st.warning( 'Clicking "Clear History" will delete all the RFPs saved to the history file.',
                        icon="⚠️")
        if st.button(label="Clear History", on_click= clear_history):
            st.success('Successfully cleared the history file!', icon="✅")

    elif tabs == 'Parse Data':

        # st.session_state["parsing_manual_airtable"]= True
        st.info('Clicking "Start Parsing" will overwrite the current manual/Airtable data with the latest version data.', icon="ℹ️")
        placeholder = st.empty()

        # allow user to click on parse_manual button only if the processing of prompts is done or if there's no files uploaded (the program was just started or reloaded)
        if (st.session_state["uploaded_file"] is None or st.session_state["doneProcessing"]) and placeholder.button(label="Start Parsing", disabled = False, key="btn4"):
            st.session_state["parsing_manual_airtable"]=True
            if st.session_state["parsing_manual_airtable"]:
                with st.spinner("Parsing the manual..."):
                    placeholder.warning( 'Please do not leave this page until the program is done parsing the manual. This may take at least 2 minutes.',
                        icon="⚠️")
                    parse_manual_airtable()
                    print("done parsing")
                    st.success('Successfully parsed Manual and Airtable data.', icon="✅")
            # reset placeholders 
            st.session_state["parsing_manual_airtable"]=False
            placeholder.empty()
            placeholder.button(label="Start Parsing", disabled = False, key="btn5")


        # if the user has uploaded a file, wait for the RFP processor to complete its task
        # the RFP processor uses the manual data, so it should not be interrupted while it processing the rfps and querying the manual data
        elif st.session_state["uploaded_file"] is not None and not st.session_state["doneProcessing"]:
            st.warning("Please wait for the program to complete processing the file. After it's complete, you can procceed.",icon="⚠️")
            placeholder.button(label="Start Parsing", disabled = True, key="btn2")
        # st.session_state["parsing_manual_airtable"]= False


    elif tabs == 'Delete Responses':
        st.write("It's good practice to occasionally delete the response files.")
        st.info( 'Clicking "Delete Response Files" will delete all the response files from the program .',
                       icon="ℹ️")
        if st.button(label = "Delete Response Files", on_click=delete_response_files):
            st.success('Successfully deleted all the response files!', icon="✅")
