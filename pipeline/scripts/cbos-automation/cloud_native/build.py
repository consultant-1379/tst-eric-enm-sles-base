import logging
import glob2
import re
import json
import cloud_native.actions.action_engine as action_executor
import uuid
from cloud_native.actions.actions import build_replace_action, build_docker_build_action

LOGGER = logging.getLogger(__name__)

FROM_LINE_EXTRACTOR_REGEX = r'^\s*([F|f][R|r][O|o][M|m])\s+\${\w+}\/\${\w+}:\${\w+}.*$'


def build_impact_chain(parent_dir, destination_file, base_images: [], excluded_repos=[]):
    impact_chain_list = []
    for base_image, prune_images in base_images:
        prune_images_split = prune_images.split(',')
        chain, _ = _build_image_impact_chain(parent_dir, base_image, prune_images_split, excluded_repos=excluded_repos)
        if chain:
            impact_chain_list.append(chain)
    return write_impact_chain_to_file(destination_file, impact_chain_list)


def write_impact_chain_to_file(destination_file, impact_chain_list):
    with open(destination_file, 'w') as actions_file:
        json.dump(impact_chain_list, actions_file, indent=4)
    return impact_chain_list


def build_all_actions_and_write_to_file(chain_file, docker_registry_url, image_repo_url, repo_path, tag,
                                        output_action_file=None, excluded_repos=[]):
    all_actions = []
    with open(chain_file, 'r') as chain_file:
        chain_list = json.load(chain_file)
    for chain in chain_list:
        actions = _build_actions(chain, docker_registry_url, image_repo_url, repo_path, tag, None,
                                 ['replace', 'docker_build'], excluded_repos)
        if actions and len(actions) > 0:
            all_actions.extend(actions)
    write_action_plan_to_file(all_actions, output_action_file)
    return all_actions


def write_action_plan_to_file(all_actions, output_action_file):
    if output_action_file:
        remove_base_image_from_chain(all_actions)
        with open(output_action_file, 'w') as action_plan:
            json.dump(all_actions, action_plan, indent=4)


def remove_base_image_from_chain(all_actions):
    # Remove the current version of the base image (eric-enm-sles-base) because it will already be built automatically
    # by the jenkins pipeline
    base_image = 0
    all_actions.pop(base_image)


def load_action_plan_and_execute_actions(actions_plan=None, actions_plan_file_path=None, number_of_retries=0,
                                         actions=['replace', 'docker_build', 'docker_pull', 'docker_tag',
                                                  'docker_push']):
    if not actions_plan or len(actions_plan) == 0:
        if not actions_plan_file_path:
            raise Exception('nether actions nor actions file provided')
        actions_plan = load_action_plan(actions_plan_file_path)
    try:
        _execute_actions_and_write_execution_report(actions_plan, actions, number_of_retries)
    except:
        LOGGER.info('Execution of actions plan has failed')


def load_action_plan(actions_plan_file_path):
    with open(actions_plan_file_path, 'r') as actions_plan_file:
        actions_plan = json.load(actions_plan_file)
    return actions_plan


def _build_image_impact_chain(parent_dir, image_name, prune_images, image_docker_file=None, excluded_repos=[]):
    LOGGER.info('Build impact chain of changing base image %s' % image_name)
    if not image_docker_file:
        try:
            image_docker_file = _get_image_from_docker_file(parent_dir, image_name)
        except Exception as e:
            LOGGER.warn('Failed to get Dockerfile for image %s , error %s' % (image_name, str(e)))
            excluded_repos.append(image_name)
            return None

    chain = {'image': image_name, 'Dockerfile': image_docker_file, 'impacted_chain': []}
    is_included = False
    if image_name in prune_images:
        is_included = True
        return chain, is_included
    all_impacted_images = _get_all_impacted_images(parent_dir, image_name)

    if all_impacted_images:
        for impacted_image, docker_file in all_impacted_images:
            sub_chain, child_included = _build_image_impact_chain(parent_dir, impacted_image, prune_images, docker_file,
                                                                  excluded_repos)
            if '*' in prune_images or 'ALL' in prune_images or 'all' in prune_images or child_included:
                chain['impacted_chain'].append(sub_chain)
                is_included = True

    return chain, is_included


def resolve_only_images_with_only_completed_actions(images_successfully_completed_action, images_with_failed_action):
    return images_successfully_completed_action - images_with_failed_action


def _execute_actions_and_write_execution_report(action_plan, actions_to_execute, number_of_retries):
    LOGGER.info('Start executing %d actions' % len(action_plan))
    images_successfully_completed_action = set([])
    images_with_failed_action = set([])
    for action_plan_item in action_plan:
        action_executor.execute(action_plan_item, actions_to_execute, images_successfully_completed_action,
                                images_with_failed_action,
                                number_of_retries=number_of_retries)

    images_successfully_completed_all_actions = resolve_only_images_with_only_completed_actions(
        images_successfully_completed_action, images_with_failed_action)
    generate_execution_report(images_successfully_completed_all_actions, images_with_failed_action)


def generate_execution_report(successfully_built_images, failed_built_images):
    write_report_to_file("workdir/successfully_built_images.txt", successfully_built_images)
    write_report_to_file("workdir/failed_images.txt", failed_built_images)


