#!/usr/bin/bash

if ps -ef | grep -v grep | grep 'pdf_converter.py\|_checking.py'  ; then
        echo "ALREADY GENERATING PDFS!"
        exit 0
fi

set -e

export WORKING_DIR=/home/rmahn/working
export OUTPUT_DIR=/home/rmahn/output

cd /home/rmahn/repos/uw-pdf-conversion-tools

./sn_pdf_converter.py -l en -p tit $@
./obs_tn_pdf_converter.py -l en -l fr -l kn $@
./obs_sn_pdf_converter.py -l en -l fr -l shu $@ 
./obs_sn_sq_pdf_converter.py -l en -l fr -l shu $@ 
./obs_sq_pdf_converter.py -l en -l fr -l shu $@ 
./obs_pdf_converter.py -l en -l fr -l shu -l ml -l nag -l ta -l te -l kn -l as $@
./tw_pdf_converter.py $@
./tw_checking.py -l en $@
./ta_pdf_converter.py -l en $@
./tq_pdf_converter.py -l en $@
./tq_pdf_converter.py -l en -p all $@
./tn_pdf_converter.py $@
./tn_checking.py -l en $@
#./bible_pdf_converter.py -l en -b ult $@
#./bible_pdf_converter.py -l en -b ust $@
#./bible_pdf_converter.py -l en -b ult -p nt $@
#./bible_pdf_converter.py -l en -b ust -p nt $@
#./bible_pdf_converter.py -l en -b ult -p ot $@
#./bible_pdf_converter.py -l en -b ust -p ot $@
#./bible_pdf_converter.py -l en -b ult -p all $@
#./bible_pdf_converter.py -l en -b ust -p all $@
