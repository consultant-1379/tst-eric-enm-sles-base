def environment_set_up()
{
    sh "sudo install pip python3 -m pip --version"
    sh "sudo python3 -m pip install pipenv"
    sh "sudo python3 -m pipenv install --python /usr/bin/python3"
    clean_up_environment()
    sh "mkdir workdir"
}

def clone_cloud_native_repos()
{
    withCredentials([sshUserPrivateKey(credentialsId: 'lciadm100_private_key', usernameVariable: 'LCIADMN100_USER_NAME',
    keyFileVariable: 'LCIADMN100_KEY_FILE')]) {
        sh "./cloud_native/list_and_clone_repos.sh $LCIADMN100_USER_NAME $LCIADMN100_KEY_FILE workdir/cloud_native_repos"
    }
}

def build_impact_chain_and_action_plan()
{
    sh "sudo python3 -m pipenv run python3 cbos_automation.py CHAIN -d workdir/cloud_native_repos -o workdir/impact-chain.json -i eric-enm-sles-base \\*"
    sh "sudo python3 -m pipenv run python3 cbos_automation.py BUILD_ACTIONS -o workdir/action-plan.json -c workdir/impact-chain.json --repo-path proj_oss_releases --tag ${IMAGE_TAG} --exclude eric-enmsg-remotedesktop"
}

def prune_images()
{
    sh "df -h"
    sh "sudo docker image prune --all --force"
    sh "df -h"
}

def build_and_push_docker_images_and_generate_report()
{
    sh "sudo python3 -m pipenv run python3 cbos_automation.py EXEC_ACTIONS -s workdir/action-plan.json"
    sh "sudo chmod 777 workdir/successfully_built_images.txt"
    sh "sudo chmod 777 workdir/failed_images.txt"
}

def build_and_push_docker_images_for_remotedesktop()
{
    withCredentials([sshUserPrivateKey(credentialsId: 'lciadm100_private_key',
    usernameVariable: 'LCIADMN100_USER_NAME', keyFileVariable: 'LCIADMN100_KEY_FILE')]) {
        sh "./cloud_native/trigger_remotedesktop_build_and_push.sh"
    }
}

def print_build_report()
{
    sh "sudo python3 -m pipenv run python3 cloud_native/print_image_report.py workdir/successfully_built_images.txt workdir/failed_images.txt"
}

def clean_up_environment()
{
    sh "rm -fR workdir"
    sh "sudo rm -fR Pipfile.lock"
}

return this