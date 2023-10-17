import requests
from alive_progress import alive_bar
import os

import warnings

warnings.simplefilter(action="ignore", category=FutureWarning)

# https://api.inaturalist.org/v1/observations?verifiable=true&order_by=observations.id&order=desc&page=1&spam=false&project_id=150883&field%3ADNA+Barcode+ITS=&locale=en-US&per_page=24

inat_api_observations_dna_seq_url = "https://api.inaturalist.org/v1/observations?verifiable=true&spam=false&project_id=150883&field%3ADNA+Barcode+ITS="

fasta_dir = "../fundis/fasta_upload"
fasta_output = f"{fasta_dir}/fundis_fasta_upload.txt"

DEFAULT_PAGE_SIZE = 200


def get_all_dna_seq_inat_obs(client):
    # Get first page
    raw_response = client.get(f"{inat_api_observations_dna_seq_url}&per_page=0&page=1")
    json_response = raw_response.json()

    # Get total number of observations with a dna sequence
    total_results = json_response['total_results']

    num_pages = int(total_results / DEFAULT_PAGE_SIZE) + (total_results % DEFAULT_PAGE_SIZE > 0)
    print(f"Retrieving {num_pages} pages of data")
    total_responses = []
    with alive_bar(num_pages) as bar:
        for page_num in range(1, num_pages+1):
            raw_response = client.get(f"{inat_api_observations_dna_seq_url}&per_page={DEFAULT_PAGE_SIZE}&page={page_num}")
            json_responses = raw_response.json()["results"]
            total_responses.extend(json_responses)
            bar()
    print(f"Len of total_responses is {len(total_responses)}")
    return total_responses

def main():
    client = requests.Session()
    dna_obs = get_all_dna_seq_inat_obs(client)

    if not os.path.exists(fasta_dir):
        print("Creating fasta dir")
        os.mkdir(fasta_dir)
        print("Done!")

    with alive_bar(len(dna_obs)) as bar:
        with open(fasta_output, "w") as f:
            for idx, result in enumerate(dna_obs):
                dna_sequence = ""
                sample_id = ""
                for field in result["ofvs"]:
                    if field["field_id"] == 3347:
                        sample_id = field["value"].upper()
                    elif field["datatype"] == "dna":
                        dna_sequence = field["value"].upper()

                    if sample_id and dna_sequence:
                        break

                if dna_sequence:
                    f.write(f">{sample_id}-{idx}\n{dna_sequence}\n")
                else:
                    print(f"ERROR: DNA sequence missing for {sample_id}!")
                bar()

if __name__ == "__main__":
    main()
