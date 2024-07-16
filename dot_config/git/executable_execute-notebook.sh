#!/bin/sh

nb=$(mktemp --suffix=.ipynb)
cat - > ${nb}
jupyter nbconvert --inplace --execute --NotebookClient.record_timing=False ${nb} 1>&2
cat ${nb}
rm -f ${nb}
