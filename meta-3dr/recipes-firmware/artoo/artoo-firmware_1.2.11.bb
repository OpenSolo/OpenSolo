SUMMARY = "Artoo firmware binary"

LICENSE = "APACHE2.0"

FILESEXTRAPATHS_prepend := "${THISDIR}/files/:"

# stick-cfg-evt-*.cfg are for use with sololink_config
SRC_URI += "file://stick-cfg-evt-mode1.cfg \
            file://stick-cfg-evt-mode2.cfg \
            file://stick-cfg-evt-default.cfg"

firmwaredir = "/firmware"
FILES_${PN} += "${firmwaredir}/"
FILES_${PN} += "${firmwaredir}/cfg"

REPO_NAME = "artoo"
REPO_TAG = "v${PV}"
FILE_EXT = "bin"
FILE_SRC = "artoo_${PV}.${FILE_EXT}"
FILE_DST = "artoo_${PV}.${FILE_EXT}"

do_fetch () {
    #
    # look up a release by tag name via the github api,
    # extract the url for the build artifact that we're interested in (*.FILE_EXT),
    # and download it.
    #
    # requires jq 1.4 or later: https://stedolan.github.io/jq/
    #

    # NB: this relies on the fact that tag names in the repo are of a specific form
    #     such that we can derive the tag name from the bitbake PV variable, which is itself
    #     derived from the name of this file.

    # There must be a github "personal access token" in the file ~/.ssh/github_token
    # https://help.github.com/articles/creating-an-access-token-for-command-line-use/
    TOKEN=$(cat ~/.ssh/github_token)

    SRC_URL="https://api.github.com/repos/OpenSolo/${REPO_NAME}/releases/tags/${REPO_TAG}"

    BIN_URL=$(curl -s -H "Authorization: token ${TOKEN}" -H "Accept: application/json" ${SRC_URL} | jq -r '.assets[] | select(.name | endswith(".${FILE_EXT}")) | .url')

    # NB: supply github access token as url param because if we supply it as a header,
    #     once github redirects us to s3, it gets included in that request as well
    #     and amazon complains that 2 forms of auth have been provided and quits.
    curl -v -L -H "Accept: application/octet-stream" ${BIN_URL}?access_token=${TOKEN} -o ${WORKDIR}/${FILE_SRC}
}

do_install () {
    install -d ${D}${firmwaredir}
    install -m 0644 ${WORKDIR}/${FILE_SRC} ${D}${firmwaredir}/${FILE_DST}
    install -d ${D}${firmwaredir}/cfg/
    install -m 0644 ${WORKDIR}/stick-cfg-evt-mode1.cfg ${D}${firmwaredir}/cfg
    install -m 0644 ${WORKDIR}/stick-cfg-evt-mode2.cfg ${D}${firmwaredir}/cfg
    install -m 0644 ${WORKDIR}/stick-cfg-evt-default.cfg ${D}${firmwaredir}/cfg
}