def write_report_to_file(file_name, build_images_report):
    with open(file_name, 'w') as output_report_file:
        for image_name in build_images_report:
            output_report_file.write("%s\n" % image_name)


def _get_base_images_from_chain(chain_list):
    base_images_list = []
    for chain in chain_list:
        base_images_list.append(chain.get('image'))
    return base_images_list


def _build_actions(chain_obj, docker_registry_url, image_repo_url, repo_path, tag, parent_image, action_types,
                   excluded_repos):
    actions = []
    image = chain_obj.get('image')
    impacted_chain = chain_obj.get('impacted_chain')
    action = {'id': uuid.uuid4().hex, 'target': chain_obj.get('Dockerfile')}
    action_details = []
    action['actions'] = action_details
    if 'replace' in action_types and parent_image:
        create_and_append_replace_action(action_details, chain_obj, docker_registry_url, image_repo_url, parent_image,
                                         repo_path, tag, image)
    if 'docker_build' in action_types and image not in excluded_repos:
        create_and_append_build_action(action_details, docker_registry_url, image, image_repo_url, repo_path, tag)

    actions.append(action)
    if len(impacted_chain) > 0:
        for imp_chain in impacted_chain:
            actions.extend(
                _build_actions(imp_chain, docker_registry_url, image_repo_url, repo_path, tag, image, action_types,
                               excluded_repos))
    return actions


def create_and_append_build_action(action_details, docker_registry_url, image, image_repo_url, repo_path, tag):
    action_details.append(build_docker_build_action(docker_registry_url, image_repo_url, repo_path, tag, image))


def create_and_append_replace_action(action_details, chain_obj, docker_registry_url, image_repo_url, parent_image,
                                     repo_path, tag, image):
    from_line = _match_in_file(chain_obj.get('Dockerfile'), FROM_LINE_EXTRACTOR_REGEX)
    as_part = ''
    if from_line and len(from_line) == 1:
        as_regex = r'\s+[A|a][S|s]\s+\w+$'
        as_part_matcher = re.search(as_regex, from_line[0])
        if as_part_matcher:
            as_part = as_part_matcher.group(0).strip()
    action_details.append(
        build_replace_action(docker_registry_url, image_repo_url, repo_path, tag, parent_image, image,
                             as_postfix=as_part))


def _docker_file_contains_single_image(search_result):
    return len(search_result) == 1


def _docker_file_contains_two_images(search_result):
    return len(search_result) == 2


def _docker_file_has_no_images(search_result):
    return len(search_result) == 0


def _get_image_from_docker_file(parent_dir, image_name):
    search_result = glob2.glob(parent_dir + '/**/' + image_name + '/Dockerfile')
    if _docker_file_contains_single_image(search_result):
        dockerfile_occurrence = 0
        return search_result[dockerfile_occurrence]
    elif _docker_file_contains_two_images(search_result):
        # assume the first dockerfile is the one to go for, works on tested versions
        dockerfile_occurrence = 1
        return search_result[dockerfile_occurrence]
    elif _docker_file_has_no_images(search_result):
        raise Exception('provided image name %s does not have Dockerfile' % image_name)
    else:
        error_messages = 'provided image name %s  has multiple Dockerfiles' % image_name
        error_messages.join('\n', search_result)
        raise Exception(error_messages)


def _get_all_impacted_images(parent_dir, image_name, excluded_repos=[]):
    all_docker_files = _get_all_docker_files(parent_dir, excluded_repos)
    impacted_mages = []
    for current_docker_file in all_docker_files:
        file_header = _get_docker_file_header(current_docker_file)
        if _check_if_image_is_based_from_another_image(file_header, image_name):
            name = _extract_image_name_from_docker_file_path(current_docker_file)
            if name:
                impacted_mages.append((name, current_docker_file))
                excluded_repos.append(name)
    return impacted_mages


def _get_docker_file_header(docker_file_path):
    with open(docker_file_path, 'r', encoding="utf8") as docker_file:
        file_header = ''
        for line in docker_file:
            file_header += line
            expression = FROM_LINE_EXTRACTOR_REGEX
            matched = re.search(expression, line)
            if matched:
                return file_header
            else:
                file_header += '\n'
    return file_header


def _extract_image_name_from_docker_file_path(docker_file_path):
    image = re.search('(?:\/)(eric-[^\/]*)(?:\/Dockerfile)', docker_file_path)
    if image is not None:
        return image.group(1)
    else:
        return None


def _check_if_image_is_based_from_another_image(file_header, image_name):
    return re.search('.*' + image_name + '(\s*\n|\s+#.*\n)', file_header) is not None


def _get_all_docker_files(parent_dir, excluded_repos=[]):
    return list([df for df in glob2.glob(parent_dir + '/**/Dockerfile') if not _is_excluded(df, excluded_repos)])


def _is_excluded(path, excluded_repos):
    for exclude in excluded_repos:
        if exclude in path:
            return True
    return False


def _match_in_file(file, regex):
    matches = []
    with open(file, 'r') as f:
        for line in f:
            for _ in re.finditer(regex, line):
                matches.append(line)
    return matches
