import html
import logging
from pathlib import Path

from engine.preprocessors.arm1.template import extract_include_dicts, \
    process_dictionary_name, transform_template_text


logger = logging.getLogger(__name__)


def process_raw_text(text):
    """
    Process text from database frontend representation to more ready for engine
    :param text:
    :return:
    """
    lines = [html.escape(d, quote=False) for d in text.split("\n")]
    return "<div>" + ("</div><div>".join(lines)) + "</div>"


def _add_dict(name: str, add_used: set, dict_references: dict):
    """
    Depth-first adding of dicts by references in `dict_references`
    to `add_used`
    :param name:
    :param add_used:
    :param dict_references:
    :return:
    """
    refs = dict_references.get(name, [])
    add_used.add(name)
    for ref in refs:
        if ref not in add_used:
            _add_dict(ref, add_used, dict_references)


class DictionariesList:
    """

    """
    def __init__(self, *, base_path):

        self.base_path: Path = base_path
        self.filename: Path = base_path / "dict.lst"
        self.dicts = {}

    def add(self, *, name, filename):

        self.dicts[name] = filename

    def __contains__(self, code):

        return code in self.dicts

    def export(self, *, common_dicts: bool, used_dicts, dictionary_rpc):

        logger.info("Export dicts: %s", used_dicts)
        self._export_used_dicts(
            common_dicts=common_dicts,
            used_dicts=used_dicts,
            dictionary_rpc=dictionary_rpc
        )

        logger.info("All dictionaries downloaded")
        logger.debug("Dict list: %s", self.dicts)

        with open(self.filename, "w") as dict_f:
            for name, file in self.dicts.items():
                dict_f.write("{name}={file}\n".format(name=name, file=file))

    def export_dictionary(self, *, base_path, path, code, text):

        if code in self.dicts:
            return

        good_code = process_dictionary_name(code)
        add_filename = Path(path) / (good_code + ".txt")
        dict_filename = base_path / add_filename
        with open(dict_filename, "w") as f:
            # FIXME трансформация текста в 230 раз медленнее записи файла
            # Если не будет вызова transform_template_text(text) (например,
            # в БД хранить уже трансформированный текст, то общая компиляция
            # словарей ускорится, примерно, в 2 раза)
            f.write(transform_template_text(text))

        self.add(name=good_code, filename=add_filename)

    def _export_used_dicts(self, *, common_dicts: bool,
                           used_dicts: set, dictionary_rpc):

        if not common_dicts:  # ???
            return

        used_dicts_path = self.base_path / "common_dicts"

        used_dicts_path.mkdir(exist_ok=True)

        logger.info("Start of reading all dictionaries from DB...")
        all_dictionaries = dictionary_rpc.list_all(_with_content=True)
        logger.info(
            "...all dictionaries are read (%s)." % len(
                all_dictionaries["items"]
            )
        )

        # code словарей, которые еще не записаны
        unsaved = used_dicts

        # code словарей, которые уже записаны
        saved = set()

        # Приватные словари (с ключем по code)
        private_dictionaries = {}

        logger.info("Start of save common dictionaries...")
        for dictionary in all_dictionaries["items"]:

            try:
                code = dictionary["code"]

                if code in saved:
                    continue

                if dictionary["common"]:
                    self._dictionary_export_process(
                        base_path=self.base_path, path="common_dicts",
                        code=code, text=dictionary["content"],
                        saved=saved, unsaved=unsaved
                    )
                else:
                    private_dictionaries[code] = dictionary

            except Exception as error:
                logger.info('Error: "%s".' % str(error))
                logger.info('...error has been ignored.')
                pass

        logger.info("...the common dictionaries have been saved.")

        del all_dictionaries

        logger.info("Start of save private dictionaries...")
        while unsaved:

            try:
                code = unsaved.pop()

                if code in saved:
                    continue

                dictionary = private_dictionaries.get(code)

                if dictionary is None:
                    logger.info(
                        f'Dictionary "{code}" does not exist in the DB.'
                    )
                    continue

                self._dictionary_export_process(
                    base_path=self.base_path, path="common_dicts",
                    code=code, text=dictionary["content"],
                    saved=saved, unsaved=unsaved
                )

            except Exception as error:
                logger.info('Error: "%s".' % str(error))
                logger.info('...error has been ignored.')
                pass

        logger.info("...the private dictionaries have been saved.")

    def _dictionary_export_process(self, base_path: Path, path: Path,
                                   code: str, text: str,
                                   saved: set, unsaved: set) -> None:
        """
            Процесс экспорта словаря
        """
        # Обновим множество, которое содержит code НЕзаписанных словарей,
        # ссылками на словари из контента записываемого словаря
        unsaved.update(extract_include_dicts(process_raw_text(text)))

        # Запишем файл со словарем
        self.export_dictionary(
            base_path=base_path, path=path, code=code, text=text,
        )

        # Обновим множество которое содержит code Записанных словарей
        saved.update([code])
