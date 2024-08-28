#!/usr/bin/env bash

source ./../gerrit_server_info
source ./../trigger_and_verify_gerrit_change.sh

current_dir=$(pwd)
GERRIT_PROJ="OSS/ENM-Parent/SQ-Gate/com.ericsson.oss.containerisation/eric-enmsg-remotedesktop"
PATCH_VERIFICATION_TIMEOUT_SEC=2000

function update_jenkins_file_pre_commit_with_new_cbos_image_tag() {
  cd workdir/cloud_native_repos/eric-enmsg-remotedesktop
  sed -i 's/env.IMAGE_TAG = sh(script: "cat .bob\/var.version", returnStdout: true).trim()/env.IMAGE_TAG = sh(script: "echo '$IMAGE_TAG'", returnStdout: true).trim()/g' JenkinsfilePreCommit
}

function git_add_remotedesktop_changes() {
  git add JenkinsfilePreCommit
  git add Dockerfile
}

commit_change() {
  git commit -m "NO-JIRA: Updating to latest CBOS version"
}

function main() {
  update_jenkins_file_pre_commit_with_new_cbos_image_tag
  git_add_remotedesktop_changes
  commit_change
  push_commit_for_review
  log_patchset_url
  wait_for_patchset_verification_and_abandon_gerrit_change
  submit_and_verify_patchset_and_abandon_gerrit_change
  if [[ $? == 0 ]]; then
    echo "eric-enmsg-remotedesktop" >>$current_dir/workdir/successfully_built_images.txt
  else
    echo "eric-enmsg-remotedesktop" >>$current_dir/workdir/failed_images.txt
  fi
}

main
