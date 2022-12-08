# Import Module
import tabula

# Read PDF File
# this contain a list
df = tabula.read_pdf("Suvendu Patra cibill report.pdf", pages = 6)[0]

# Convert into Excel File
df.to_excel('Excel File Path')

