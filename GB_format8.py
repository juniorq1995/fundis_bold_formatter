import pandas as pd
import requests
import os
from requests.exceptions import JSONDecodeError

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

inat_csv = input("Enter name of csv file containing iNat ids (under column name 'numbers'): ")
print("Spooling transmodulators")

# Load DataFrames
df_inat = pd.read_csv(inat_csv)
inat_ids = df_inat['numbers'].dropna().tolist()

print("Actuating quantum telemetry values")

# Get accession numbers from iNat IDs
lines = []
client = get_client()
for inat in inat_ids:
	inat = int(inat)
	raw_response = client.get(inat_api_observation_url + str(inat))
	try:
		result = raw_response.json()["results"][0]
	except JSONDecodeError:
		print(
			f"Error returned from iNat {inat} (HTTP {raw_response.status_code})"
		)
	fasta = None
	accession_id = None

	for field in result["ofvs"]:
		if field["field_id"] == 2330:
			fasta = field["value"].upper()
		elif field["field_id"] == 3347:
			accession_id = field["value"].upper()
	if fasta and accession_id:
		lines.append(f">{accession_id}\n")
		lines.append(f"{fasta}\n")
	else:
		if fasta is None:
			print(f"No FASTA present for iNat {inat}")
		else:
			print(f"No Accession ID present for iNat {inat}")
		continue

# Write updated sequences to a new FASTA file
with open('new_sequences.fasta', 'w') as f:
	f.writelines(lines)

print("Mission complete, go get em tiger!. Check new_source_modifiers.tsv and new_sequences.fasta \
and rename them in an informative way. Move everything except for this program and the iNaturalist data to a new folder \
and name it in a way that tells you what you did and when you did it for future reference. Very important. Byeeeeeeeeeeeeee!")

# TODO: Add coordionates and source modifier file tsv (https://www.ncbi.nlm.nih.gov/WebSub/html/help/genbank-source-table.html)
