import sys


def main():
    successful_report_file = sys.argv[1]
    failure_report_file = sys.argv[2]

    failed_builds, successful_builds = extract_build_report_data(successful_report_file, failure_report_file)
    print_report_results(failed_builds, successful_builds)


def extract_build_report_data(successful_report, failure_report):
    successful_images_built = extract_list_of_images_from_build_report(successful_report)
    failed_images = extract_list_of_images_from_build_report(failure_report)

    return failed_images, successful_images_built


def extract_list_of_images_from_build_report(file_name):
    with open(file_name) as build_results_file:
        images = []
        for image_name in build_results_file:
            images.append(image_name.rstrip("\n"))
    return images


def print_images_from_report(report_type, images):
    print("+++++++++++++++++++++++++++++++++++++++")
    print("        %s Image(s):         " % report_type)
    print("+++++++++++++++++++++++++++++++++++++++")
    for image in sorted(images):
        print(image)
    print("+++++++++++++++++++++++++++++++++++++++")


def print_report_results(failed_images, successful_builds):
    total_number_of_builds = len(successful_builds) + len(failed_images)
    print_successful_image_build_report(successful_builds, total_number_of_builds)
    print_failed_image_build_report(failed_images)


def print_failed_image_build_report(failed_images):
    number_of_failed_builds = len(failed_images)

    if number_of_failed_builds > 0:
        print_images_from_report("Failed", failed_images)
        print('Failed to build %d image(s)' % number_of_failed_builds)
        raise Exception('Image(s) Failed to build!')


def print_successful_image_build_report(successful_build_images, total_number_of_builds):
    number_of_successful_builds = len(successful_build_images)
    print_images_from_report("Successful", successful_build_images)
    print('Successfully built %d/%d Image(s)' % (number_of_successful_builds, total_number_of_builds))


if __name__ == "__main__":
    main()
