#!/usr/bin/env bash
# -*- coding: utf8 -*-
#
#  Copyright (c) 2019 unfoldingWord
#  http://creativecommons.org/licenses/MIT/
#  See LICENSE file for details.
#
#  Contributors:
#  Richard Mahn <rich.mahn@unfoldingword.org>

set -e
set -x

MY_DIR=$(cd $(dirname "$0") && pwd)

if [ ! -z $1 ]; then
  WORKING_DIR=$1
fi

if [ -z $WORKING_DIR ]; then
    echo "Please specify the working directory for the tn_pdf_converter."
    exit 1
fi

if [ ! -d "$WORKING_DIR" ]; then
  echo "WORKING_DIR $WORKING_DIR doesn't exist"
  exit 1
fi

RESOURCE_DIR="$WORKING_DIR/tn_resources"

if [ -d "$RESOURCE_DIR" ]; then
  echo "$RESOURCE_DIR already exists. Please remove it and run this script again"
  exit 1
fi

cp -R "$MY_DIR/tn_resources" "$RESOURCE_DIR"

cd "$RESOURCE_DIR"
npm i
node ./getResources.js ./

rm -rf en/translationHelps en/bibles/t4t en/bibles/udb en/bibles/ulb
rm -rf kn/translationHelps
rm -rf hbo/bibles
rm -rf el-x-koine/bibles

echo "TN Resources have been installed in $RESOURCE_DIR"
