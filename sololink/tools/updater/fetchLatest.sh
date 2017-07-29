#!/bin/sh

# Given a project directory (where "build" normally is), copy the latest
# update images from:
#     build/tmp*/deploy/images/imx6solo_3dr/3dr-solo*.tar.gz
#     build/tmp*/deploy/images/imx6solo_3dr_artoo/3dr-controller*.tar.gz
# renaming them in the copy with the supplied version number, e.g.
#     controller_x.y.z.tar.gz
#     solo_x.y.z.tar.gz
#
# $1 is the project directory
# $2 is the version (x.y.z)

if [ $# -eq 0 ]; then
    echo "Usage: $0 <project_dir> <version>"
    echo "    where the images are in <project_dir>/build/tmp*/deploy/images"
    exit
fi

if [ -z "${2}" ]; then
    version=`date +%Y%m%d`
else
    version=${2}
fi

image_dir=$1/build/tmp*/deploy/images

get_image() {
    # $1 is solo or controller
    # $2 is link_name
    # $3 is version
    if [ -e ${2} ]; then
        full_path=`readlink ${2}`
        src_name=`basename ${full_path}`
        dst_name=${1}_${3}.tar.gz
        echo "copying ${src_name} -> ${dst_name}"
        cp ${full_path} ${dst_name}
        cp ${full_path}.md5 ${dst_name}.md5
        sed -i "s/${src_name}/${dst_name}/g" ${dst_name}.md5
    else
        echo "${2} not found"
    fi
}

get_image solo ${image_dir}/imx6solo_3dr_1080p/3dr-solo-test.tar.gz ${version}
get_image controller ${image_dir}/imx6solo_3dr_artoo/3dr-controller-test.tar.gz ${version}
