from pathlib import Path

from engine.preprocessors.arm1.template import _process_name


class VarsExport:
    """
    Add vars templates exporting
    """
    def __init__(self, base_path):
        self.base_path: Path = base_path

        self.vars = {}

    def add_var(self, name, value):
        self.vars[name] = value

    def add_vars(self, names, value):
        self.vars.update(dict.fromkeys(names, value))

    def export(self):
        """
        Write all vars to file
        :return:
        """
        with open(self.base_path / "defvars.lst", "a") as export_f:
            for varname, value in self.vars.items():
                # Add \n first to php processor export compability
                export_f.write("\n%s\t%s" % (_process_name(varname), value))
