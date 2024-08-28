#!/bin/bash

###########################################################################
# COPYRIGHT Ericsson 2021
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
###########################################################################

# GLOBAL VARIABLES
_SLES_RSYSLOG_INSTALLATION=/sbin/rsyslogd
_RHEL_RSYSLOG_INSTALLATION=/etc/init.d/rsyslog
ARG="status"
_DISABLE_ENV_VAR="$DISABLE_RSYSLOG_HEALTH_CHECK"


#///////////////////////////////////////////////////////////////
# end successfuly if container is configured to disable Rsyslog health check
#///////////////////////////////////////////////////////////////

if [[ -n $_DISABLE_ENV_VAR  && $_DISABLE_ENV_VAR == "True" ]]; then
  exit 0;
fi

#//////////////////////////////////////////////////////////////
# RHEL/PHYSICAL/vENM
#/////////////////////////////////////////////////////////////
if [[ -f $_RHEL_RSYSLOG_INSTALLATION ]]; then
  $_RHEL_RSYSLOG_INSTALLATION $ARG > /dev/null 2>&1
  ret=$?
  if [[ "$ret" -eq 0 ]]; then
    exit 0
  else
    logger "rsyslog not running"
    exit 1
  fi
fi


#//////////////////////////////////////////////////////////////
# SLES
#/////////////////////////////////////////////////////////////

if [[ -f $_SLES_RSYSLOG_INSTALLATION ]]; then
  pidof /sbin/rsyslogd &> /dev/null
  ret=$?
  if [[ "$ret" -eq 0 ]]; then
    exit 0;
  fi
  logger "rsyslog not running";
  exit 1
fi

#//////////////////////////////////////////////////////////////
# RSYSLOG not being installed
#/////////////////////////////////////////////////////////////

exit 0