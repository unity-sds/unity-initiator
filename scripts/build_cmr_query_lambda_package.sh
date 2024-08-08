#!/bin/bash
BASE_PATH=$(dirname "${BASH_SOURCE}")
BASE_PATH=$(cd "${BASE_PATH}/.."; pwd)
DIST_DIR=${BASE_PATH}/dist
PKG_DIR=${DIST_DIR}/lambda_packages
CMR_QUERY_DIR=${BASE_PATH}/terraform-unity/triggers/cmr_query

set -ex

rm -rf $DIST_DIR
pip install hatch
hatch clean
hatch build
VERSION=$(hatch run python -c 'from importlib.metadata import version; print(version("unity_initiator"))')
echo "{\"version\": \"$VERSION\"}" > ${DIST_DIR}/version.json
mkdir -p $PKG_DIR
pip install -t $PKG_DIR ${DIST_DIR}/unity_initiator-*.whl
pip install -t $PKG_DIR python_cmr
cp ${CMR_QUERY_DIR}/lambda_handler.py $PKG_DIR/
cd $PKG_DIR
zip -rq ${DIST_DIR}/cmr_query-${VERSION}-lambda.zip .
