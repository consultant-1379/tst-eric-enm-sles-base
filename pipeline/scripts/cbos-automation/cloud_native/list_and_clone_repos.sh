#!/bin/bash

source ./../gerrit_server_info

gerrit_user_name=$1
gerrit_key_file=$2
checkout_directory=$3
current_dir=$(pwd)

list_of_repos_to_clone_file_name="list_of_repos_to_clone.txt"
cloned_repos_success_file_name="cloned_repos_success.txt"
cloned_repos_failure_file_name="cloned_repos_failure.txt"

declare -a repo_name_prefixes=("OSS/com.ericsson.oss.containerisation"
  "OSS/ENM-Parent/SQ-Gate/com.ericsson.oss.containerisation"
  "OSS/com.ericsson.oss.itpf.security"
  "OSS/com.ericsson.oss.itpf.modeling")

# Excluding fmx because it was not included in the E2E build and kept failing,
# Will be updated to get a list of repos to exclude that are not in the E2E build.
declare -a repos_to_exclude=("fmx")

total_repos_to_clone_count="0"
cloned_repos_success_count="0"
cloned_repos_failure_count="0"

REMOTE_DESKTOP_GERRIT_PROJ="OSS/ENM-Parent/SQ-Gate/com.ericsson.oss.containerisation/eric-enmsg-remotedesktop"

function create_list_of_repos_to_clone() {
  ssh -i $gerrit_key_file -p $GERRIT_PORT $gerrit_user_name@$GERRIT_MIRROR_SERVER gerrit ls-projects --prefix="$1" | grep "/eric-" | grep -v "test" >>$list_of_repos_to_clone_file_name
}

function remove_repos_with_pattern_from_list() {
  for repos_to_exclude in "${repos_to_exclude[@]}"; do
    sed -i "/${repos_to_exclude}/d" $list_of_repos_to_clone_file_name
  done
}

function clone_repositories() {

  remove_repos_with_pattern_from_list
  total_repos_to_clone_count=$(cat $list_of_repos_to_clone_file_name | wc -l)

  if [ "$total_repos_to_clone_count" -gt "0" ]; then
    while read repo; do
      echo "Cloning repository: $repo"

      if [[ "$repo" == *"eric-enmsg-remotedesktop"* ]]; then
        git clone ssh://$GERRIT_SERVER:$GERRIT_PORT/$REMOTE_DESKTOP_GERRIT_PROJ && scp -p -P $GERRIT_PORT $GERRIT_SERVER:hooks/commit-msg eric-enmsg-remotedesktop/.git/hooks/
      else
        git clone -v --branch=master ssh://$gerrit_user_name@$GERRIT_MIRROR_SERVER:$GERRIT_PORT/$repo
      fi
      if [ "$?" == "0" ]; then
        echo "$repo" >>$cloned_repos_success_file_name
        echo "Repository successfully cloned: $repo"
      else
        echo "$repo" >>$cloned_repos_failure_file_name
        echo "Error while cloning repo: $repo"
      fi
    done <$list_of_repos_to_clone_file_name

    cloned_repos_success_count=$(cat $cloned_repos_success_file_name | wc -l)
    cloned_repos_failure_count=$(cat $cloned_repos_failure_file_name | wc -l)
  else
    echo "The list of repositories to clone might be empty. Skipping cloning of repositories."
  fi
}

function print_clone_operation_summary() {
  echo ""
  echo "++++++++++++++++++++++++"
  echo "++ Repo clone summary ++"
  echo "++++++++++++++++++++++++"

  echo "Total repositories to clone: $total_repos_to_clone_count"
  echo "Total repositories cloned successfully: $cloned_repos_success_count"
  echo "Total repositories that could not be cloned: $cloned_repos_failure_count"
  echo "-------------------------------------------"

  if [ -f $cloned_repos_success_file_name ]; then
    echo ""
    echo "Detail or repositories cloned successfully:"
    echo "-------------------------------------------"
    cat $cloned_repos_success_file_name
  fi

  if [ -f $cloned_repos_failure_file_name ]; then
    echo ""
    echo "Detail or repositories that could not be cloned:"
    echo "------------------------------------------------"
    cat $cloned_repos_failure_file_name
  fi

}

function main() {
  mkdir -p $checkout_directory
  cd $checkout_directory

  for repo_name_prefix in "${repo_name_prefixes[@]}"; do
    create_list_of_repos_to_clone $repo_name_prefix
  done

  clone_repositories
  print_clone_operation_summary
}

main
