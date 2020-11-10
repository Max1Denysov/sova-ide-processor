import argparse
import random
import re
import traceback

import sqlalchemy as sa
from engine.preprocessors.arm1.dictionaries import _add_dict, process_raw_text
from engine.preprocessors.arm1.template import (extract_content_dicts,
                                                extract_include_dicts)
from nlab.rpc.client import WebClient

"""
Ожидаем на локальном порту 5810 Постгрес с армом.
"""


def _upload_dict(name, text, is_common, profile_ids, dictionary_rpc):

    try:
        have_dicts = dictionary_rpc.list(
            code=name,
        )
        if have_dicts["total"]:
            print("U", name)
            d = dictionary_rpc.update(
                id=have_dicts["items"][0]["id"],
                content=text,
                common=is_common,
                hidden=is_common,
                profile_ids=profile_ids if not is_common else []
            )
        else:
            print("C", name)
            d = dictionary_rpc.create(  # noqa
                code=name,
                content=text,
                common=is_common,
                hidden=is_common,
                profile_ids=profile_ids if not is_common else []
            )
    except KeyboardInterrupt:
        exit(-1)

    except Exception:
        print(traceback.format_exc())


def process_inf_dicts(*, inf_id, db, profile_ids, client, used_dicts=None):

    dictionary_rpc = client.component("dictionary")

    dicts = db.execute("""
        SELECT
            dict_id,
            lower(dict_name) AS dict_name,
            inf_id,
            dict_text
        FROM dicts
        WHERE inf_id=0 OR inf_id=%d
    """ % inf_id)
    fetch_dicts = dicts.fetchall()

    dict_content = {}
    dict_references = {}
    dict_infs = {}

    def add_dicts(dicts):
        for dict_id, dict_name, inf_id, dict_text in dicts:
            content = process_raw_text(dict_text)
            dict_content[dict_name] = content
            dict_infs[dict_name] = inf_id

            references = extract_include_dicts(dict_text)
            if references:
                dict_references[dict_name] = set(references)

    previous_missing_dicts = set()
    while True:
        add_dicts(fetch_dicts)

        add_used = set()

        for name in used_dicts:
            _add_dict(name, add_used, dict_references)

        used_dicts.update(add_used)

        missing_dicts = used_dicts - set(dict_content.keys())

        if missing_dicts == previous_missing_dicts:
            print("Can't resolve dicts: %s" % missing_dicts)
            # raise RuntimeError
            break

        print("Missing dicts:", missing_dicts)
        if not missing_dicts:
            break

        previous_missing_dicts = missing_dicts

        missing_dicts_str = "ARRAY['" + "','".join(missing_dicts) + "']"

        dicts = db.execute("""
           SELECT
               dict_id,
               lower(dict_name) AS dict_name,
               inf_id,
               dict_text
           FROM dicts
           WHERE dict_name = ANY(%s)
        """ % (missing_dicts_str,))
        fetch_dicts = dicts.fetchall()

    for dict_name, dict_text in dict_content.items():
        if used_dicts and dict_name not in used_dicts:
            continue

        is_common = dict_infs[dict_name] == 0
        set_profile_ids = [] if is_common else []

        _upload_dict(
            name=dict_name,
            text=dict_text,
            is_common=is_common,
            profile_ids=set_profile_ids,
            dictionary_rpc=dictionary_rpc,
        )


def replace_extend_answer(text, dumped_templates) -> (str, bool):
    result = text
    ext_answers = re.finditer(r'(\[\s*ExtendAnswer\s*\(\s*"(\d+)"\s*\)\s*\])',
                              text, flags=re.IGNORECASE | re.MULTILINE)

    missing = set()

    for m in ext_answers:
        old_template_id = int(m.group(2))
        if old_template_id in dumped_templates:
            result = result.replace(
                m.group(1), '[ExtendAnswer("%s")]' %
                            dumped_templates[old_template_id])
        else:
            missing.add(old_template_id)

    return result, missing


