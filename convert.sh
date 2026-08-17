#!/bin/bash

function usage {
    echo -e "usage: $0 [-p <string>]\n\nBatch convert GoPro .MP4 files into .avi with mjpeg codec."
    echo "-p        Path to video folder containing .MP4 videos"
    exit
}

while getopts ":p:h" o
do
    case "$o" in
        p)
            input_dir=$OPTARG
            echo "Video path set to $input_dir"
            ;;
        h)
            usage
            ;;
        :)
            echo "ERROR: Option -$OPTARG requires an argument"
            usage
            ;;
        \?)
            echo "Invalid option -$OPTARG"
            usage
            ;;
    esac
done


# Directory containing the .mp4 files (can be set to current directory)
#input_dir="."

# Loop through each .mp4 file
for file in "$input_dir"/*.MP4; do
    # Skip if no .mp4 files are found
    [ -e "$file" ] || continue

    # Extract the base filename (without extension)
    base_name=$(basename "$file" .MP4)

    # Construct the output .avi filename
    output_file="$input_dir/$base_name.avi"

    # Run ffmpeg to convert the file
    ffmpeg -i "$file" -vcodec mjpeg -q:v 1 -an "$output_file"
done

