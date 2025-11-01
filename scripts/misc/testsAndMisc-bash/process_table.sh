
#!/bin/bash

process_table_schema() {
    while IFS=$'\t' read -r column_name _ data_type _; do
        # Print the column name and data type
        echo -e "$column_name\t$data_type"
    done < "$1"
}

input_file="$1"

# Check if a file is provided as an argument
if [ $# -eq 0 ]; then
    echo "Usage: $0 <filename>"
    exit 1
fi

# Process the provided file and skip the first row
first_line=true
process_table_schema "$input_file" | while IFS=$'\t' read -r column_name data_type; do
    if [ "$first_line" = true ]; then
        first_line=false
        continue
    fi
    case "$data_type" in
        "timestamp")
            sqlalchemy_type="DateTime"
            ;;
        "int"|"integer"|"int4")
            sqlalchemy_type="Integer"
            ;;
        "varchar"*|"text")
            sqlalchemy_type="String" # handles types like varchar(256)
            ;;
        "boolean"|"bool")
            sqlalchemy_type="Boolean"
            ;;
        "float"|"float8")
            sqlalchemy_type="Float"
            ;;
        "serial4")
            sqlalchemy_type="Integer"
            ;;
        "numeric"*)
            sqlalchemy_type="Numeric" # handles types like numeric(12, 2)
            ;;
        *)
            sqlalchemy_type="UNDEFINED_CHANGE_ME" # default to UNDEFINED_CHANGE_ME if data type is unrecognized
            ;;
    esac
    echo "$column_name = Column($sqlalchemy_type)"
done