def process_inf(*, inf_id, name, code, complect_id, to_profile_id, incremental,
                db, client):
    complect_rpc = client.component("complect")
    profile_rpc = client.component("profile")
    suite_rpc = client.component("suite")
    template_rpc = client.component("template")

    # region профиль (получение или создание)
    if to_profile_id:
        profile = profile_rpc.fetch(id=to_profile_id)
        profile_id = to_profile_id
    else:
        profile = profile_rpc.create(name=name, code=code)
        profile_id = profile["id"]
    print(profile["name"], profile["code"], profile_id)
    # endregion

    # region комлект (получение или создание)
    if complect_id:
        complect = complect_rpc.fetch(id=complect_id)
    else:
        complect = complect_rpc.create(name="", profile_ids=[profile["id"]])
    print("Complect", complect["id"])
    # endregion

    # region запрос в старый АРМ (получение данных)
    templates = db.execute("""
        SELECT
            d.listing_id       as listing_id,
            d.id               as template_id,
            d.template_text    as template_text,
            n.listing_name     as listing_name,
            d.listing_position as listing_position,
            d.disable          as template_disable,
            n.disable          as listing_disable
        FROM infdllist i
        JOIN dlstorage d
            ON d.listing_id=i.listing_id
        JOIN listingnames n
            ON n.listing_id=i.listing_id
        WHERE inf_id=%(inf_id)s
    """, inf_id=inf_id).fetchall()
    # endregion

    # region
    suites_set = set(x[0] for x in templates)
    suites_data = {
        x["listing_id"]: {
            "title": x["listing_name"],
            "disable": x["listing_disable"],
        }
        for x in templates
    }
    # endregion

    # region
    dumped_suite_items = suite_rpc.list_all(profile_ids=[profile_id])
    dumped_suites = {
        suite["meta"].get("listing_id"): suite["id"]
        for suite in dumped_suite_items["items"]
    }
    if to_profile_id and len(dumped_suites) != len(dumped_suite_items["items"]):  # noqa
        raise RuntimeError("Can't recognize unique listing_ids in given db. "
                           "Try import profile from scratch not to profile_id")
    # endregion

    # region создание наборов
    suites = {}
    for suite_cnt, listing_id in enumerate(suites_set):
        # region вывод информации
        if suite_cnt % 100 == 99 or suite_cnt == len(suites_set) - 1:
            print("SUITES %d/%d" % (suite_cnt + 1, len(suites_set)))
        # endregion
        added_suite_id = dumped_suites.get(listing_id)
        if added_suite_id:
            suite = suite_rpc.update(
                id=added_suite_id,
                title=suites_data[listing_id]["title"],
                is_enabled=not suites_data[listing_id]["disable"],
                meta={
                    "listing_id": listing_id,
                },
            )
        else:
            suite = suite_rpc.create(
                profile_id=profile["id"],
                title=suites_data[listing_id]["title"],
                is_enabled=not suites_data[listing_id]["disable"],
                meta={
                    "listing_id": listing_id,
                },
            )
        suites[listing_id] = suite
    # endregion

    # region
    dumped_template_items = template_rpc.list_all(profile_ids=[profile_id])
    dumped_templates = {
        template["meta"].get("template_id"): template["id"]
        for template in dumped_template_items["items"]
    }
    # Ensure all templates have correct meta.template_id if updates profile
    if (to_profile_id and
            len(dumped_templates) != len(dumped_template_items["items"])):
        raise RuntimeError("Can't recognize unique template_id in given db. "
                           "Try import profile from scratch not to profile_id")
    # endregion

    delayed_update = []
    used_dicts = set()

    # region сохранение шаблонов
    for template_cnt, (listing_id, template_id, template_text, listing_name,
        template_position, template_disable, listing_disable) in \
            enumerate(templates):
        # region вывод
        if template_cnt % 100 == 99 or template_cnt == len(templates) - 1:
            print("TEMPLATES %d/%d" % (template_cnt + 1, len(templates)))
        # endregion

        suite_id = suites[listing_id]["id"]

        items = extract_content_dicts(template_text)
        if items:
            used_dicts.update(set(it.lower() for it in items))

        arm_text = process_raw_text(template_text)

        # Trying to replace ExtendAnswer old identifiers.
        # It's ok now if we can't replace something
        # We might not reach this template yet
        try:
            arm_text, missing = replace_extend_answer(
                arm_text, dumped_templates)

            if missing:
                # Look to the template in the end
                delayed_update.append((template_id, arm_text))
        except Exception:
            print("Missing", traceback.format_exc())

        if incremental and dumped_templates.get(template_id):
            continue

        added_template_id = dumped_templates.get(template_id)
        if added_template_id:
            template_rpc.update(
                id=added_template_id,
                content=arm_text,
                position=template_position,
                is_enabled=not template_disable,
                meta={
                    "title": str(template_id),
                    "template_id": template_id,
                }
            )
        else:
            template = template_rpc.create(
                suite_id=suite_id,
                content=arm_text,
                position=template_position,
                is_enabled=not template_disable,
                meta={
                    "title": str(template_id),
                    "template_id": template_id,
                }
            )
            dumped_templates[template_id] = template["id"]
    # endregion

    # region Return to missed templates
    for template_id, arm_text in delayed_update:
        arm_text, missing = replace_extend_answer(
            arm_text, dumped_templates)

        if missing:
            # Again it's not error if template is switched off
            print("Missing templates %s" % missing)

        template_rpc.update(
            id=dumped_templates[template_id],
            content=arm_text,
        )
    # endregion
    return profile["id"], used_dicts


