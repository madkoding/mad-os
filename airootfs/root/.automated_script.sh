#!/usr/bin/env bash

script_cmdline() {
    local param
    for param in $(</proc/cmdline); do
        case "${param}" in
            script=*)
                echo "${param#*=}"
                return 0
                ;;
            *)
                :
                ;;
        esac
    done
    return 0
}

automated_script() {
    local script rt
    local tmp_script
    script="$(script_cmdline)"
    if [[ -n "${script}" ]]; then
        tmp_script="$(mktemp /tmp/startup_script.XXXXXX)"
        if [[ "${script}" =~ ^((http|https|ftp|tftp)://) ]]; then
            # there's no synchronization for network availability before executing this script
            printf '%s: waiting for network-online.target\n' "$0"
            until systemctl --quiet is-active network-online.target; do
                sleep 1
            done
            printf '%s: downloading %s\n' "$0" "${script}"
            curl "${script}" --location --retry-connrefused --retry 10 --fail -s -o "${tmp_script}"
            rt=$?
        else
            cp "${script}" "${tmp_script}"
            rt=$?
        fi
        if [[ ${rt} -eq 0 ]]; then
            chmod 700 "${tmp_script}"
            printf '%s: executing automated script\n' "$0"
            # note that script is executed when other services (like pacman-init) may be still in progress, please
            # synchronize to "systemctl is-system-running --wait" when your script depends on other services
            "${tmp_script}"
        fi
        rm -f "${tmp_script}"
    fi
    return 0
}

if [[ $(tty) == "/dev/tty1" ]]; then
    automated_script
fi
