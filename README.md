# uW PDF Conversion Tools
Conversion tool for converting uW resources to PDF.

NOTE: Python 3 Only

# To run

```bash
cd /opt && git clone https://github.com/unfoldingWord-dev/uw-pdf-conversion-tools.git
cd /opt/uw-pdf-conversion-tools && pip3 install -r requirements.txt
cd /opt/uw-pdf-conversion-tools
./run.sh <converter> [-hr] [-l <lang>] [-w <working_dir>] [-o <output_dir>] [-p <project>] [--owner <owner>] [--<resource>-tag <tag>] 
```

`<converter>` can be the following:
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
  -h, --help             show this help message and exit
  -r, --regenerate       Regenerate PDF even if exists: Default: false
  -l LANG_CODES, --lang_code LANG_CODES
                         Language Code(s). Default: en
  -w WORKING_DIR, --working WORKING_DIR
                         Working Directory. Default: a temp directory that gets
                        deleted
  -o OUTPUT_DIR, --output OUTPUT_DIR
                         Output Directory. Default: ./
  -p PROJECT_IDS, --project_id PROJECT_IDS
                         Project ID(s) for resources with projects, such as a
                        Bible book. Default: all
  --owner OWNER          Owner of the resource repo on GitHub. Default:
                        unfoldingWord
  --<resource>-tag <tag> For every resource used, you can specify a branch or tag.
                         Default: master (run `./run.sh <converter> -h` for possible tags)
```

# Examples

- Run the OBS SN PDF converter for English (default language) but don't generate if PDF already exists in the output dir:

    `./run.sh obs_sn_pdf_converter -w ~/working -o ~/output`

- Run the TA PDF converter for English and French and generate even if the latest commit has a PDF file in the output dir

    `./run.sh ta_pdf_converter -w ~/working -o ~/output -l en -l fr -r`

- Run the OBS TN PDF converter for English and use release versions v6 of OBS TN, v6 of OBS, v11 of TA and v11 of TW.

    `./run.sh obs_tn_pdf_converter -w ~/working -o ~/output -l en --obs-tn-tag v6 --obs-tag v6 --ta-tag v11 --tw-tag v11`

# Notes
 - Language being generate must have a locale file in the `./locale` directory. You can copy the `English-en_US.json` file to a new language and update the strings on the right.
 - A index.php will be linked to in your output dir to list all of the latest versions of the resources generated