def test_extract():
    assert extract_content_dicts("[dict(abc)]") == ["abc"]
    assert extract_content_dicts("\n\n[dict(abc)]\n") == ["abc"]
    assert extract_content_dicts("[dict(abc-zyw_weee)]") == ["abc-zyw_weee"]
    assert extract_content_dicts("[<dict(abc-zyw_weee)>]") == ["abc-zyw_weee"]
    assert extract_content_dicts("[<udict(abc-zyw_weee)>]") == ["abc-zyw_weee"]
    assert extract_content_dicts(
        "[<sudict(abc-zyw_weee)>]"
    ) == ["abc-zyw_weee"]


def test_includes():
    assert extract_include_dicts("xxx\n--include(Good_bye)\n") == ["good_bye"]

    assert extract_include_dicts(
        "--include(Geo_names_male)\n--include(word_names_male_uz)"
    ) == ["geo_names_male", "word_names_male_uz"]


def test_extend_answer():
    assert replace_extend_answer('[ExtendAnswer("123")]', {123: "abc"}) == (
           '[ExtendAnswer("abc")]', set())

    assert replace_extend_answer(' [ ExtendAnswer("123") ] '
                                 '[ExtendAnswer( "456" )] ',
                                  {123: "abc", 456: "def"}) == (
           ' [ExtendAnswer("abc")] [ExtendAnswer("def")] ', set())


def run_tests():
    test_extract()
    test_includes()
    test_extend_answer()


if __name__ == "__main__":
    run_tests()

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-n', '--name', required=False, help='Profile name')
    parser.add_argument('-c', '--code', required=True, help='Profile code')
    parser.add_argument('-i', '--inf-id', required=True, help='Inf id')
    parser.add_argument(
        '--profile-id',
        required=False,
        help='Update profile_id')
    parser.add_argument(
        '--complect-id',
        required=False,
        help='Attach to complect_id')

    help_arg = 'Db conn e.g. '
    help_arg += 'postgresql://chatbot:qwerty@localhost:5810/DLStorage'
    parser.add_argument('-d', '--db', required=True, help=help_arg)

    help_arg = 'Target ARM gateway host e.g. '
    help_arg += '"http://host.name.ai/template"'
    parser.add_argument('-t', '--target', required=True, help=help_arg)

    parser.add_argument('--incremental', required=False, action='store_true',
                        help="Do not update existed templates")

    args = parser.parse_args()

    db = sa.create_engine(args.db)

    client = WebClient(url=args.target)

    inf_id = int(args.inf_id)

    name = args.name
    if not name:
        name = "Тест: %d" % random.randrange(0, 10000)

    profile_id, used_dicts = process_inf(inf_id=inf_id,
                                         name=name,
                                         code=args.code,
                                         complect_id=args.complect_id,
                                         to_profile_id=args.profile_id,
                                         incremental=args.incremental,
                                         db=db,
                                         client=client)

    process_inf_dicts(inf_id=inf_id, db=db, profile_ids=[profile_id],
                      client=client, used_dicts=used_dicts)
