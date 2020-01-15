# uW PDF Conversion Tools
Conversion tool for converting uW resources to PDF.

NOTE: Python 3 Only

# To run

```bash
cd /opt && git clone https://github.com/unfoldingWord-dev/uw-pdf-conversion-tools.git
cd /opt/uw-pdf-conversion-tools && pip3 install -r requirements.txt
cd /opt/uw-pdf-conversion-tools && ./run.sh <resource converter> <arguments>
```

`resource_converter` can be the following:
  - obs_pdf_converter
  - obs_sn_pdf_converter
  - obs_sn_sq_pdf_converter
  - obs_sq_pdf_converter
  - obs_tn_pdf_converter
  - ta_pdf_converter
  - tn_pdf_converter
  - tq_pdf_converter
  - tw_pdf_converter

optional arguments:
```
  -h, --help            show this help message and exit
  -l LANG_CODES, --lang_code LANG_CODES
                        Language Code(s)
  -p PROJECT_IDS, --project_id PROJECT_IDS
                        Project ID(s)
  -w WORKING_DIR, --working WORKING_DIR
                        Working Directory
  -o OUTPUT_DIR, --output OUTPUT_DIR
                        Output Directory
  --owner OWNER         Owner
  -r, --regenerate      Regenerate PDF even if exists
  --obs-tag OBS
```

# Example

- Run the OBS TN PDF converter for English (default language) but don't generate if already exists in the output dir:

    `./run.sh obs_tn_pdf_converter -w ~/working -o ~/output`

- Run the TA PDF converter for English and French and generate even if the latest commit has a HTML and PDF file in the output dir

    `./run.sh obs_tn_pdf_converter -w ~/working -o ~/output -l en -l fr -r`

# Notes
Language being generate must have a locale file in the `./locale` directory. You can copy the `English-en_US.json` file to a new language and update the strings on the right.

