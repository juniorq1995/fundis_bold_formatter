import requests
import pandas as pd
from datetime import datetime
import shutil
import os
from dotenv import load_dotenv
from math import isnan
from alive_progress import alive_bar
import argparse

import warnings

warnings.simplefilter(action="ignore", category=FutureWarning)

load_dotenv()

# create parser
parser = argparse.ArgumentParser()

# add arguments to the parser
parser.add_argument("input_file")

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

observations_url = "https://api.inaturalist.org/v1/observations?verifiable=true&page={}&projects%5B%5D=ca-fundis&per_page={}"

inat_api_observation_url = "https://api.inaturalist.org/v1/observations/"

DEFAULT_INPUT = "input.csv"  # NOTE: File name will look like CA-FunDiS BOLD and HAY Accession Tracking - Plate01-44142.csv

batch_size = 100

DEFAULT_PHYLUM = "Basidiomycota"
institution_storing = "California State University East Bay"
license_contact = "sequencing@fundis.org"
license_institution = "FunDiS"
view_metadata = "Fruitbody"

image_dir = "image_upload"
bold_dir = "bold_upload"

oauth_creds = {
    "client_id": os.getenv("client_id"),
    "client_secret": os.getenv("client_secret"),
    "username": os.getenv("username"),
    "password": os.getenv("password"),
    "grant_type": "password",
}


