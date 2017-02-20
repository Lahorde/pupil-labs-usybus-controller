#!/bin/sh
function usage()
{
  echo "Description : "
  echo "  Compare pupil exported gaze with UB2 gaze received"
  echo "PARAMS :"
  echo "  pupil player gaze exported file"
  echo "  uvy_bus subscriber gaze file"
  echo "  number of line to compare"
}

function check_args()
{
  if [ $# -ne 3 ]
  then 
    (>&2 echo "Error : invalid number of arguments")
    usage
    exit 1
  fi
}

check_args "$@"
set -o pipefail

nb_lines=$3
# check line count
if [ $(grep -c "^.*$" $1) -lt $3 ] | [ $(grep -c "^.*$" $2) -lt $3 ]
then
  grep -c "^.*$" $1 
  nb_lines=$(grep -c "^.*$" $1)
fi
  
# check line count
if [ $(grep -c "^.*$" $2) -lt $nb_lines ]
then
  nb_lines=$(grep -c "^.*$" $2)
fi

echo "run test on $nb_lines of gaze data"

# Extract only gaze from pupilabs capture exported csv file
pupil_export_gaze="$(sed '1d' $1 | sed -rn 's/^(([^,]+,){3})([^,]+,[^,]+),.*/\3/p')"
if [ $? -ne 0 ]
then
 usage
fi 

for line in $(seq $nb_lines)
do
  pupil_export_gaze_lines="$(echo "$pupil_export_gaze" | sed -n "1,${line}p")"
  # grep on multiple lines (use -Pz option of grep) with multiple lines regexp (use tr)
  if ! less "$2" | tr '\n' ' ' | grep -Pzo "$(echo "$pupil_export_gaze_lines" | tr '\n' ' ')" > /dev/null
  then 
    (>&2 echo "TEST KO - mismatch at line $line")
    exit 1 
  fi
done
  
pupil_export_gaze_lines="$(echo "$pupil_export_gaze" | sed -n "1,${nb_lines}p")"

# grep on multiple lines (use -Pz option of grep) with multiple lines regexp (use tr)
if less "$2" | tr '\n' ' ' | grep -Pzo "$(echo "$pupil_export_gaze_lines" | tr '\n' ' ')" > /dev/null
then
  echo TEST OK
else
  (>&2 echo TEST KO)
  exit 1 
fi
