#!/bin/bash

files=("hooks/script.js")

all_files_meta=()

upload_folder_or_file() {
    local path=$1
    local url=$2
    local response

    if [[ -d "$path" ]]; then
        files_args=()
        for filepath in "$path"/*; do
            if [[ -f "$filepath" ]]; then
                files_args+=("-F" "files=@$filepath")
            fi
        done
        response=$(curl -s -X POST "${files_args[@]}" "$url")
    elif [[ -f "$path" ]]; then
        response=$(curl -s -X POST -F "files=@$path" "$url")
    else
        echo "Path not found: $path"
        return 1
    fi

    # Extract and append to the all_files_meta array
    # Requires jq installed
    mapfile -t meta_items < <(echo "$response" | jq -r '.files_meta[]')
    all_files_meta+=("${meta_items[@]}")
}

for item in "${files[@]}"; do
  upload_folder_or_file "$item" "http://127.0.0.1:8000/upload-files"
done

# Print all collected metadata
echo "Collected files_meta:"
printf '%s\n' "${all_files_meta[@]}"