def main():
    # parse the arguments
    args = parser.parse_args()

    if args.input_file:
        input_file = args.input_file
    else:
        input_file = DEFAULT_INPUT

    print(f"Input file is {input_file}")
    input_df = pd.read_csv(input_file, usecols=["iNat number"])
    inat_nums = set(input_df["iNat number"].tolist())

    oauth_response = requests.post(
        "https://www.inaturalist.org/oauth/token", oauth_creds
    )
    if oauth_response.status_code != 200:
        print(
            f"Error getting oauth token from iNat (HTTP {oauth_response.status_code}). Full response is {oauth_response.content}"
        )

    # 2. get JWT token
    bearer_token = "Bearer " + oauth_response.json()["access_token"]
    jwt_response = requests.get(
        "https://www.inaturalist.org/users/api_token",
        headers={"Authorization": bearer_token},
    )
    if jwt_response.status_code != 200:
        print(f"Error getting jwt token from iNat (HTTP {jwt_response.status_code})")
    client = requests.Session()
    client.headers["Authorization"] = jwt_response.json()["api_token"]

    voucher_info_rows = []
    taxonomy_rows = []
    specimen_details_rows = []
    collection_data_rows = []
    image_metadata = []

    if not os.path.exists(image_dir):
        os.mkdir(image_dir)

    if not os.path.exists(bold_dir):
        os.mkdir(bold_dir)
    print("Retrieving data")
    with alive_bar(len(inat_nums)) as bar:
        for idx, inat_num in enumerate(inat_nums):
            if isnan(inat_num):
                bar()
                continue
            inat_num = int(inat_num)
            field_id = f"iNat{inat_num}"
            raw_response = client.get(inat_api_observation_url + str(inat_num))
            result = raw_response.json()["results"][0]

            coordinate_accuracy = result["positional_accuracy"]
            # Sample ID/Collection Code (HAY-F*****)
            sample_id = ""
            identifier = "" # Accession Number
            notes = ""
            habitat_description = ""
            for field in result["ofvs"]:
                if field["field_id"] == 3347:
                    sample_id = field["value"].upper()
                    identifier = field["user"]["name"]
                elif field["field_id"] == 15976:
                    notes = field["value"]
                elif field["field_id"] == 15831:
                    habitat_description = field["value"]
            # Voucher Info:
            # Sample ID, Field ID, Museum ID, Collection Code, Institution Storing
            voucher_info_rows.append(
                [sample_id, field_id, "", sample_id, institution_storing]
            )
            # Taxonomy:
            # Sample ID, Phylum, Class, Order, Family, Subfamily, Tribe, Genus, Species, Subspecies, Identifier, Identifier_Email, Identification_Method, Taxonomy_Notes
            phylum = (
                taxon_class
            ) = (
                order
            ) = (
                family
            ) = (
                subfamily
            ) = (
                tribe
            ) = (
                genus
            ) = (
                species
            ) = (
                subspecies
            ) = identifier_email = identification_method = taxonomy_notes = ""
            for field in result["identifications"][0]["taxon"]["ancestors"]:
                if field["rank"] == "phylum":
                    phylum = field["name"]
                elif field["rank"] == "class":
                    taxon_class = field["name"]
                elif field["rank"] == "order":
                    order = field["name"]
                elif field["rank"] == "family":
                    family = field["name"]
                elif field["rank"] == "subfamily":
                    subfamily = field["name"]
                elif field["rank"] == "tribe":
                    tribe = field["name"]
                elif field["rank"] == "genus":
                    genus = field["name"]
                elif field["rank"] == "species":
                    species = field["name"]
                elif field["rank"] == "subspecies":
                    subspecies = field["name"]
            if phylum == "":
                phylum = DEFAULT_PHYLUM
            taxonomy_rows.append(
                [
                    sample_id,
                    phylum,
                    taxon_class,
                    order,
                    family,
                    subfamily,
                    tribe,
                    genus,
                    species,
                    subspecies,
                    identifier,
                    identifier_email,
                    identification_method,
                    taxonomy_notes,
                ]
            )

            # Specimen Details:
            # Sample ID, Sex, Reproduction, Life Stage, Extra Info (iNat-ID), Notes, Voucher Status, Tissue Descriptor, Associated Taxa, Associated Specimens
            # external_url = f"inaturalist.org/observations/{inat_num}"
            specimen_details_rows.append(
                [sample_id, "", "", "", field_id, notes, "", "", "", ""]
            )

            # Collection Data:
            # Sample ID, Collectors, Collection Date, Country/Ocean, State/Province, Region, Sector, Exact Site, Lat, Lon, Elev, Depth, Elevation Precision, Depth Precision, GPS Source, Coordinate Accuracy, Event Time, Collection Date Accuracy, Habitat, Sampling Protocol, Collection Notes, Site Code, Collection Event ID
            observed_on = result["observed_on"]
            obscured = result["obscured"]
            if obscured:
                latitude, longitude = result["private_location"].split(",")
            else:
                latitude, longitude = result["location"].split(",")

            state = ""
            country = ""
            region = ""  # county
            sector = ""
            exact_site = ""
            # Get city, state, country, county from ex: http://maps.googleapis.com/maps/api/geocode/json?latlng=40.714224,-73.961452&sensor=false
            geo_url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={latitude},{longitude}&key={GOOGLE_MAPS_API_KEY}"
            geo_response = requests.get(geo_url)
            geo_json = geo_response.json()
            for geo_result in geo_json["results"]:
                if state and country and region:
                    break
                for component in geo_result["address_components"]:
                    if "country" in component["types"] and country == "":
                        country = component["long_name"]
                    elif (
                        "administrative_area_level_1" in component["types"]
                        and state == ""
                    ):
                        state = component["long_name"]
                    elif (
                        "administrative_area_level_2" in component["types"]
                        and region == ""
                    ):
                        region = component["long_name"]  # county

            elev_url = f"https://maps.googleapis.com/maps/api/elevation/json?locations={latitude}%2C{longitude}&key={GOOGLE_MAPS_API_KEY}"
            elev_response = requests.get(elev_url)
            elev_json = elev_response.json()["results"][0]
            elevation = elev_json["elevation"]
            elevation_precision = elev_json["resolution"]

            depth = ""
            depth_precision = ""
            gps_source = ""
            event_time = ""
            collection_date_accuracy = ""
            habitat = ""
            sampling_protocol = ""
            site_code = ""
            collection_event_id = ""

            collection_data_rows.append(
                [
                    sample_id,
                    identifier,
                    observed_on,
                    country,
                    state,
                    region,
                    sector,
                    exact_site,
                    latitude,
                    longitude,
                    obscured,
                    elevation,
                    depth,
                    elevation_precision,
                    depth_precision,
                    gps_source,
                    coordinate_accuracy,
                    event_time,
                    collection_date_accuracy,
                    habitat,
                    sampling_protocol,
                    habitat_description,
                    site_code,
                    collection_event_id,
                ]
            )
            # Image:
            # Image File, Original Specimen, View Metadata, Caption	Measurement, Measurement Type, Sample Id, Process Id, License Holder, License, License Year, License Institution, License Contact, Photographer
            # 03inat987654.jpg, yes, fruiting body,,,,HAY-F-012345,, harte singer, CC-BY-NC, 2023, FunDiS, sequencing@fundis.org, harte singer
            # For image url swap out the "medium" in medium.jpg for large so it becomes "large.jpg"
            license_year = datetime.strptime(observed_on, "%Y-%m-%d").year

            # Retrieve all image urls:
            photos = result["observation_photos"]
            if len(photos) > 10:
                photos = photos[:10]
            for image in photos:
                image_url = image["photo"]["url"]
                image_url = image_url.replace("square", "medium")
                position = image["position"]
                filename = f"{field_id}_{position}.jpg"

                # No need to download the file if it is already present
                if os.path.exists(os.path.join(image_dir, filename)):
                    continue
                with open(os.path.join(image_dir, filename), "wb") as f:
                    f.write(requests.get(image_url).content)

                license_code = image["photo"]["license_code"]
                license_holder = (
                    image["photo"]["attribution"].split(",")[0].split("(c) ")[1]
                )  # assume also photographer
                image_metadata.append(
                    [
                        filename,
                        "yes",
                        view_metadata,
                        "",  # caption
                        "",  # measurement
                        "",  # measurement type
                        sample_id,
                        "",  # process id
                        license_holder,
                        license_code,
                        license_year,
                        license_institution,
                        license_contact,
                        identifier,
                    ]
                )
            bar()

    # Convert lists to pandas and write to excel spreadsheets
    voucher_info_df = pd.DataFrame(
        voucher_info_rows,
        columns=[
            "Sample ID",
            "Field ID",
            "Museum ID",
            "Collection Code",
            "Institution Storing",
        ],
    )
    taxonomy_df = pd.DataFrame(
        taxonomy_rows,
        columns=[
            "Sample ID",
            "Phylum",
            "Class",
            "Order",
            "Family",
            "Subfamily",
            "Tribe",
            "Genus",
            "Species",
            "Subspecies",
            "Identifier",
            "Identifier Email",
            "Identification Method",
            "Taxonomy Notes",
        ],
    )
    specimen_details_df = pd.DataFrame(
        specimen_details_rows,
        columns=[
            "Sample ID",
            "Sex",
            "Reproduction",
            "Life Stage",
            "Extra Info",
            "Notes",
            "Voucher Status",
            "Tissue Descriptor",
            # 'External URLs',
            "Associated Taxa",
            "Associated Specimens",
        ],
    )
    collection_data_df = pd.DataFrame(
        collection_data_rows,
        columns=[
            "Sample ID",
            "Collectors",
            "Collection Date",
            "Country/Ocean",
            "State/Province",
            "Region",
            "Sector",
            "Exact Site",
            "Lat",
            "Lon",
            "Obscured",
            "Elev",
            "Depth",
            "Elevation Precision",
            "Depth Precision",
            "GPS Source",
            "Coordinate Accuracy",
            "Event Time",
            "Collection Date Accuracy",
            "Habitat",
            "Sampling Protocol",
            "Collection Notes",
            "Site Code",
            "Collection Event ID",
        ],
    )
    image_metadata_df = pd.DataFrame(
        image_metadata,
        columns=[
            "Image File",
            "Original Specimen",
            "View Metadata",
            "Caption",
            "Measurement",
            "Measurement Type",
            "Sample Id",
            "Process Id",
            "License Holder",
            "License",
            "License Year",
            "License Institution",
            "License Contact",
            "Photographer",
        ],
    )
    print(f"Created dataframes for upload data")

    print("Writing BOLD data to spreadsheet")
    with pd.ExcelWriter(os.path.join(bold_dir, "bold_upload.xls")) as writer:
        # use to_excel function and specify the sheet_name and index
        # to store the dataframe in specified sheet
        voucher_info_df.to_excel(
            writer, sheet_name="Voucher Info", index=False, engine="xlsxwriter"
        )
        taxonomy_df.to_excel(
            writer, sheet_name="Taxonomy", index=False, engine="xlsxwriter"
        )
        specimen_details_df.to_excel(
            writer, sheet_name="Specimen Details", index=False, engine="xlsxwriter"
        )
        collection_data_df.to_excel(
            writer, sheet_name="Collection Data", index=False, engine="xlsxwriter"
        )

    print(f"Writing image metadata to spreadsheet")
    image_metadata_df.to_excel(
        os.path.join(image_dir, "ImageData.xls"), index=False, engine="xlsxwriter"
    )

    # Compress image_dir
    print("Compressing image archive")
    shutil.make_archive(image_dir, "zip", image_dir)
    print("Done!")


if __name__ == "__main__":
    main()
