#!/bin/bash

DIR_SRC=./
DIR_RELEASES=$DIR_SRC/ipk
DIR_IPK_TMP=$DIR_SRC/tmp

NEW_VERSION=`grep "VERSION=\"" ${DIR_SRC}/bot.py | cut -d'=' -f2 | sed "s/\"//g"`
NEW_VERSION=$(eval echo $NEW_VERSION)

if [ "$1" == "vti" ]; then
  DIR_IPK_SRC=$DIR_SRC/package-vti/
  TYPE="vti"
else
  DIR_IPK_SRC=$DIR_SRC/package/
  TYPE="all"
fi

PKG_NAME=junglebot_${NEW_VERSION}_all

echo "Building package $PKG_NAME"

DIR_PKG_BUILD=$DIR_IPK_TMP/$PKG_NAME
rm -rf $DIR_PKG_BUILD
mkdir -p $DIR_PKG_BUILD

cp -rp $DIR_IPK_SRC/* $DIR_PKG_BUILD/
newLine="Version: ${NEW_VERSION}"
sed -i "2s/.*/${newLine}/" $DIR_PKG_BUILD/CONTROL/control

DIR_PKG_DEST=$DIR_PKG_BUILD/usr/bin/junglebot
mkdir -p $DIR_PKG_DEST
if [ "$1" == "vti" ]; then
  REQ_FILE='requirements-vti.txt'
else
  REQ_FILE='requirements.txt'
fi
cp -rf $DIR_SRC/bot.py $DIR_SRC/$REQ_FILE $DIR_SRC/amigos.cfg $DIR_SRC/parametros.py $DIR_SRC/locales $DIR_SRC/images $DIR_PKG_DEST
  
ipkg-build ${DIR_PKG_BUILD}

mkdir -p ${DIR_RELEASES}
cp -p ${PKG_NAME}.ipk ${DIR_RELEASES}/junglebot_${NEW_VERSION}_${TYPE}.ipk
echo "Moved ${PKG_NAME}.ipk to ${DIR_RELEASES}/junglebot_${NEW_VERSION}_${TYPE}.ipk"
cp -p ${PKG_NAME}.ipk ${DIR_RELEASES}/junglebot_${TYPE}.ipk
echo "Moved ${PKG_NAME}.ipk to ${DIR_RELEASES}/junglebot_${TYPE}.ipk"
rm ${PKG_NAME}.ipk
rm -rf ${DIR_IPK_TMP}