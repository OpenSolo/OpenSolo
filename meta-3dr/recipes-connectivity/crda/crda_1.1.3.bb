DESCRIPTION = "Wireless Central Regulatory Domain Agent"
HOMEPAGE = "http://wireless.kernel.org/en/developers/Regulatory/CRDA"

LICENSE = "ISC"
LIC_FILES_CHKSUM = "file://LICENSE;md5=07c4f6dea3845b02a18dc00c8c87699c"


DEPENDS = "python-m2crypto-native python-native libgcrypt libnl"

SRC_URI = "https://www.kernel.org/pub/software/network/crda/${BP}.tar.bz2;name=crda \
           https://www.kernel.org/pub/software/network/wireless-regdb/wireless-regdb-2013.01.11.tar.bz2;name=bin \
"

SRC_URI[crda.md5sum] = "29579185e06a75675507527243d28e5c"
SRC_URI[crda.sha256sum] = "aa8a7fe92f0765986c421a5b6768a185375ac210393df0605ee132f6754825f0"
SRC_URI[bin.md5sum] = "f137585abd5e07454932ea555b826149"
SRC_URI[bin.sha256sum] = "6eb469555eb547b22738ce7bf59ebba42138560f128085a5e238eb6c8075792e"

inherit python-dir pythonnative
# Recursive make problem
EXTRA_OEMAKE = "MAKEFLAGS= DESTDIR=${D}"

do_compile() {
    oe_runmake all_noverify
}

do_install() {
    oe_runmake install

    install -d ${D}${libdir}/crda/

    install -m 0644 ${WORKDIR}/wireless-regdb-2013.01.11/regulatory.bin ${D}${libdir}/crda/regulatory.bin
}


RDEPENDS_${PN} = "udev"
FILES_${PN} += "${libdir}crda/regulatory.bin \
                ${base_libdir}/udev/rules.d/85-regulatory.rules \
"
