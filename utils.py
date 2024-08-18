import httpx
from pathlib import Path
from loguru import logger
from config import get_settings
from db import UploadedFile, SessionLocal
from sqlalchemy import select
from sqlalchemy.orm import Session


BASE_YA_DISK_URL = 'https://cloud-api.yandex.net'


def upload_file_to_cloud(path: Path, uid: str) -> None:
    """Загрузить файл в Яндекс.Диск."""
    settings = get_settings()
    logger.info('Начата загрузка файла в облачное хранилище {uid}', uid=uid)
    response = httpx.get(
        f'{BASE_YA_DISK_URL}/v1/disk/resources/upload',
        params={
            'path': f'/{uid}',
        },
        headers={'Authorization': f'OAuth {settings.CLOUD_API_KEY}'},
        timeout=30,
    )
    response.raise_for_status()
    href = response.json()['href']

    with open(path, 'rb') as f:
        response = httpx.put(
            href,
            files={
                'file': f,
            },
            timeout=30,
        )
    if not response.is_success:
        logger.error(
            'Ошибка при загрузке файла в облачное хранилище {uid}: {response_content}',
            uid=uid,
            response_content=response.text,
        )
        response.raise_for_status()
    logger.info(
        'Файл загружен в облачное хранилище в облачное хранилище {uid}', uid=uid
    )

    db = SessionLocal()
    uploaded_file = db.scalars(select(UploadedFile).where(UploadedFile.uid == uid)).one_or_none()
    if not uploaded_file:
        logger.warning('Метаданные файла отсутствуют {uid}', uid=uid)
        return
    uploaded_file.is_uploaded_to_cloud = True
    db.add(uploaded_file)
    db.commit()


def get_file_path_by_uid(uid: str) -> Path:
    """Получить путь для хранения файла по его UID."""
    settings = get_settings()
    settings.FILES_DIR.mkdir(exist_ok=True)
    return settings.FILES_DIR / uid


def save_file_metadata(
    uid: str,
    filename: str,
    db: Session,
    format: str | None,
) -> UploadedFile:
    """Сохранить информацию о файле в БД."""
    path = get_file_path_by_uid(uid)
    extension = None
    if '.' in filename:
        extension = filename.split('.')[-1]
        filename = ''.join(filename.split('.')[:-1])
    size = path.stat().st_size
    uploaded_file = UploadedFile(
        uid=uid,
        size=size,
        format=format,
        original_name=filename,
        extension=extension,
    )
    db.add(uploaded_file)
    db.commit()
    return uploaded_file
