## Разархивирование файлов

Поддерживается три формата:
- 7z
- zip
- tar

Использование:
        
        from nlab.archiver import Archiver
        filepath = r"tests/data_7z.7z"  # путь к архиву
        path = "tests/data_7z"          # путь к папке, в которую будет произведено извлечение файлов

        archiver = Archiver(filepath=filepath)
        archiver.extractall(path=path)
        
Создание временной директории для разахивирования файлов
    
    import os
    from nlab.archiver import TempDirectory
    
    with TempDirectory() as path:
        archiver.extractall(path)
        for dir_path, _, file_names in os.walk(path_to_directory):
            for file in file_names:
                # выполнение действий с файлами архива