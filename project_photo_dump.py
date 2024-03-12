import requests
from alive_progress import alive_bar
import os
import argparse
import shutil

import warnings

warnings.simplefilter(action="ignore", category=FutureWarning)

# https://api.inaturalist.org/v1/observations?verifiable=true&order_by=observations.id&order=desc&page=1&spam=false&project_id=150883&field%3ADNA+Barcode+ITS=&locale=en-US&per_page=24

inat_api_observations_dna_seq_url = "https://api.inaturalist.org/v1/observations?verifiable=true&spam=false&project_id=150883"

photo_dir = "project_photos"
image_ref_file = "image_file_reference.txt"

DEFAULT_PAGE_SIZE = 200

# create parser
parser = argparse.ArgumentParser()

# add arguments to the parser
parser.add_argument("input_file", default="input.csv")

def get_all_inat_obs(client):
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
    print(f"{len(total_responses)} observations retrieved.")
    return total_responses

def main():
    client = requests.Session()
    inat_obs = get_all_inat_obs(client)
    file_list = []

    if not os.path.exists(photo_dir):
        print("Creating project photo dump dir")
        os.mkdir(photo_dir)
        print("Done!")

    with alive_bar(len(inat_obs)) as bar:
        for idx, result in enumerate(inat_obs):
            field_id = f"iNat{result['id']}"
            photos = result["observation_photos"]
            if len(photos) > 0:
                image = photos[0]
                image_url = image["photo"]["url"]
                image_url = image_url.replace("square", "medium")
                file_ext = image_url.split('.')[-1]
                filename = f"{result['id']}_medium.{file_ext}"

                # No need to download the file if it is already present
                if os.path.exists(os.path.join(photo_dir, filename)):
                    continue
                # else:
                #     print(field_id)
                with open(os.path.join(photo_dir, filename), "wb") as f:
                    f.write(requests.get(image_url).content)
                    file_list.append(filename)
            else:
                print(f"{field_id} has no photos attached to the iNaturalist observation. Skipping...")
            bar()
    # Compress image_dir
    print("Compressing image archive")
    shutil.make_archive(photo_dir, "zip", photo_dir)
    print("Done!")

    print(f"Writing image filenames to {image_ref_file}")
    with open(os.path.join(photo_dir, image_ref_file), 'w') as outfile:
        outfile.write('\n'.join(str(i) for i in file_list))
    print("Done!")
if __name__ == "__main__":
    main()
