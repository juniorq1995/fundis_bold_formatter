import pandas as pd
import requests

inat_api_observation_url = "https://api.inaturalist.org/v1/observations/"

# User inputs
print("Initializing FUNDIS Sheet Crusher 5000...")
print("Welcome Validator")

inat_csv = input("Enter name of csv file containing iNat ids (under column name 'numbers'): ")
print("Spooling transmodulators")

# Load DataFrames
df_inat = pd.read_csv(inat_csv)
inat_ids = df_inat['numbers'].tolist()

print("Actuating quantum telemetry values")

# Get accession numbers from iNat IDs
lines = []
for inat in inat_ids:
	raw_response = requests.get(inat_api_observation_url + str(inat))
	result = raw_response.json()["results"][0]
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
