version=$(curl -sL https://api.github.com/repos/dsillman2000/yaml-reference-specs/releases/latest | jq -r .tag_name)
status="failing"
color="red"
YAML_REFERENCE_CLI_EXECUTABLE=$(pwd)/.venv/bin/yaml-reference-cli go run github.com/dsillman2000/yaml-reference-specs@${version}
if [ $? -eq 0 ]; then
    status="passing"
    color="brightgreen"
fi
fmtversion=$(echo ${version} | sed 's/-/--/g')
BADGE="![Spec Status](https://img.shields.io/badge/spec%20${fmtversion}-${status}-${color}?link=https%3A%2F%2Fgithub.com%2Fdsillman2000%2Fyaml-reference-specs%2Ftree%2F${version})"

echo "Updating README badge status:"
echo "  version = ${version}"
echo "  status = ${status}"
echo "  color = ${color}"
sed -i 's|!\[Spec Status\].*|'"$BADGE"'|g' README.md
echo "Done."
