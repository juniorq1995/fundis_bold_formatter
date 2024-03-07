import pandas as pd

# User inputs
print("Initializing FUNDIS Sheet Crusher 5000...")
print("Welcome Validator")
source_modifiers_tsv = input("Enter name of file from MycoMap (i.e. something.tsv): ")
inat_csv = input("Enter name of iNat data (i.e. iNat9.21.csv): ")
fasta_file = input("Enter the FASTA file (i.e. sequences.fasta): ")
print("Spooling transmodulators")

# Load DataFrames
df_source_modifiers = pd.read_csv(source_modifiers_tsv, sep='\t')
df_inat = pd.read_csv(inat_csv)

# Extract iNat_ID from the 'Isolate' column
df_source_modifiers['iNat_ID'] = df_source_modifiers['Isolate'].str.split('#').str[1]
df_source_modifiers['iNat_ID'] = df_source_modifiers['iNat_ID'].astype(int)
print("Actuating quantum telemetry values")

# Merge DataFrames based on iNat_ID
df_source_modifiers = pd.merge(df_source_modifiers, df_inat, left_on='iNat_ID', right_on='id', how='left')

# Create a new column "specimen-voucher" and replace 'Sequence_ID' with the herbarium accession number
df_source_modifiers['specimen-voucher'] = df_source_modifiers['field:accession number'] # TODO: Get this field from iNat directly using inat id from tsv file
# df_source_modifiers['Sequence_ID'] = df_source_modifiers['field:accession number'] # TODO Why same value with diff names?
seq_accession_mapping = dict(zip(df_source_modifiers['Sequence_ID'], df_source_modifiers['specimen-voucher']))

# List the columns you need
needed_columns = ['Sequence_ID', 'specimen-voucher', 'Organism', 'Isolate', 'Country', 'Collection-date', 
'Collected_by', 'Fwd_primer_name', 'Rev_primer_name', 'Note' ]  # Replace these with the actual column names you need
print("beep boop beep bop")
# Select only those columns
df_source_modifiers = df_source_modifiers[needed_columns]
df['inat_id'] = df['Isolate'].str.split("# ", n=1).str[1] # TODO: Get accession num from iNat

# Save the updated source_modifiers DataFrame
df_source_modifiers.to_csv('new_source_modifiers.tsv', sep='\t', index=False)

# Read FASTA file
with open(fasta_file, 'r') as f:
	lines = f.readlines()

# Assuming that the sequences are in the same order as in the source modifiers DataFrame
newlines = []
for i, line in enumerate(lines):
	x = i // 2
	if line.startswith('>'):
		seq_id = int(line[1:])
		accession_num = seq_accession_mapping[seq_id]
		line = f">{accession_num}\n"
	newlines.append(line)

# Write updated sequences to a new FASTA file
with open('new_sequences.fasta', 'w') as f:
	f.writelines(newlines)

print("Mission complete, go get em tiger!. Check new_source_modifiers.tsv and new_sequences.fasta \
and rename them in an informative way. Move everything except for this program and the iNaturalist data to a new folder \
and name it in a way that tells you what you did and when you did it for future reference. Very important. Byeeeeeeeeeeeeee!")
