#!/usr/bin/env bash

POLLING_INTERVAL_SEC=10

function push_commit_for_review() {
  git log -1
  git push origin HEAD:refs/for/master
  COMMIT=$(git rev-parse HEAD)
}

function log_patchset_url() {
  patchset_url=$(ssh -p $GERRIT_PORT $GERRIT_SERVER gerrit query project:$GERRIT_PROJ $COMMIT | grep url | awk '{print $2}')
  echo "Patchset created: $patchset_url"
}

function wait_for_patchset_verification_and_abandon_gerrit_change() {
  status=$(ssh -p $GERRIT_PORT $GERRIT_SERVER gerrit query project:$GERRIT_PROJ commit:$COMMIT label:Verified=0 | grep status | awk '{print $2}')
  elapsed_time=0
  while [[ "$status" == "NEW" ]] && [[ "$elapsed_time" -lt "$PATCH_VERIFICATION_TIMEOUT_SEC" ]]; do
    echo "Waiting for Verified label..."
    sleep $POLLING_INTERVAL_SEC
    elapsed_time=$(($elapsed_time + $POLLING_INTERVAL_SEC))
    status=$(ssh -p $GERRIT_PORT $GERRIT_SERVER gerrit query project:$GERRIT_PROJ commit:$COMMIT label:Verified=0 | grep status | awk '{print $2}')
  done

  if [[ "$status" == "NEW" ]]; then
    echo "Timeout waiting for verification to complete"
    abandon_gerrit_change
    return 1
  fi
}

function submit_and_verify_patchset_and_abandon_gerrit_change() {
  verify_status=$(ssh -p $GERRIT_PORT $GERRIT_SERVER gerrit query project:$GERRIT_PROJ commit:$COMMIT label:Verified=1 | grep status | awk '{print $2}')
  if [[ "$verify_status" == "NEW" ]]; then
    echo "Verification Passed"
    abandon_gerrit_change
  else
    echo "Verification on patchset failed"
    abandon_gerrit_change
    return 1
  fi

}

function abandon_gerrit_change() {
  echo "Abandoning patchset: $patchset_url"
  ssh -p $GERRIT_PORT $GERRIT_SERVER gerrit review -p $GERRIT_PROJ --abandon $COMMIT
}
