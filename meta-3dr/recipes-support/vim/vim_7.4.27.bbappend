SUMMARY = "Vi IMproved - enhanced vi editor"
do_install_append() {
    # Work around rpm picking up csh or awk as a dep
    chmod -x ${D}${datadir}/${BPN}/${VIMDIR}/tools/*.pl
}
