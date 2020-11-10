## Создание задач для выполнения отдельным процессом

Два метода:
- создание задачи (task.create)
- получение информации по задаче (task.info, task.list)

Примеры использования:
    
Cоздание задачи:
    
    result = post_request(get_create_request(method="task.create",
                                             script="scripts.processor.run",
                                             type="compiler",
                                             args={"complect_id": complect_id}))

    result = result["result"]
    
Получение информации:

    result = post_request(get_info_request(method="task.info",
                                       task_id=task_id))
    
    result = result["result"]

Получение списка задач:
                        
    result = post_request(get_info_request(method="task.list",
                                           type="compiler",
                                           offset=offset,
                                           limit=limit))

    result = result["result"]