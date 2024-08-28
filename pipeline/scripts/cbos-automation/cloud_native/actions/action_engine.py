import logging
from cloud_native.actions.actions import create_new_action

LOGGER = logging.getLogger(__name__)


def execute(action_plan_item, actions_to_execute, successful_actions, failed_actions, number_of_retries=0):
    LOGGER.debug('Start executing action [%s] from action plan [%s]' % (str(actions_to_execute), str(action_plan_item)))
    target = action_plan_item.get('target')
    image_name = _get_image_name_from_action_plan_item(action_plan_item)
    for action in action_plan_item.get('actions'):
        action_type = action.get('type')
        if action_type not in actions_to_execute:
            LOGGER.info(
                'action type %s is not among list of action to execute %s' % (action_type, str(actions_to_execute)))
            continue
        execution_count = 0
        executed_successfully = False
        retry_limit_reached = False
        while not executed_successfully and not retry_limit_reached:
            try:
                execution_count += 1
                action_obj = create_new_action(target, action)
                LOGGER.info('======== executing action %s ========' % action_obj)
                action_obj.execute()
                executed_successfully = True
                if action_type == "docker_build":
                    successful_actions.add(image_name)
            except Exception as action_exception:
                if execution_count > number_of_retries:
                    retry_limit_reached = True
                    LOGGER.warn('error while applying action %s on target %s for error %s' % (
                        str(action_obj), target, str(action_exception)))
                    failed_actions.add(image_name)


def _get_image_name_from_action_plan_item(action_plan_item):
    replace_action_element_index = 0
    image_name = action_plan_item.get('actions')[replace_action_element_index].get('config').get('image_name')
    return image_name
