#!/usr/bin/env bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd `dirname $SCRIPT_DIR`

BUILD_PATH="$SCRIPT_DIR/BUILD"
PACKAGE="./package.json"

if [ ! -f "$BUILD_PATH" ]; then
    echo -e "1" > $BUILD_PATH
fi

BUILD=`cat $BUILD_PATH`
# BUILD=`echo $((BUILD + 1))`
# echo -n $BUILD > $BUILD_PATH
echo -n $((BUILD + 1)) > $BUILD_PATH

VERSION=`jq .version -r $PACKAGE`
MAJOR=`echo $VERSION | ( IFS=".$IFS"; read a b && echo $a )`
MINOR=`echo $VERSION | ( IFS=".$IFS"; read a b c && echo $b )`
PATCH=`echo $VERSION | ( IFS=".$IFS"; read a b c d && echo $c )`
# BUILD=`echo $VERSION | ( IFS=".$IFS"; read a b c d e && echo $d )`

VER=`echo $MAJOR.$MINOR.$PATCH`
VER_FULL=`echo $VER.$BUILD`
# git tag v$VER

set -x
$SCRIPT_DIR/build-docker.sh $VER_FULL
set +x

echo -e "$ watch -n 0.01 \"du -sh ./irishandler_python_${VER_FULL}.tar.gz\""
echo -e "$ watch -n 0.01 \"df\""
docker save irishandler-python:$VER_FULL | gzip > irishandler_python_${VER_FULL}.tar.gz
