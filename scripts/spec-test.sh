version=$(curl -sL https://api.github.com/repos/dsillman2000/yaml-reference-specs/releases/latest | jq -r .tag_name)
status="failing"
color="red"
YAML_REFERENCE_CLI_EXECUTABLE=$(pwd)/.venv/bin/yaml-reference-cli go run github.com/dsillman2000/yaml-reference-specs@${version}
if [ $? -eq 0 ]; then
    status="passing"
fi
fmtversion=$(echo ${version} | sed 's/-/--/g')
echo "Spec test compliance status:"
echo "  version = ${version}"
echo "  status = ${status}"
echo "Done."
