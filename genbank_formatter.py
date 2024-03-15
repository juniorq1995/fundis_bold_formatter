import pandas as pd
import requests
import os
from requests.exceptions import JSONDecodeError
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

inat_api_observation_url = "https://api.inaturalist.org/v1/observations/"

oauth_creds = {
    "client_id": os.getenv("client_id"),
    "client_secret": os.getenv("client_secret"),
    "username": os.getenv("username"),
    "password": os.getenv("password"),
    "grant_type": "password",
}

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
LEGAL_FASTA_CHARS = set(
    ["A", "T", "C", "G", "N", "Y", "R", "M", "W", "S", "K", "H", "B", "V", "D"]
)


def get_client():
    oauth_response = requests.post(
        "https://www.inaturalist.org/oauth/token", oauth_creds
    )
    if oauth_response.status_code != 200:
        print(
            f"Error getting oauth token from iNat (HTTP {oauth_response.status_code}). Using client w/o token"
        )
        return requests
    bearer_token = "Bearer " + oauth_response.json()["access_token"]
    jwt_response = requests.get(
        "https://www.inaturalist.org/users/api_token",
        headers={"Authorization": bearer_token},
    )
    if jwt_response.status_code != 200:
        print(f"Error getting jwt token from iNat (HTTP {jwt_response.status_code})")
    client = requests.Session()
    client.headers["Authorization"] = jwt_response.json()["api_token"]
    return client


# User inputs
print("Initializing FUNDIS Sheet Crusher 5000...")
print("Welcome Validator")

inat_csv = input(
    "Enter name of csv file containing iNat ids (under column name 'numbers'): "
)
print("Spooling transmodulators")

# Load DataFrames
df_inat = pd.read_csv(inat_csv)
inat_ids = df_inat["numbers"].dropna().tolist()

print("Actuating quantum telemetry values")

# Get accession numbers from iNat IDs
lines = []
source_modifier_rows = []
client = get_client()
for inat in inat_ids:
    inat = int(inat)
    raw_response = client.get(inat_api_observation_url + str(inat))
    try:
        result = raw_response.json()["results"][0]
    except JSONDecodeError:
        print(f"Error returned from iNat {inat} (HTTP {raw_response.status_code})")
        continue
    fasta = ""
    accession_id = ""
    # organism = ""
    identifier = ""
    isolate = f"CA FUNDIS iNaturalist # {inat}"
    collection_date = datetime.strptime(result["observed_on"], "%Y-%m-%d").strftime(
        "%d-%b-%Y"
    )  # Should be in '31-Jan-2001' format. Read it in "2023-02-03" format
    fwd_primer = "ITS1F"
    rev_primer = "ITS4"
    ric = ""

    if result["obscured"]:
        latitude, longitude = result["private_location"].split(",")
    else:
        latitude, longitude = result["location"].split(",")

    country = ""
    # Get city, state, country, county from ex: http://maps.googleapis.com/maps/api/geocode/json?latlng=40.714224,-73.961452&sensor=false
    geo_url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={latitude},{longitude}&key={GOOGLE_MAPS_API_KEY}"
    geo_response = requests.get(geo_url)
    geo_json = geo_response.json()
    for geo_result in geo_json["results"]:
        for component in geo_result["address_components"]:
            if "country" in component["types"] and country == "":
                country = component["long_name"]
                break

    for field in result["ofvs"]:
        if field["field_id"] == 2330:
            fasta = field["value"].upper()
        elif field["field_id"] == 3347:
            accession_id = field["value"].upper()
            identifier = field["user"]["name"]
        elif field["field_id"] == 10675:
            organism = field["value"]
        elif field["field_id"] == 16718:
            ric = field["value"]

    note = f"California Fungal Diversity Survey www.fundis.org; iNaturalist.org #{inat}; RiC {ric}"

    source_modifier_rows.append(
        [
            accession_id,
            accession_id,
            organism,
            isolate,
            country,
            collection_date,
            identifier,
            fwd_primer,
            rev_primer,
            note,
        ]
    )

    if fasta and accession_id:
        filtered_fasta = "".join([i for i in fasta.upper() if i in LEGAL_FASTA_CHARS])
        lines.append(f">{accession_id}\n")
        lines.append(f"{filtered_fasta}\n")
        if len(fasta) > len(filtered_fasta):
            print(f"Filtered out {len(fasta)-len(filtered_fasta)} illegal chars")
    else:
        if fasta is None:
            print(f"No FASTA present for iNat {inat}, skipping")
        else:
            print(f"No Accession ID present for iNat {inat}, skipping")
        continue
source_modifier_df = pd.DataFrame(
    source_modifier_rows,
    columns=[
        "Sequence_ID",
        "specimen-voucher",
        "Organism",
        "Isolate",
        "Country",
        "Collection-date",
        "Collected_by",
        "Fwd_primer_name",
        "Rev_primer_name",
        "Note",
    ],
)
# Write updated sequences to a new FASTA file
with open("sequences.fasta", "w") as f:
    f.writelines(lines)

source_modifier_df.to_csv("source_modifiers.tsv", sep="\t", index=False)

print(
    "Mission complete, go get em tiger!. Check new_source_modifiers.tsv and new_sequences.fasta \
and rename them in an informative way. Move everything except for this program and the iNaturalist data to a new folder \
and name it in a way that tells you what you did and when you did it for future reference. Very important. Byeeeeeeeeeeeeee!"
)

# TODO: Add lat_lon field (https://www.ncbi.nlm.nih.gov/WebSub/html/help/genbank-source-table.html)
