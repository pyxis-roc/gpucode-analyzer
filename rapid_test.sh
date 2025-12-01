#!/bin/bash

if [ $# -lt 1 ]; then
    echo Usage: $0 sass-files
    exit 1;
fi;

for i in "$@"; do
    echo $i
    FN=`echo $(basename $i) | awk -F. '{print $2}'`

    if [ -z "$FN" ]; then
        echo $i malformed
        continue;
    fi;
    YAML="`dirname $i`/${FN}.yaml"
    if [ ! -f "$YAML" ]; then
        cat > $YAML <<EOF
$FN:
  global_decl: []
  args: []
  constant_map: {}
EOF
    fi;

    echo '**** ' $i
    echo "python3 -m gpucodeanalyzer.cfg2c ${i} $YAML ${FN}.c"
    python3 -m gpucodeanalyzer.cfg2c ${i} $YAML ${FN}.c
    clang -c ${FN}.c -I gpucodeanalyzer/isa/sass
done;
