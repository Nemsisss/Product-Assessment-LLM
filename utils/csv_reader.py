# basic imports
import csv
import logging

# setting configs
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)

def read_csv(csv_file_path):
    logging.info('Reading CSV')
    rows = []
    with open(csv_file_path, newline="") as csvfile:
        reader = csv.reader(csvfile, delimiter="\n")
        # skip the header
        headers = next(reader)
        for row in reader:
            # remove the comma in the end of each row
            rows.append("".join(row)[:-1])
    csvfile.close()
    return rows

