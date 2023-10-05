import requests
import pandas as pd
import argparse
from math import isnan
from alive_progress import alive_bar
import os
from dotenv import load_dotenv
import time

import warnings

warnings.simplefilter(action="ignore", category=FutureWarning)

load_dotenv()

# https://api.inaturalist.org/v1/observations?verifiable=true&order_by=observations.id&order=desc&page=1&spam=false&project_id=150883&field%3ADNA+Barcode+ITS=&locale=en-US&per_page=24

inat_api_observation_url = "https://api.inaturalist.org/v1/observations/"

inat_api_observations_dna_seq_url = "https://api.inaturalist.org/v1/observations?verifiable=true&spam=false&project_id=150883&field%3ADNA+Barcode+ITS="

fasta_dir = "fasta_upload"
fasta_output = f"{fasta_dir}/fundis_fasta_upload.txt"

FASTA_HEADER = ">HAY-F" # >HAY-F-012345
DEFAULT_PAGE_SIZE = 200
DEFAULT_SLEEP = 15

oauth_creds = {
    "client_id": os.getenv("client_id"),
    "client_secret": os.getenv("client_secret"),
    "username": os.getenv("username"),
    "password": os.getenv("password"),
    "grant_type": "password",
}

# create parser
parser = argparse.ArgumentParser()

# add arguments to the parser
parser.add_argument("--input_file", required=False)

def get_all_dna_seq_inat_ids():
    inat_nums = set()
    # Get first page
    raw_response = requests.get(f"{inat_api_observations_dna_seq_url}&per_page=0&page=1")
    json_response = raw_response.json()

    # Get total number of observations with a dna sequence
    total_results = json_response['total_results']
    print(f"Retrieving {total_results} results")

    num_pages = int(total_results / DEFAULT_PAGE_SIZE) + (total_results % DEFAULT_PAGE_SIZE > 0)
    with alive_bar(total_results) as bar:
        for page_num in range(1, num_pages+1):
            raw_response = requests.get(f"{inat_api_observations_dna_seq_url}&per_page={DEFAULT_PAGE_SIZE}&page={page_num}")
            json_responses = raw_response.json()["results"]
            for response in json_responses:
                inat_num = int(response['id'])
                inat_nums.add(inat_num)
                bar()

    return inat_nums

def main():
    # parse the arguments
    args = parser.parse_args()

    # oauth_response = requests.post(
    #     "https://www.inaturalist.org/oauth/token", oauth_creds
    # )
    # if oauth_response.status_code != 200:
    #     print(
    #         f"Error getting oauth token from iNat (HTTP {oauth_response.status_code}). Full response is {oauth_response.content}"
    #     )
    #
    # # 2. get JWT token
    # bearer_token = "Bearer " + oauth_response.json()["access_token"]
    # jwt_response = requests.get(
    #     "https://www.inaturalist.org/users/api_token",
    #     headers={"Authorization": bearer_token},
    # )
    # if jwt_response.status_code != 200:
    #     print(f"Error getting jwt token from iNat (HTTP {jwt_response.status_code})")
    #
    # client = requests.Session()
    # client.headers["Authorization"] = jwt_response.json()["api_token"]

    if args.input_file:
        input_file = args.input_file
        print(f"Input file is {input_file}")
        input_df = pd.read_csv(input_file, usecols=["iNat number"])
        inat_nums = set(input_df["iNat number"].tolist())
    else:
        # Get all observations with a dna sequence
        inat_nums = get_all_dna_seq_inat_ids()

    if not os.path.exists(fasta_dir):
        print("Creating fasta dir")
        os.mkdir(fasta_dir)
        print("Done!")

    with alive_bar(len(inat_nums)) as bar:
        with open(fasta_output, "w") as f:
            for idx, inat_num in enumerate(inat_nums):
                if isnan(inat_num):
                    bar()
                    continue

                inat_num = int(inat_num)
                raw_response = requests.get(inat_api_observation_url + str(inat_num))
                if raw_response.status_code == 200:
                    result = raw_response.json()["results"][0]
                elif raw_response.status_code == 429:
                    print(f"Too many requests in a short span of time, sleeping for {DEFAULT_SLEEP} seconds before resuming tasks")
                    time.sleep(DEFAULT_SLEEP)
                    raw_response = requests.get(inat_api_observation_url + str(inat_num))
                    if raw_response != 200:
                        print(f"Still no valid response. Skipping iNat{inat_num}")
                        continue
                else:
                    print(f"Error: {raw_response.content}")
                    continue

                dna_sequence = ""
                for field in result["ofvs"]:
                    if field["datatype"] == "dna":
                        dna_sequence = field["value"].upper()
                        break

                if dna_sequence:
                    f.write(f"{FASTA_HEADER}-{idx}\n{dna_sequence}\n")
                else:
                    print(f"ERROR: DNA sequence missing for iNat{inat_num}!")
                bar()

if __name__ == "__main__":
    main()
