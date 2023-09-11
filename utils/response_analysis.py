# basic imports
import logging

# streamlit imports
from streamlit_elements import elements, mui, nivo
import streamlit as st

# setting configs
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)

def extract(response):
    logging.info('Extracting "Yes"s and "No"s ')
    toRet=''
    if len(response) <=3:
        #if the response is "No."
        if (response[:2]).lower() == 'no':
            toRet='No'
        # if the response is "Yes"
        elif response.lower() == 'yes':
            toRet ='Yes'
    elif len(response)<=4:
        # if the response is "Yes."
        if (response[:3]).lower() == 'yes':
            toRet = 'Yes'
    else:
        # if response is longer than 3 characters only check the first 2 and first 3 characters
        if (response[:2]).lower() == 'no':
            toRet='No'
        elif (response[:3]).lower() == 'yes':
            toRet = 'Yes'
        else:
            toRet = 'N/A'

    return toRet

def calc_compliance(res_arr):

    logging.info("Calculating compliance score")
    # total count includes "yes"s and "no"s only, it does not include "N/A" values
    total_count=0
    yes_count=0
    no_count=0
    percentage=0
    for res in res_arr:

        if res == 'No':
            total_count+=1
            no_count+=1
        
        elif res == 'Yes':
            total_count+=1
            yes_count+=1

    if total_count != 0:
        percentage = yes_count/total_count*100
    return(percentage, yes_count, no_count)



def create_piechart(yes, no, percentage_placeholder,piechart_placeholder,compliance_score):

    logging.info("Creating the pie chart")
    color=''
    if compliance_score[0] < 50:
        color = 'red'
    elif compliance_score[0]>=50 and compliance_score[0]<70:
        color = 'orange'
    else:
        color = 'green' 
    with piechart_placeholder :
        percentage_placeholder.subheader(f"Compliance Score: :{color}[ {'{:.2f}'.format(compliance_score[0])}%] ")
        with elements("nivo_charts"):
            data = [{
            "id": "yes",
            "label": "Complient",
            "value": yes,
        }, {
            "id": "no",
            "label": "Non-Complient",
            "value": no,
        }]
            with mui.Box(sx={"height": 400}):
                nivo.Pie(
                    data=data,
                    keys=[ "yes", "no"],
                    valueFormat=">-.2f",
                    margin={ "top": 70, "right": 80, "bottom": 40, "left": 80 },
                    gridLabelOffset=36,
                    dotSize=10,
                    colors={ 'scheme': 'accent' },
                    dotColor={ "theme": "background" },
                    dotBorderWidth=2,
                    motionConfig="wobbly",
                    legends=[
                        {
                            "anchor": "top-right",
                            "direction": "column",
                            "translateX": -50,
                            "translateY": -40,
                            "itemWidth": 80,
                            "itemHeight": 20,
                            "itemTextColor": "#ffffff",
                            "symbolSize": 12,
                            "symbolShape": "circle",
                            "effects": [
                                {
                                    "on": "hover",
                                    "style": {
                                        "itemTextColor": "#0bfc03"
                                    }
                                }
                            ]
                        }
                    ],
                    theme={
                        "background": "#191919",
                        "textColor": "#FFFFFF",
                        "tooltip": {
                            "container": {
                                "background": "#000000",
                                "color": "#FFFFFF",
                                "font-family": "sans-serif",
                                "font-size": "12px"
                            }
                        }
                    }
                )