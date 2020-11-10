from scripts import compiler


def run(complect_id, target, compiler_host, task_id, try_create_revision):
    """
    Compability method

    :param complect_id:
    :param target:
    :param compiler_host:
    :param task_id:
    :param try_create_revision:
    :return:
    """
    return compiler.run(
        complect_id=complect_id,
        target=target,
        compiler_host=compiler_host,
        task_id=task_id,
        try_create_revision=try_create_revision,
    )
