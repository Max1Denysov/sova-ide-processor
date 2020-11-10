import os
import py7zlib
import tarfile
import zipfile
from abc import ABCMeta, abstractmethod
from nlab.archiver.exceptions import ArchiveError


class ArchiveFile(metaclass=ABCMeta):
    def __init__(self):
        self.filepath = None

    @abstractmethod
    def check_file(self):
        pass

    @abstractmethod
    def extractall(self, filepath, path):
        pass

    @staticmethod
    @abstractmethod
    def compress(folderpath, path, archive_name):
        pass


class SevenZFile(ArchiveFile):
    """
    7z file
    """
    def check_file(self):
        """
        Проверка файла
        """
        try:
            with open(self.filepath, 'rb') as fp:
                py7zlib.Archive7z(fp)
                return True
        except:
            return False

    def extractall(self, filepath, path):
        """
        Извлечение
        """
        self.filepath = filepath
        if not self.check_file():
            raise ArchiveError("Bad archive file. Can not open the file.")

        with open(self.filepath, "rb") as fp:
            archive = py7zlib.Archive7z(fp)
            for name in archive.getnames():
                outfilename = os.path.join(path, name)
                outdir = os.path.dirname(outfilename)
                if not os.path.exists(outdir):
                    os.makedirs(outdir)
                with open(outfilename, 'wb') as outfile:
                    outfile.write(archive.getmember(name).read())

    @staticmethod
    def compress(folderpath, path, archive_name):
        """
        Архивирование
        """
        raise NotImplementedError("""Method "compress" is not implemented for 7z archive.""")


class TarFile(ArchiveFile):
    """
    Tar file
    """
    def check_file(self):
        """
        Проверка файла
        """
        return tarfile.is_tarfile(self.filepath)

    def get_mode(self):
        """
        Получение режима
        """
        if self.filepath.endswith("tar.gz"):
            return "r:gz"
        elif self.filepath.endswith("tar.xz"):
            return "r:xz"
        elif self.filepath.endswith("tar"):
            return "r:"
        return "r:*"

    def extractall(self, filepath, path):
        """
        Извлечение
        """
        self.filepath = filepath
        if not self.check_file():
            raise ArchiveError("Bad archive file. Can not open the file.")

        mode = self.get_mode()
        with tarfile.open(self.filepath, mode) as tar:
            tar.extractall(path=path)

    @staticmethod
    def compress(folderpath, path, archive_name):
        """
        Архивирование
        """
        with tarfile.open(os.path.join(path, archive_name), "w:gz") as tar:
            tar.add(folderpath, arcname=os.path.basename(os.path.join(path, archive_name)))


class ZipFile(ArchiveFile):
    """
    Zip file
    """
    def check_file(self):
        """
        Проверка файла
        """
        try:
            the_zip_file = zipfile.ZipFile(self.filepath)
            the_zip_file.testzip()
            return True
        except zipfile.BadZipFile:
            return False

    def extractall(self, filepath, path):
        """
        Извлечение
        """
        self.filepath = filepath
        if not self.check_file():
            raise ArchiveError("Bad archive file. Can not open the file.")

        with zipfile.ZipFile(self.filepath, 'r') as zip_ref:
            zip_ref.extractall(path)

    @staticmethod
    def compress(folderpath, path, archive_name):
        """
        Архивирование
        """
        with zipfile.ZipFile((os.path.join(path, archive_name)), 'w') as zip:
            for root, _, files in os.walk(folderpath):
                for file in files:
                    zip.write(os.path.join(root, file), os.path.basename(os.path.join(root, file)))


class Archiver:
    """
    Архиватор
    """
    def __init__(self):
        self.__archiver = None

    def extractall(self, filepath, path):
        """
        Извлечение
        """
        if filepath.lower().endswith("zip"):
            self.__archiver = ZipFile()
        elif filepath.lower().endswith("7z"):
            self.__archiver = SevenZFile()
        else:
            self.__archiver = TarFile()

        self.__archiver.extractall(filepath=filepath, path=path)

    def compress(self, folderpath, path, archive_name="result.zip"):
        """
        Архивирование
        """
        if archive_name.lower().endswith("zip"):
            self.__archiver = ZipFile()
        elif archive_name.lower().endswith("7z"):
            self.__archiver = SevenZFile()
        elif archive_name.lower().endswith("gz"):
            self.__archiver = TarFile()
        else:
            raise NameError("Unknown format file.")

        self.__archiver.compress(folderpath, path, archive_name)
