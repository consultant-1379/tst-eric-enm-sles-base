ARG OS_BASE_IMAGE_NAME=sles
ARG OS_BASE_IMAGE_REPO=armdocker.rnd.ericsson.se/proj-ldc/common_base_os
ARG OS_BASE_IMAGE_TAG="3.49.0-4"

FROM ${OS_BASE_IMAGE_REPO}/${OS_BASE_IMAGE_NAME}:${OS_BASE_IMAGE_TAG}

ARG BUILD_DATE=unspecified
ARG IMAGE_BUILD_VERSION=unspecified
ARG GIT_COMMIT=unspecified
ARG ISO_VERSION=unspecified
ARG RSTATE=unspecified

LABEL \
com.ericsson.product-number="CXC 174 2278" \
com.ericsson.product-revision=$RSTATE \
enm_iso_version=$ISO_VERSION \
org.label-schema.name="ENM SLES Common Base OS Base Image" \
org.label-schema.build-date=$BUILD_DATE \
org.label-schema.vcs-ref=$GIT_COMMIT \
org.label-schema.vendor="Ericsson" \
org.label-schema.version=$IMAGE_BUILD_VERSION \
org.label-schema.schema-version="1.0.0-rc1"

ARG SLES_BASE_OS_REPO=sles_base_os_repo
ARG CBO_REPO=arm.rnd.ki.sw.ericsson.se/artifactory/proj-ldc-repo-rpm-local/common_base_os/sles/
ARG CBO_VERSION="3.49.0-4"

ARG ENM_ISO_REPO_URL=ci-portal.seli.wh.rnd.internal.ericsson.com/static/staticRepos/
ARG ENM_ISO_REPO_VERSION=ENM_20_13_ERICenm_CXP9027091_1_97_28
ARG ENM_ISO_REPO_NAME=enm_iso_repo

RUN zypper addrepo -C -G -f https://${CBO_REPO}${CBO_VERSION}?ssl_verify=no $SLES_BASE_OS_REPO && \
    zypper addrepo -C -G -f https://${ENM_ISO_REPO_URL}${ENM_ISO_REPO_VERSION}?ssl_verify=no $ENM_ISO_REPO_NAME

COPY image_content/ERIClitpvmmonitord_CXP9031644* /var/tmp/
COPY image_content/omelasticsearch.so /usr/lib64/rsyslog/omelasticsearch.so

RUN mkdir -p /usr/share/man/man1

# SLES - need to  install python 2.7 or vmmonitord will pull in latest from suse repo which is python 3.
# SLES - cron default on base rhel, needs to be installed on SLES, used by web context registration.
# SLES - python2-pycurl - used by pib, default on rhel, needs to be installed on SLES
# SLES - higher version of rsyslog & omelasticsearch available, compatable with ES 6.X(ADP version)
# SLES - shadow brings in the user/group commands
# SLES - zypper as package manager, "zypper dup -y" same as "yum update -y"
# SLES - remove rhel and litp repo to avoid clashes with suse software
# TODO
# VMMONITORD - needs to be replaced with new version to avoid daemon process
RUN zypper dup -y && \
    zypper install -y rsyslog \
    hostname \
    sysvinit-tools \
    curl \
    python \
    python2-pycurl \
    bind-utils \
    sudo \
    cron \
    shadow \
    EXTRserverjre_CXP9035480 && \
    zypper --no-gpg-checks install -y /var/tmp/ERIClitpvmmonitord_CXP9031644* && \
    zypper clean -a && \
    rm -f /var/tmp/ERIClitpvmmonitord_CXP9031644* \
    /etc/rsyslog.d/remote.conf

ARG _ERIC_DIRS_="/ericsson /etc/opt/ericsson /opt/ericsson /var/opt/ericsson"

COPY image_content/scripts/nonroot/change_permissions.sh /usr/local/bin/change_permissions.sh
# SLES - groupmem not available in SLES, used usermod
# SLES - useradd requires -m to create home dir, rhel creates by default
RUN groupadd -g 205 enm && \
    groupadd -g 206 jboss && \
    useradd -genm -d /home/enmadm -m enmadm && \
    useradd -genm -u 308 -d /home/jboss_user -m jboss_user && \
    groupadd -g 500 cloud-user && \
    useradd -g cloud-user -d /home/cloud-user -m cloud-user && \
    usermod -a -G cloud-user cloud-user && \
    usermod -a -G jboss,enm enmadm && \
    usermod -a -G jboss,enm jboss_user && \
    chgrp root /home /run/lock && \
    chmod 775 /home && \
    mkdir -m 775 /ericsson /ericsson/3pp /ericsson/3pp/jboss && \
    bash /usr/local/bin/change_permissions.sh && \
    find /var/log ! -name zypper.log -exec chmod g=u {} \; && \
    chmod g=u /run /usr/java/default/jre/lib/security/cacerts


ENV JAVA_HOME=/usr/java/latest
ENV PATH=$PATH:$JAVA_HOME/bin
ENV PATH=$PATH:/sbin
ENV PATH=$PATH:/usr/sbin

COPY image_content/rsyslog.d/* /etc/rsyslog.d/
COPY image_content/limits.d/* /etc/security/limits.d/
COPY image_content/rsyslog.conf /etc/rsyslog.conf
RUN mkdir -pm 775 /usr/lib/ocf/resource.d/ && \
    chown jboss_user:root /usr/lib/ocf/resource.d/
COPY --chown=jboss_user:root image_content/scripts/healthcheck/ /usr/lib/ocf/resource.d/
RUN chmod 771 /usr/lib/ocf/resource.d/rsyslog-healthcheck.sh

COPY --chown=jboss_user:root --from=armdocker.rnd.ericsson.se/proj-enm/eric-enm-healthcheck-agent:1.0.0-1 /ericsson/enm_healthcheck/bin/enm_healthcheck.py /ericsson/enm_healthcheck/bin/enm_healthcheck.py

# SLES - 90-nproc.conf didn't exist, this would overwrite the limits.conf setting if exist and as we are setting to same values so not needed.
# SLES - stopping of services not required.
RUN sed -i '$ i\*               -       nofile          10240' /etc/security/limits.conf && \
        sed -i '$ i\*           -       nproc           10240' /etc/security/limits.conf && \
        rm -f /etc/localtime
