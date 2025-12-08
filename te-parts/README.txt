# TE_scraper
This script downloads PDFs from TE using a list of `part_number` values in an Excel file.

1. Requirements
	Python 3.11+ (recommended)
	Install the required Python packages: pip install aiohttp aiofiles pandas openpyxl

2. In the same folder as TE_scraper.py, create an Excel file named te_parts.xlsx
	The file must have a column named part_number
	Each row should contain one TE part number

3. Open a terminal / command prompt in that folder
	Run: python te_scraper.py



# TE_pdf_rename
This script renames all downloaded PDF files into the required naming format and also removes/ignores duplicates automatically.

How it Works
1. First, run `TE_scraper.py`.  
   	It will download all PDFs into the **PDFs** folder (created automatically in the same directory).

2. After TE_scraper has finished:
   	All PDFs are already stored inside the `PDFs` folder.
   	Now you can run this script to clean and rename them.

How to Run
Open a terminal / command prompt in that folder
	Run: python TE_pdf_rename.py



#TE_pdf_to_excel
This script scans all PDF files inside a `PDFs` folder, extracts key TE product information (part number, description, RoHS/ELV/REACH/halogen content, etc.)

1. Requirements:
	pip install pdfplumber PyPDF2 pymupdf

2. Place the script and make sure you have a PDFs folder
	(All input PDFs must be inside the PDFs folder)

3. Open a terminal / command prompt in that folder
	Run: python TE_pdf_to_excel.py