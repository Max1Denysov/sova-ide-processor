import argparse
from pathlib import Path

from engine.preprocessors.arm1.dictionaries import process_raw_text
from nlab.rpc.client import WebClient


def import_data(*, profile_name, client, suites_path: Path):
    suite_rpc = client.component("suite")
    template_rpc = client.component("template")

    profile_rpc = client.component("profile")
    profiles = profile_rpc.list()

    profile_id = None
    for profile in profiles['items']:
        if profile['name'] == profile_name:
            profile_id = profile['id']
            break

    if profile_id is None:
        raise Exception("Profile with the name '{profile_name}' not found!")

    profile_suites = suite_rpc.list_all(profile_ids=profile_id)

    profile_suites_title_ids = {suite["title"]: suite["id"]
                                for suite in profile_suites['items']}

    suite_files = suites_path.glob("*")
    for suite_file in suite_files:
        suite_title = suite_file.with_suffix("").name

        if profile_suites_title_ids.get(suite_title):
            #
            # Remove whole suite with previous version
            #
            suite_rpc.remove(
                id=profile_suites_title_ids[suite_title],
            )

        suite = suite_rpc.create(
            profile_id=profile_id,
            title=suite_title,
            is_enabled=True,
        )

        print(suite_title, suite["id"])

        with open(suite_file) as f:
            data = f.read()

        # print(data)
        templates_raw = [item.strip() for item in data.split("\n\n\n")
                         if item.strip()]

        for templates_counter, template_raw in enumerate(templates_raw):
            arm_text = process_raw_text(template_raw)

            print(template_raw)
            print("--------")

            template_rpc.create(
                suite_id=suite["id"],
                content=arm_text,
                position=templates_counter,
                is_enabled=True,
                meta={
                    "title": str(templates_counter),
                    "template_id": templates_counter,
                }
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('path', type=Path, help='Path')
    parser.add_argument('--profile-name', required=True, help='Profile name')

    help_arg = 'Target ARM gateway host e.g. '
    help_arg += '"https://host.name.ai/"'
    parser.add_argument('-t', '--target', required=True, help=help_arg)

    args = parser.parse_args()

    client = WebClient(url=args.target)

    import_data(profile_name=args.profile_name, client=client,
                suites_path=args.path)
