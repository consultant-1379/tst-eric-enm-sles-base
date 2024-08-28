import argparse
import logging.config
from cloud_native import build

logging.config.fileConfig(fname='LOGGING.conf', disable_existing_loggers=False)
LOGGER = logging.getLogger(__name__)


def main():
    args = build_arg_parser()
    resolve_cn_action_args_and_execute(args)
    print(args)


def resolve_cn_action_args_and_execute(args):
    if args.command == 'CHAIN':
        build.build_impact_chain(args.d, args.o, args.i, excluded_repos=args.exclude)
    elif args.command == 'BUILD_ACTIONS':
        build.build_all_actions_and_write_to_file(args.c, args.docker_registry_url, args.repo, args.repo_path, args.tag,
                                                  output_action_file=args.o, excluded_repos=args.exclude)
    elif args.command == 'EXEC_ACTIONS':
        build.load_action_plan_and_execute_actions(actions_plan_file_path=args.s, number_of_retries=args.m,
                                                   actions=args.selected_action)


def build_chain_action_parameters(main_parser, parent_parsers):
    parser_base_image_impact = main_parser.add_parser('CHAIN', help='Get impact chain for base images',
                                                      conflict_handler='resolve', usage='%(prog)s [options]',
                                                      parents=parent_parsers)

    parser_base_image_impact.add_argument('-o', required=True, type=str, metavar='output_file',
                                          help='Output file for impact chain')

    parser_base_image_impact.add_argument('-i', required=True, action='append', nargs=2,
                                          metavar='base_image leaf_images',
                                          help='set of base image(s) name followed by comma separated '
                                               'with a leaf image(s) to stop at. '
                                               'leaf images to stop at or * for all child images'
                                               'example -i base_image ch_img1,ch_image2,... \n or -i base_image *')


def build_build_actions_action_parameters(main_parser, parent_parsers):
    parser_base_image_action = main_parser.add_parser('BUILD_ACTIONS', help='build actions plan for Dockerfiles',
                                                      conflict_handler='resolve', usage='%(prog)s [options]',
                                                      parents=parent_parsers)
    parser_base_image_action.add_argument('-c', required=True, type=str, metavar='chain_file',
                                          help='input file for impact chain')
    parser_base_image_action.add_argument('--docker-registry-url', type=str, metavar=' docker_registry_url',
                                          default='armdocker.rnd.ericsson.se', help='docker registry url')
    parser_base_image_action.add_argument('--repo', type=str, metavar='repo',
                                          help='new repository value, provide the old one if you do not want to '
                                               'change it ')
    parser_base_image_action.add_argument('--repo-path', type=str, metavar='repo_path',
                                          help='new repo path value, provide the old one if you do not want to change '
                                               'it ')
    parser_base_image_action.add_argument('--tag', required=True, type=str, metavar='image_tag',
                                          help='new image tag value, provide the old one if you do not want to change '
                                               'it')
    parser_base_image_action.add_argument('-o', required=True, type=str, metavar='destination_file',
                                          help='destination file to create action plan')

    parser_base_image_action.add_argument('--exclude', nargs='+', metavar='repo_name', default=[],
                                          help='repo names to be excluded')


def build_exec_actions_action_parameters(main_parser, parent_parsers):
    parser_base_image_action_execute = main_parser.add_parser('EXEC_ACTIONS', help='Execute actions from json file',
                                                              conflict_handler='resolve', usage='%(prog)s [options]',
                                                              parents=parent_parsers)
    parser_base_image_action_execute.add_argument('-s', required=True, type=str, metavar='source_file',
                                                  help='file to read action plan from')
    parser_base_image_action_execute.add_argument('-m', required=False, type=int, default=0, metavar='count',
                                                  help='Number of retries for failed actions, the default is zero')


def build_arg_parser():
    prepare_parent_parser = argparse.ArgumentParser(conflict_handler='resolve', add_help=True)

    prepare_parent_parser.add_argument('-d', required=True, type=str, metavar='dir_path', help='working directory path')

    prepare_parent_parser.add_argument('--exclude', nargs='+', metavar='repo_name', default=[],
                                       help='repo names to be excluded')

    parser = argparse.ArgumentParser(description='cENM Build utility', conflict_handler='resolve', add_help=True)
    subparsers = parser.add_subparsers(dest="command", help='Action to be performed')

    build_chain_action_parameters(subparsers, [prepare_parent_parser])

    action_parent_parser = argparse.ArgumentParser(conflict_handler='resolve', add_help=True)

    action_parent_parser.add_argument('--selected-action', nargs='+',
                                      default=['replace', 'docker_build', 'docker_pull', 'docker_tag', 'docker_push'],
                                      choices=['replace', 'docker_build', 'docker_pull', 'docker_tag', 'docker_push'],
                                      help='select actions to execute from action plan')

    build_build_actions_action_parameters(subparsers, [action_parent_parser])
    build_exec_actions_action_parameters(subparsers, [action_parent_parser])

    args = parser.parse_args()
    LOGGER.info(args)
    return args


if __name__ == "__main__":
    main()
