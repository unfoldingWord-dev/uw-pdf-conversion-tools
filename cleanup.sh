#!/bin/bash

set -e

if ps -ef | grep -v grep | grep 'pdf_converter.py\|_checking.py'  ; then
        echo "CURRENTLY GENERATING PDFS!"
        exit 0
fi

rm -rf /home/rmahn/working/resources_*

OIFS="$IFS"
IFS=$'\n'

cd /home/rmahn/output
files="$(find save log obs* ta* tn* tw* ult* ust* -type f -name '*.html' -or -name '*.pdf' -or -name "*_rcs.json" -or -name "*_bad_*.json" -or -name "*_appendix_rcs.json" -or -name "*.log")"
for f in $files; do
    dir=$(dirname $f)
    list="$(find -L $dir -xtype l -samefile "$f")"
    if [[ "$list" == "" ]]; then
        echo "$f does not have symlink."
        rm $f
    fi
done
cd ~/

IFS="$OIFS"

