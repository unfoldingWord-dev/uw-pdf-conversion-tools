#!/usr/bin/bash

if ps -ef | grep -v grep | grep 'pdf_converter.py\|_checking.py'  ; then
        echo "ALREADY GENERATING PDFS!"
        exit 0
fi

set -e
set -x

export WORKING_DIR=/home/rmahn/working
export OUTPUT_DIR=/home/rmahn/output

cd /home/rmahn/repos/uw-pdf-conversion-tools

./obs_tn_pdf_converter.py -l en -l fr -l shu $@
./obs_sn_pdf_converter.py -l en -l fr -l shu $@
./obs_sn_sq_pdf_converter.py -l en -l fr $@
./obs_sq_pdf_converter.py -l en -l fr -l shu $@
./obs_pdf_converter.py -l en -l fr -l shu $@
./tn_checking.py -l en $@
./tw_checking.py -l en $@
./ta_pdf_converter.py -l en $@
./tq_pdf_converter.py -l en $@
./tq_pdf_converter.py -l en -p all $@
./tw_pdf_converter.py $@
#./bible_pdf_converter.py -l en -b ult $@
#./bible_pdf_converter.py -l en -b ust $@
#./bible_pdf_converter.py -l en -b ult -p nt $@
#./bible_pdf_converter.py -l en -b ust -p nt $@
#./bible_pdf_converter.py -l en -b ult -p ot $@
#./bible_pdf_converter.py -l en -b ust -p ot $@
#./bible_pdf_converter.py -l en -b ult -p all $@
#./bible_pdf_converter.py -l en -b ust -p all $@
./tn_pdf_converter.py $@

