import re
from abc import abstractmethod
import docker
import os
import sys
import json
import logging
import uuid

LOGGER = logging.getLogger(__name__)


def __build_action():
    action_detail = {'id': uuid.uuid4().hex, 'type': None, 'config': {}, 'failure_strategy': {}}
    return action_detail


def build_replace_action(docker_registry_url, image_repo_url, repo_path, tag, parent_image, image, as_postfix=''):
    action_detail = __build_action()
    action_detail['type'] = 'replace'
    action_detail['config']['regex_match'] = {'regex': r"^\s*([F|f][R|r][O|o][M|m])\s+\${\w+}\/\${\w+}:\${\w+}.*$"}
    action_detail['config']['replace_string'] = r"FROM %s/%s:%s %s" % \
                                                (docker_registry_url,
                                                 _concatenate_parameters_separated_by_slashes(
                                                     repo_path, image_repo_url, parent_image), tag, as_postfix)
    action_detail['config']['image_name'] = image
    action_detail['failure_strategy'] = {'strategy': 'report_continue'}
    return action_detail


def build_docker_build_action(docker_registry_url, image_repo_url, repo_path, tag, image_name):
    action_detail = __build_action()
    action_detail['type'] = 'docker_build'
    action_detail['config']['build_info'] = {'docker_registry': docker_registry_url, 'repo': image_repo_url,
                                             'repo_path': repo_path, 'tag': tag, 'image_name': image_name}
    action_detail['failure_strategy'] = {'strategy': 'report_continue'}
    return action_detail


class Action:

    def __init__(self, target, failure_strategy):
        self.failure_strategy = failure_strategy
        self.target = target

    @abstractmethod
    def execute(self, **kwargs):
        pass

    def __str__(self):
        self_level_dict = dict([(k, getattr(self, k)) \
                                for k in dir(self) if '_' not in k])
        return str(self_level_dict)


class ReplaceAction(Action):

    def __init__(self, target, action_config, failure_strategy):
        super().__init__(target, failure_strategy)
        self.replacement = action_config.get('replace_string')
        self.regex = action_config['regex_match']['regex']

    def execute(self):
        matcher = RegexMatcher(self.regex)
        with open(self.target, 'r') as file:
            count, new_str = self._replace_marched_values(file, matcher)
        if count > 0:
            with open(self.target, 'w') as file:
                self._write_to_file(file, new_str)

    def _replace_marched_values(self, file, matcher):
        new_str, count = matcher.apply(string_to_match=file.read(), replace=self.replacement)
        return count, new_str

    def _write_to_file(self, file, new_str):
        file.write(new_str)


class BuildDockerImageAction(Action):

    def __init__(self, target, action_config, failure_strategy):
        super().__init__(target, failure_strategy)
        self.docker_registry = action_config['build_info']['docker_registry']
        self.repo = action_config['build_info']['repo']
        self.repo_path = action_config['build_info']['repo_path']
        self.tag = action_config['build_info']['tag']
        self.image_name = action_config['build_info']['image_name']

    def execute(self, **kwargs):
        docker_api = docker.APIClient()
        image_tag = '%s/%s:%s' % (
            self.docker_registry, _concatenate_parameters_separated_by_slashes(self.repo_path, self.repo,
                                                                               self.image_name), self.tag)
        head, _ = os.path.split(self.target)
        self.log_and_build_docker_image(docker_api, head, image_tag)
        self.log_and_push_docker_image(docker_api, image_tag)

    def log_and_build_docker_image(self, docker_api, head, image_tag):
        LOGGER.info('Start building docker image %s' % image_tag)
        for line in docker_api.build(path=head, tag=image_tag, nocache=True):
            process_docker_api_line(line)

    def log_and_push_docker_image(self, docker_api, image_tag):
        LOGGER.info('Start pushing docker image %s' % image_tag)
        for line in docker_api.push(image_tag, stream=True, decode=True):
            print(line)


def create_new_action(target, action_str):
    action_type = action_str.get('type')

    if action_type == 'replace':
        return ReplaceAction(target, action_str.get('config'), action_str.get('failure_strategy'))
    elif action_type == 'docker_build':
        return BuildDockerImageAction(target, action_str.get('config'), action_str.get('failure_strategy'))
    else:
        raise Exception('could not build Action from action details %s' % str(action_str))


class RegexMatcher:

    def __init__(self, regex):
        self.regex = regex

    def apply(self, string_to_match='', replace=''):
        if len(replace) > 0:
            matcher = re.search(self.regex, string_to_match, flags=re.MULTILINE)
            if not matcher:
                return string_to_match, 0
            matched_str = matcher.group()
            replace_with = '\n## ' + matched_str.strip() + '\n' + replace
            return re.subn(self.regex, replace_with, string_to_match, flags=re.MULTILINE)

        return re.search(self.regex, string_to_match, flags=re.MULTILINE)


def process_docker_api_line(payload):
    """ Process the output from API stream, throw an Exception if there is an error """
    if not payload:
        return None
    payload_str = payload.decode('utf-8')
    for segment in payload_str.split('\n'):
        line = segment.strip(" '\r\n")
        if line:
            try:
                line_payload = json.loads(line)
            except ValueError as ex:
                print("Could not decipher payload from API: " + str(ex))
                continue
            if line_payload:
                if "errorDetail" in line_payload:
                    error = line_payload["errorDetail"]
                    sys.stderr.write(error["message"])
                    raise RuntimeError("Error on build - code " + error["code"])
                elif "stream" in line_payload:
                    sys.stdout.write(line_payload["stream"])


def _concatenate_parameters_separated_by_slashes(*args):
    final_str = ''
    for val in args:
        if val is None or len(val) == 0:
            continue
        if len(final_str) == 0:
            final_str += val
        else:
            final_str += '/' + val
    return final_str
