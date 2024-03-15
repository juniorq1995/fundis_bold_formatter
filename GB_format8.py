import pandas as pd

# User inputs
print("Initializing FUNDIS Sheet Crusher 5000...")
print("Welcome Validator")
source_modifiers_tsv = input("Enter name of file from MycoMap (i.e. something.tsv): ")
inat_csv = input("Enter name of iNat data (i.e. iNat9.21.csv): ")
fasta_file = input("Enter the FASTA file (i.e. sequences.fasta): ")
print("Spooling transmodulators")

# Load DataFrames
df_source_modifiers = pd.read_csv(source_modifiers_tsv, sep="\t")
df_inat = pd.read_csv(inat_csv)

# Extract iNat_ID from the 'Isolate' column
df_source_modifiers["iNat_ID"] = df_source_modifiers["Isolate"].str.split("#").str[1]
df_source_modifiers["iNat_ID"] = df_source_modifiers["iNat_ID"].astype(int)
print("Actuating quantum telemetry values")

# Merge DataFrames based on iNat_ID
df_source_modifiers = pd.merge(
    df_source_modifiers, df_inat, left_on="iNat_ID", right_on="id", how="left"
)

# Create a new column "specimen-voucher" and replace 'Sequence_ID' with the herbarium accession number
df_source_modifiers["specimen-voucher"] = df_source_modifiers["field:accession number"]
df_source_modifiers["Sequence_ID"] = df_source_modifiers["field:accession number"]

# List the columns you need
needed_columns = [
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
]  # Replace these with the actual column names you need
print("beep boop beep bop")
# 'Organism' field_id=10675
# 'Isolate' construct from iNat ID (ex: CA FUNDIS iNaturalist # 147975094)
# Country: build from lat/long
# obscured = result["obscured"]
# if obscured:
#     latitude, longitude = result["private_location"].split(",")
# else:
#     latitude, longitude = result["location"].split(",")

# Collection-date: observed_on
# Collected_by: identifier
# Fwd_primer_name: ITS1F
# Rev_primer_name: ITS4
# Note: RiC from field_id=16718 then use to construct California Fungal Diversity Survey www.fundis.org; iNaturalist.org #147975094; RiC 72

# Select only those columns
df_source_modifiers = df_source_modifiers[needed_columns]

# Save the updated source_modifiers DataFrame
df_source_modifiers.to_csv("new_source_modifiers.tsv", sep="\t", index=False)

# Read FASTA file
with open(fasta_file, "r") as f:
    lines = f.readlines()

# Assuming that the sequences are in the same order as in the source modifiers DataFrame
newlines = []
for i, line in enumerate(lines):
    x = i // 2
    if line.startswith(">"):
        line = ">" + str(df_source_modifiers.loc[x, "Sequence_ID"]) + "\n"
    newlines.append(line)

# Write updated sequences to a new FASTA file
with open("new_sequences.fasta", "w") as f:
    f.writelines(newlines)

print(
    "Mission complete, go get em tiger!. Check new_source_modifiers.tsv and new_sequences.fasta \
and rename them in an informative way. Move everything except for this program and the iNaturalist data to a new folder \
and name it in a way that tells you what you did and when you did it for future reference. Very important. Byeeeeeeeeeeeeee!"
)
