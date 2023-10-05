import requests
import pandas as pd
import os
from dotenv import load_dotenv
from math import isnan
from alive_progress import alive_bar

import warnings

warnings.simplefilter(action="ignore", category=FutureWarning)

load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

inat_api_observation_url = "https://api.inaturalist.org/v1/observations/"

input_file = "input.csv"  # NOTE: File name will look like CA-FunDiS BOLD and HAY Accession Tracking - Plate01-44142.csv

myco_dir = "myco_upload"

DEFAULT_PHYLUM = "Basidiomycota"
institution_storing = "California State University East Bay"
license_contact = "sequencing@fundis.org"
license_institution = "FunDiS"
view_metadata = "Fruitbody"

oauth_creds = {
    "client_id": os.getenv("client_id"),
    "client_secret": os.getenv("client_secret"),
    "username": os.getenv("username"),
    "password": os.getenv("password"),
    "grant_type": "password",
}


def main():
    input_df = pd.read_csv(input_file, usecols=["iNat number"])
    inat_nums = set(input_df["iNat number"].tolist())

    oauth_response = requests.post(
        "https://www.inaturalist.org/oauth/token", oauth_creds
    )
    if oauth_response.status_code != 200:
        print(
            f"Error getting oauth token from iNat (HTTP {oauth_response.status_code})"
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

    if not os.path.exists(myco_dir):
        os.mkdir(myco_dir)

    myco_portal = []
    print("Retrieving data")
    with alive_bar(len(inat_nums)) as bar:
        for idx, inat_num in enumerate(inat_nums):
            if isnan(inat_num):
                bar()
                continue
            inat_num = int(inat_num)
            description = f"<a href='https://www.inaturalist.org/observations/{inat_num}' target='_blank' style='color: blue;'> Original observation #{inat_num} (iNaturalist)</a>"
            raw_response = client.get(inat_api_observation_url + str(inat_num))
            result = raw_response.json()["results"][0]

            event_date = result["observed_on"]
            scientific_name = result["species_guess"]  # Is this correct?

            # Catalog Number/Collection Code (HAY-F*****)
            catalog_number = ""
            recorded_by = ""
            notes = ""
            habitat = ""
            substrate = ""
            locality = ""  # combine field: general description with place_guess TODO

            taste = ""
            odor = ""
            uv_reaction = ""
            koh_reaction = ""

            associated_taxa = ""
            associated_second = ""
            associated_third = ""
            associated_fourth = ""

            for field in result["ofvs"]:
                if field["field_id"] == 3347:
                    catalog_number = field["value"].upper()
                    recorded_by = field["user"]["name"]
                elif field["field_id"] == 15976:
                    notes = field["value"]
                elif field["field_id"] == 1374:
                    if habitat:
                        habitat = f"{field['value']}. {habitat}"
                    else:
                        habitat = f"{field['value']}. "
                elif field["field_id"] == 15831:
                    if habitat:
                        habitat = habitat + field["value"]
                    else:
                        habitat = field["value"]
                elif field["field_id"] == 7582:
                    substrate = field["value"]
                elif field["field_id"] == 3330:
                    locality = f"{field['value']}. {result['place_guess']}"
                elif field["field_id"] == 15979:
                    taste = field["value"]
                elif field["field_id"] == 15977:
                    odor = field["value"]
                elif field["field_id"] == 15978:
                    uv_reaction = field["value"]
                elif field["field_id"] == 15976:
                    koh_reaction = field["value"]
                elif field["field_id"] == 15820:
                    associated_taxa = field["value"]
                elif field["field_id"] == 15821:
                    associated_second = field["value"]
                # elif field['field_id'] == 15820:
                #     associated_third = field['value']
                # elif field['field_id'] == 15820:
                #     associated_fourth = field['value'] # TODO: What are the field ID's for these?

            occurence_remarks = ""

            if notes:
                occurence_remarks += f"({notes})."
            if taste:
                occurence_remarks += f"Taste: {taste}."
            if odor:
                occurence_remarks += f"Odor: {odor}."
            if koh_reaction:
                occurence_remarks += f"KOH: {koh_reaction}."
            if uv_reaction:
                occurence_remarks += f"UV (365 nm): {uv_reaction}."

            if associated_second:
                associated_taxa = f"{associated_taxa}, {associated_second}"
            elif associated_third:
                associated_taxa = f"{associated_taxa}, {associated_third}"
            elif associated_fourth:
                associated_taxa = f"{associated_taxa}, {associated_fourth}"

            obscured = result["obscured"]
            if obscured:
                latitude, longitude = result["private_location"].split(",")
            else:
                latitude, longitude = result["location"].split(",")

            state = ""
            county = ""  # county
            # Get city, state, country, county from ex: http://maps.googleapis.com/maps/api/geocode/json?latlng=40.714224,-73.961452&sensor=false
            geo_url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={latitude},{longitude}&key={GOOGLE_MAPS_API_KEY}"
            geo_response = requests.get(geo_url)
            geo_json = geo_response.json()
            for geo_result in geo_json["results"]:
                if state and county:
                    break
                for component in geo_result["address_components"]:
                    if (
                        "administrative_area_level_1" in component["types"]
                        and state == ""
                    ):
                        state = component["long_name"]
                    elif (
                        "administrative_area_level_2" in component["types"]
                        and county == ""
                    ):
                        county = component["long_name"]  # county
            myco_portal.append(
                [
                    event_date,
                    recorded_by,
                    description,
                    locality,
                    latitude,
                    longitude,
                    county,
                    state,
                    scientific_name,
                    catalog_number,
                    habitat,
                    substrate,
                    occurence_remarks,
                    associated_taxa,
                ]
            )
            bar()
    myco_portal_df = pd.DataFrame(
        myco_portal,
        columns=[
            "eventDate",
            "recordedBy",
            "description",
            "locality",
            "decimalLatitude",
            "decimalLongitude",
            "county",
            "stateProvince",
            "scientificName",
            "catalogNumber",
            "habitat",
            "substrate",
            "occurenceRemarks",
            "associatedTaxa",
        ],
    )

    print(f"Writing Myco portal data to MycoUpload.xlsx")
    myco_portal_df.to_excel(
        os.path.join(myco_dir, "MycoUpload.xlsx"), index=False, engine="xlsxwriter"
    )


if __name__ == "__main__":
    main()
