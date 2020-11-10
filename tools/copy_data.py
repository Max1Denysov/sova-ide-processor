import argparse

from nlab.rpc.client import WebClient

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('profile_id', help='Profile id')
    URL_ARM = 'http://is-dev.aa/template'
    parser.add_argument(
        '-s', '--source',
        required=True,
        help='Source gateway host e.g. "%s"' % URL_ARM
    )
    parser.add_argument(
        '-t', '--target',
        required=True,
        help='Target gateway host e.g. "%s"' % URL_ARM
    )

    args = parser.parse_args()

    source = WebClient(url=args.source)
    target = WebClient(url=args.target)

    s_profiles = source.component("profile")
    s_suites = source.component("suite")
    s_templates = source.component("template")
    s_dictionaries = source.component("dictionary")

    t_profiles = target.component("profile")
    t_suites = target.component("suite")
    t_templates = target.component("template")
    t_dictionaries = target.component("dictionary")

    source_profile_ids = [args.profile_id]

    for dictionary in s_dictionaries.list_all(_with_content=True)["items"]:
        create_dictionary = dict(dictionary)
        del create_dictionary["id"]
        del create_dictionary["updated"]
        have_dicts = t_dictionaries.list(
            code=dictionary["code"],
        )
        if have_dicts["total"]:
            print("U", dictionary["code"])
            d = t_dictionaries.update(
                id=have_dicts["items"][0]["id"],
                content=dictionary["content"],
                common=dictionary["common"],
                hidden=dictionary["hidden"],
            )
        else:
            print("C", dictionary["code"])
            d = t_dictionaries.create(
                code=dictionary["code"],
                content=dictionary["content"],
                common=dictionary["common"],
                hidden=dictionary["hidden"],
            )

    for source_profile_id in source_profile_ids:
        profile = s_profiles.fetch(id=source_profile_id)

        source_suites = s_suites.list_all(profile_ids=[profile["id"]])

        create_profile = dict(profile)
        del create_profile["id"]
        del create_profile["engine_id"]
        target_profile = t_profiles.create(**create_profile)

        print(target_profile["id"])

        print("SUITE 0/%d" % len(source_suites["items"]))
        for source_cnt, source_suite in enumerate(source_suites["items"]):
            if source_cnt % 100 == 99 or source_cnt == len(source_suites["items"]) - 1:  # noqa
                print(
                    "SUITE %d/%d" % (
                        source_cnt + 1, len(source_suites["items"])
                    )
                )

            create_suite = dict(source_suite)
            create_suite["profile_id"] = target_profile["id"]
            del create_suite["id"]
            del create_suite["updated"]
            del create_suite["hidden"]
            del create_suite["stat"]
            target_suite = t_suites.create(**create_suite)

            source_templates = s_templates.list_all(
                suite_id=source_suite["id"]
            )

            for source_template in source_templates["items"]:
                source_template["suite_id"] = target_suite["id"]

                create_template = dict(source_template)
                del create_template["id"]
                del create_template["updated"]
                del create_template["state"]
                del create_template["profile_id"]
                del create_template["stats"]
                del create_template["suite_title"]
                del create_template["template_title"]
                del create_template["created"]
                t_templates.create(**create_template)
