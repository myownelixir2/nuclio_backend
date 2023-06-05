#!/bin/bash

PREFIX="tests.test_"
TEST_FILES=("auth" "activity" "generator" "mixer" "post_fx" "storage" "utils")

for test_file in "${TEST_FILES[@]}"
do
   python -m unittest "${PREFIX}${test_file}"
done