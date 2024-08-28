#!/usr/bin/env bash

source ./pipeline/scripts/gerrit_server_info
source ./pipeline/scripts/trigger_and_verify_gerrit_change.sh

GERRIT_PROJ="OSS/com.ericsson.oss.containerisation/eric-enm-sles-base"
PATCH_VERIFICATION_TIMEOUT_SEC=14400

function set_up() {
  set -e
  set -x
}

function clone_repo() {
  sudo rm -fR eric-enm-sles-base
  git clone ssh://$GERRIT_SERVER:$GERRIT_PORT/$GERRIT_PROJ && scp -p -P $GERRIT_PORT gerrit.ericsson.se:hooks/commit-msg eric-enm-sles-base/.git/hooks/
}

function update_file_content() {
  cd eric-enm-sles-base
  sed -i 's/OS_BASE_IMAGE_TAG=.*/OS_BASE_IMAGE_TAG='$IMAGE_TAG'/' Dockerfile
  sed -i 's/CBO_VERSION=.*/CBO_VERSION='$IMAGE_TAG'/' Dockerfile
  sed -i 's/image-base-os-version: .*/image-base-os-version: '$IMAGE_TAG'/' ruleset2.0.yaml
}

function git_add_cbos_changes() {
  git add ruleset2.0.yaml
  git add Dockerfile
}

function commit_change() {
  git commit -m "${CBO_TYPE} RELEASE. Update Common Base OS to ${IMAGE_TAG}"
}

function main() {
  set_up
  clone_repo
  update_file_content
  git_add_cbos_changes
  commit_change
  push_commit_for_review
  log_patchset_url
  wait_for_patchset_verification_and_abandon_gerrit_change
  if [[ $? == 1 ]]; then
    exit 1
  fi
  submit_and_verify_patchset_and_abandon_gerrit_change
  if [[ $? == 1 ]]; then
    exit 1
  fi
}

main
