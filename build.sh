#!/bin/bash

DIR_SRC=./
DIR_RELEASES=$DIR_SRC/ipk
DIR_IPK_TMP=$DIR_SRC/tmp

NEW_VERSION=`grep "VERSION=\"" ${DIR_SRC}/bot.py | cut -d'=' -f2 | sed "s/\"//g"`
NEW_VERSION=$(eval echo $NEW_VERSION)

if [ "$1" == "vti" ]; then
  DIR_PKG_BUILD=$DIR_SRC/package-vti/
  TYPE="vti"
  PKG_NAME_ORIG=enigma2-plugin-extensions-junglebot-vti_${NEW_VERSION}_all
else
  DIR_PKG_BUILD=$DIR_SRC/package/
  TYPE="all"
  PKG_NAME_ORIG=enigma2-plugin-extensions-junglebot_${NEW_VERSION}_all
fi

PKG_NAME=junglebot_${NEW_VERSION}_all

echo "Building package $PKG_NAME"

newLine="Version: ${NEW_VERSION}"
sed -i "2s/.*/${newLine}/" $DIR_PKG_BUILD/CONTROL/control

DIR_PKG_DEST=$DIR_PKG_BUILD/usr/bin/junglebot
if [ "$1" == "vti" ]; then
  REQ_FILE='requirements-vti.txt'
else
  REQ_FILE='requirements.txt'
fi
cp -rf $DIR_SRC/bot.py $DIR_SRC/$REQ_FILE $DIR_SRC/amigos.cfg $DIR_SRC/parametros.py $DIR_SRC/locales $DIR_SRC/images $DIR_SRC/CHANGELOG.md $DIR_SRC/README.md $DIR_SRC/LICENSE $DIR_PKG_DEST
  
ipkg-build ${DIR_PKG_BUILD}

mkdir -p ${DIR_RELEASES}
cp -p ${PKG_NAME_ORIG}.ipk ${DIR_RELEASES}/junglebot_${NEW_VERSION}_${TYPE}.ipk
echo "Moved ${PKG_NAME_ORIG}.ipk to ${DIR_RELEASES}/junglebot_${NEW_VERSION}_${TYPE}.ipk"
cp -p ${PKG_NAME_ORIG}.ipk ${DIR_RELEASES}/junglebot_${TYPE}.ipk
echo "Moved ${PKG_NAME_ORIG}.ipk to ${DIR_RELEASES}/junglebot_${TYPE}.ipk"
rm ${PKG_NAME_ORIG}.ipk
rm -rf ${DIR_IPK_TMP}