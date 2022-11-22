SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_DIR=$( dirname ${SCRIPT_DIR} )
sudo chown $USER -R ${PROJECT_DIR}/storage